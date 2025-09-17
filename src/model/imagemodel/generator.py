# image_ai/generator.py
from __future__ import annotations
from typing import Optional, Tuple, List
from PIL import Image
import io, base64, json, os, numpy as np, requests
import torch
from huggingface_hub import InferenceClient

# ---- API 스위치 ----
API_PROVIDER = os.getenv("ADSGEN_API_PROVIDER", "local")  # "hf" | "local"
HF_API_TOKEN = os.getenv("HF_API_TOKEN")  # Hugging Face 토큰
HF_TXT2IMG_MODEL = os.getenv("ADSGEN_HF_TXT2IMG_MODEL", "stabilityai/stable-diffusion-3.5-medium")

# 로컬용 import는 필요 시만
if API_PROVIDER == "local":
    from diffusers import (
        StableDiffusion3Pipeline,
        StableDiffusion3Img2ImgPipeline,
        DPMSolverMultistepScheduler,
    )

DTYPE  = torch.bfloat16 if torch.cuda.is_available() else torch.float32
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

SD3_MODEL = os.getenv("ADSGEN_SD3_MODEL", "/opt/models/hf/sd3.5-medium")

def _size_to_8x(size: Tuple[int,int]) -> Tuple[int,int]:
    w, h = size
    return (w - w % 8, h - h % 8)

# -----------------------
# HF API backend (txt2img)
# -----------------------
def _hf_txt2img(prompt: str, w: int, h: int, steps: int, guidance: float, negative: str, seed: int | None):
    """
    Hugging Face InferenceClient + provider 경유 호출 (sd3.5 large turbo 등)
    - 환경변수:
      * HF_API_TOKEN            : 필수 (Access Token)
      * ADSGEN_HF_PROVIDER      : 기본 'fal-ai' (fal-ai 권장)
      * ADSGEN_HF_TXT2IMG_MODEL : 예) 'stabilityai/stable-diffusion-3.5-large-turbo'
    """
    token   = os.getenv("HF_API_TOKEN") or os.getenv("HF_TOKEN")
    model   = os.getenv("ADSGEN_HF_TXT2IMG_MODEL", "stabilityai/stable-diffusion-3.5-large-turbo")
    provider = os.getenv("ADSGEN_HF_PROVIDER", "fal-ai")

    if not token:
        raise RuntimeError("HF_API_TOKEN (or HF_TOKEN) is not set")

    # InferenceClient: provider 경유
    client = InferenceClient(provider=provider, api_key=token)

    # Turbo 계열은 짧은 스텝 권장 (4~8)
    steps = max(1, min(12, steps))

    # 호출 (PIL.Image 반환)
    img = client.text_to_image(
        prompt=prompt,
        model=model,
        negative_prompt=(negative or None),
        height=h,
        width=w,
        num_inference_steps=steps,
        guidance_scale=float(guidance),
        seed=seed
    )
    # 일부 provider가 numpy 이미지로 줄 수도 있어 PIL 보장
    if not isinstance(img, Image.Image):
        img = Image.fromarray(img)
    return img

class ReconGenerator:
    """
    SD3.5 Medium 재구성
    - API_PROVIDER=hf → HF Inference API(txt2img) 사용
    - API_PROVIDER=local → 기존 diffusers(local) 사용
    """
    def __init__(self, model_id: str = SD3_MODEL, device: str = DEVICE, dtype=DTYPE):
        self.backend = API_PROVIDER
        if self.backend == "local":
            # --- 파이프라인 로드 ---
            self.pipe_t2i = StableDiffusion3Pipeline.from_pretrained(
                model_id, torch_dtype=dtype, use_safetensors=True
            )
            self.pipe_i2i = StableDiffusion3Img2ImgPipeline.from_pretrained(
                model_id, torch_dtype=dtype, use_safetensors=True
            )
            # 스케줄러
            try:
                self.pipe_t2i.scheduler = DPMSolverMultistepScheduler.from_config(
                    self.pipe_t2i.scheduler.config, algorithm_type="sde-dpmsolver++", use_karras=True
                )
                self.pipe_i2i.scheduler = DPMSolverMultistepScheduler.from_config(
                    self.pipe_i2i.scheduler.config, algorithm_type="sde-dpmsolver++", use_karras=True
                )
            except Exception:
                pass
            # 메모리/속도
            for p in (self.pipe_t2i, self.pipe_i2i):
                for fname in ("enable_attention_slicing", "enable_vae_slicing"):
                    try: getattr(p, fname)()
                    except Exception: pass
                try: p.enable_xformers_memory_efficient_attention()
                except Exception: pass
                p.to(device)
        else:
            # API 모드에서는 로컬 초기화 불필요
            self.pipe_t2i = None
            self.pipe_i2i = None

        self.has_ip_adapter = False  # API 경로에선 미사용/미지원
        self.ip_adapter_error = None

    def generate(
        self,
        ref_image: Image.Image,
        prompt: str,
        size: Tuple[int,int],
        seed: Optional[int] = None,
        strength: float = 0.5,
        guidance_scale: float = 5.0,
        negative: str = (
            "lowres, blurry, watermark, text, extra objects, deformation artifacts, oversharpen, banding"
        ),
        steps: int = 20,
        use_ip: Optional[bool] = None,
        ip_scale: float = 0.6,
        noise_mode: str = "none",
        ref_mode: str = "ip_txt2img",  # "ip_txt2img" | "img2img"
        extra_ref_images: Optional[List[Image.Image]] = None,
        style_ref_image: Optional[Image.Image] = None,
        ip_style_scale: float = 0.4,
    ) -> Image.Image:

        W, H = _size_to_8x(size)
        if self.backend == "hf":
            # 현재 구현: txt2img만. (img2img은 필요 시 별도로 확장)
            if ref_mode != "ip_txt2img":
                raise NotImplementedError("API 모드(hf)는 현재 txt2img만 지원해요. ref_mode=ip_txt2img로 사용하세요.")
            return _hf_txt2img(prompt, W, H, steps, guidance_scale, negative, seed)

        # ---------- local 분기 ----------
        ref_rgb = ref_image.convert("RGB")
        g = torch.Generator(device=self.pipe_t2i.device if ref_mode=="ip_txt2img" else self.pipe_i2i.device)
        if seed is not None:
            g = g.manual_seed(seed)

        if ref_mode == "ip_txt2img":
            out = self.pipe_t2i(
                prompt=prompt,
                negative_prompt=negative,
                guidance_scale=guidance_scale,
                num_inference_steps=steps,
                generator=g,
                width=W, height=H,
            ).images[0]
            return out

        # img2img (로컬)
        init = ref_rgb.resize((W, H), Image.LANCZOS)
        if noise_mode != "none":
            rng = np.random.default_rng(seed if seed is not None else 0)
            noise = rng.normal(0.0, 1.0, (H, W, 3)).astype(np.float32)
            init_np = np.array(init, dtype=np.float32) / 255.0
            sigma = 0.03 if noise_mode == "soft" else 0.07
            init = Image.fromarray(
                (np.clip(init_np + sigma * noise, 0, 1) * 255).astype(np.uint8), mode="RGB"
            )
        out = self.pipe_i2i(
            prompt=prompt,
            negative_prompt=negative,
            image=init,
            strength=strength,
            guidance_scale=guidance_scale,
            num_inference_steps=steps,
            generator=g,
        ).images[0]
        return out