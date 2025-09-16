# image_ai/generator.py
from __future__ import annotations
from typing import Optional, Tuple, List
from PIL import Image
import torch, os, numpy as np
from diffusers import (
    StableDiffusionXLImg2ImgPipeline,
    StableDiffusionXLPipeline,
    DPMSolverMultistepScheduler,
)

DTYPE  = torch.float16 if torch.cuda.is_available() else torch.float32
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

SDXL_MODEL   = os.getenv("ADSGEN_SDXL_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
IP_REPO      = os.getenv("ADSGEN_IPADAPTER_REPO", "h94/IP-Adapter")
IP_SUBFOLDER = os.getenv("ADSGEN_IP_SUBFOLDER", "sdxl_models")  # SDXL 전용 가중치 위치

def _size_to_8x(size: Tuple[int,int]) -> Tuple[int,int]:
    w, h = size
    return (w - w % 8, h - h % 8)

class ReconGenerator:
    """
    SDXL 기반 재구성:
      - 기본: txt2img(+IP-Adapter)로 '참조만 하고 새로 합성' (ref_mode='ip_txt2img')
      - 선택: img2img (ref_mode='img2img'), 입력은 fit_to_canvas로 왜곡 없이 맞춤
      - IP-Adapter: on/off + 스케일, 멀티 이미지(제품 여러 장 + 스타일 레퍼런스) 지원
      - 속도 최적화: DPM-Solver++(Karras), safety checker off, slicing, xFormers, 채널라스트, (선택) torch.compile
    """
    def __init__(self, model_id: str = SDXL_MODEL, device: str = DEVICE, dtype=DTYPE):
        # --- 파이프라인 로드 ---
        self.pipe_i2i = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            model_id, torch_dtype=dtype, use_safetensors=True,
            variant="fp16" if dtype == torch.float16 else None,
        )
        self.pipe_t2i = StableDiffusionXLPipeline.from_pretrained(
            model_id, torch_dtype=dtype, use_safetensors=True,
            variant="fp16" if dtype == torch.float16 else None,
        )

        # --- 스케줄러: 빠르고 안정적인 DPM-Solver++(Karras) ---
        try:
            self.pipe_t2i.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipe_t2i.scheduler.config, algorithm_type="sde-dpmsolver++", use_karras=True
            )
            self.pipe_i2i.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipe_i2i.scheduler.config, algorithm_type="sde-dpmsolver++", use_karras=True
            )
        except Exception:
            pass

        # --- 메모리/속도 최적화 ---
        self.pipe_t2i.safety_checker = None
        self.pipe_i2i.safety_checker = None
        self.pipe_t2i.enable_attention_slicing()
        self.pipe_i2i.enable_attention_slicing()
        self.pipe_t2i.enable_vae_slicing()
        self.pipe_i2i.enable_vae_slicing()
        # 큰 해상도에서 VRAM 빠듯하면 필요 시:
        # self.pipe_t2i.enable_vae_tiling(); self.pipe_i2i.enable_vae_tiling()

        if device == "cuda":
            try:
                self.pipe_i2i.enable_xformers_memory_efficient_attention()
                self.pipe_t2i.enable_xformers_memory_efficient_attention()
            except Exception:
                pass

        self.pipe_i2i.to(device)
        self.pipe_t2i.to(device)

        try:
            self.pipe_t2i.unet.to(memory_format=torch.channels_last)
            self.pipe_i2i.unet.to(memory_format=torch.channels_last)
            torch.set_float32_matmul_precision("high")
        except Exception:
            pass

        # (선택) PyTorch 2.x: 첫 호출 워밍업 필요
        try:
            self.pipe_t2i.unet = torch.compile(self.pipe_t2i.unet, mode="reduce-overhead", fullgraph=False)
            self.pipe_i2i.unet = torch.compile(self.pipe_i2i.unet, mode="reduce-overhead", fullgraph=False)
        except Exception:
            pass

        # --- IP-Adapter 로드 (SDXL 서브폴더 우선 → 폴백) ---
        self.has_ip_adapter = False
        self.ip_adapter_error: Optional[str] = None
        try:
            # 1) SDXL 전용 서브폴더 가중치 우선
            self.pipe_i2i.load_ip_adapter(IP_REPO, subfolder=IP_SUBFOLDER)
            self.pipe_t2i.load_ip_adapter(IP_REPO, subfolder=IP_SUBFOLDER)
            self.has_ip_adapter = True
        except Exception as e1:
            try:
                # 2) 구버전/커스텀 레이아웃 폴백
                self.pipe_i2i.load_ip_adapter(IP_REPO)
                self.pipe_t2i.load_ip_adapter(IP_REPO)
                self.has_ip_adapter = True
            except Exception as e2:
                self.has_ip_adapter = False
                self.ip_adapter_error = f"{type(e2).__name__}: {e2}"

    # IP-Adapter 스케일/입력 바인딩 헬퍼 (단일/다중 모두 지원)
    def _apply_ip_adapter(
        self,
        pipe,
        enabled: bool,
        images: List[Image.Image],
        scales: List[float],
    ):
        if not enabled or not images:
            return {}, False
        try:
            # 최신 diffusers: 리스트 입력과 리스트 스케일 지원
            pipe.set_ip_adapter_scale([max(0.0, min(1.0, s)) for s in scales])
            return {"ip_adapter_image": images}, True
        except Exception:
            # 구버전: 단일만 지원할 수 있음 → 첫 번째만 사용
            try:
                pipe.set_ip_adapter_scale(max(0.0, min(1.0, scales[0])))
                return {"ip_adapter_image": images[0]}, True
            except Exception:
                return {}, False

    def generate(
        self,
        ref_image: Image.Image,                       # 제품 기본 참조 1장
        prompt: str,
        size: Tuple[int,int],
        seed: Optional[int] = None,
        strength: float = 0.55,                       # (img2img) 변형 강도
        guidance_scale: float = 5.5,
        negative: str = (
            "lowres, blurry, watermark, text, extra objects, deformation artifacts, oversharpen, banding"
        ),
        steps: int = 28,
        use_ip: Optional[bool] = None,                # None: 자동, True/False: 강제
        ip_scale: float = 0.6,                        # 제품 고정 강도
        noise_mode: str = "soft",                     # img2img 전용: "none" | "soft" | "strong"
        ref_mode: str = "ip_txt2img",                 # "ip_txt2img" | "img2img"
        # --- 멀티 IP-Adapter 확장(선택) ---
        extra_ref_images: Optional[List[Image.Image]] = None,  # 제품 추가컷들
        style_ref_image: Optional[Image.Image] = None,         # 스타일/무드 레퍼런스
        ip_style_scale: float = 0.4,                           # 스타일 고정 강도
    ) -> Image.Image:

        # ----- 기본 파라미터 정리 -----
        W, H = _size_to_8x(size)
        ref_rgb = ref_image.convert("RGB")
        extra_rgbs = [im.convert("RGB") for im in (extra_ref_images or [])]
        style_rgb = style_ref_image.convert("RGB") if style_ref_image is not None else None

        # 시드/제네레이터
        g_i2i = torch.Generator(device=self.pipe_i2i.device).manual_seed(seed) if seed is not None else None
        g_t2i = torch.Generator(device=self.pipe_t2i.device).manual_seed(seed) if seed is not None else None

        # IP-Adapter 사용 여부
        ip_enabled = self.has_ip_adapter if use_ip is None else (use_ip and self.has_ip_adapter)

        # IP-Adapter 입력/스케일 구성
        ip_images: List[Image.Image] = [ref_rgb] + extra_rgbs
        ip_scales: List[float] = [ip_scale] + [ip_scale] * len(extra_rgbs)
        if style_rgb is not None:
            ip_images.append(style_rgb)
            ip_scales.append(ip_style_scale)

        # ----- 경로 1: 참조만 하고 새로 합성 (권장, 빠름) -----
        if ref_mode == "ip_txt2img":
            kwargs = dict(
                prompt=prompt,
                negative_prompt=negative,
                guidance_scale=guidance_scale,
                num_inference_steps=steps,
                generator=g_t2i,
                width=W, height=H,
            )
            if ip_enabled and any(s > 0 for s in ip_scales):
                extra, ok = self._apply_ip_adapter(self.pipe_t2i, True, ip_images, ip_scales)
                if ok:
                    kwargs.update(extra)
            out = self.pipe_t2i(**kwargs).images[0]
            return out

        # ----- 경로 2: 왜곡 없는 img2img -----
        from .io import fit_to_canvas
        init = fit_to_canvas(ref_rgb, (W, H))

        if noise_mode != "none":
            rng = np.random.default_rng(seed if seed is not None else 0)
            noise = rng.normal(0.0, 1.0, (H, W, 3)).astype(np.float32)
            init_np = np.array(init, dtype=np.float32) / 255.0
            sigma = 0.03 if noise_mode == "soft" else 0.07
            init = Image.fromarray(
                (np.clip(init_np + sigma * noise, 0, 1) * 255).astype(np.uint8), mode="RGB"
            )

        kwargs = dict(
            prompt=prompt,
            negative_prompt=negative,
            image=init,
            strength=strength,                  # img2img 변형 강도
            guidance_scale=guidance_scale,
            num_inference_steps=steps,
            generator=g_i2i,
            width=W, height=H,
        )
        if ip_enabled and any(s > 0 for s in ip_scales):
            extra, ok = self._apply_ip_adapter(self.pipe_i2i, True, ip_images, ip_scales)
            if ok:
                kwargs.update(extra)

        out = self.pipe_i2i(**kwargs).images[0]
        return out