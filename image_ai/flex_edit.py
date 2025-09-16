# image_ai/flex_edit.py
from __future__ import annotations
import os, torch, cv2, numpy as np
from typing import Optional, Tuple
from PIL import Image, ImageFilter
from diffusers import (
    StableDiffusionXLControlNetInpaintPipeline, 
    ControlNetModel,
    AutoencoderKL,
)
# from diffusers.utils import load_image

DTYPE  = torch.float16 if torch.cuda.is_available() else torch.float32
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# SDXL Inpaint 베이스
SDXL_INPAINT = os.getenv(
    "ADSGEN_INPAINT_MODEL",
    "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"
)

# SDXL 전용 ControlNet 가중치로 변경
CN_CANNY = os.getenv(
    "ADSGEN_CN_CANNY",
    "diffusers/controlnet-canny-sdxl-1.0"
)

VAE_ID = os.getenv("ADSGEN_VAE_MODEL", "madebyollin/sdxl-vae-fp16-fix")

IP_REPO      = os.getenv("ADSGEN_IP_ADAPTER", "h94/IP-Adapter")
IP_SUBFOLDER = os.getenv("ADSGEN_IP_SUBFOLDER", "sdxl_models")

NEG = (
    "lowres, blurry, noisy, watermark, text, logo change, deformation artifacts, "
    "extra parts, duplicate object, oversharpen, color banding"
)

def _resize_to_8x(size: Tuple[int,int]) -> Tuple[int,int]:
    w,h = size
    return (w - w%8, h - h%8)

def _to_pil(img):
    return img if isinstance(img, Image.Image) else Image.open(img)

def _canny_from_rgb(img: Image.Image, low=80, high=160) -> Image.Image:
    rgb = np.array(img.convert("RGB"))
    edges = cv2.Canny(rgb, low, high)
    edges = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=1)
    return Image.fromarray(edges)

class FlexEditor:
    """
    실루엣 일부 변형 허용:
      - IP-Adapter scale: 0.3~0.6 (아이덴티티 느슨하게 고정)
      - ControlNet(Canny): 주요 윤곽 가이드 (allow_deform로 강도 조정)
      - Inpaint: 제품/주 변형 영역만 흰색 마스크로 편집
    """
    def __init__(self, use_ip=True, use_controlnet=True,
                 device: str = DEVICE, dtype = DTYPE):

        vae = AutoencoderKL.from_pretrained(VAE_ID, torch_dtype=dtype) if VAE_ID else None

        controlnet = None
        if use_controlnet:
            controlnet = ControlNetModel.from_pretrained(CN_CANNY, torch_dtype=dtype)

        # SDXL + ControlNet + Inpaint 파이프라인
        self.pipe = StableDiffusionXLControlNetInpaintPipeline.from_pretrained(
            SDXL_INPAINT,
            controlnet=controlnet,
            vae=vae,
            torch_dtype=dtype,
            use_safetensors=True,
            variant="fp16" if dtype==torch.float16 else None,
        )

        if device == "cuda":
            try:
                self.pipe.enable_xformers_memory_efficient_attention()
            except Exception:
                pass
            self.pipe.to(device)
        else:
            self.pipe.to(device)

        # IP-Adapter (있는 경우만)
        self.ip_enabled = False
        if use_ip:
            try:
                # SDXL 호환 IP-Adapter 로드
                self.pipe.load_ip_adapter(IP_REPO, subfolder=IP_SUBFOLDER)
                self.ip_enabled = True
            except Exception:
                self.ip_enabled = False

    def edit(
        self,
        image: Image.Image,                  # 원본 RGB/RGBA
        product_mask: Optional[Image.Image], # L, 흰=편집/검=보존
        prompt: str,
        user_style: Optional[str] = None,
        allow_deform: float = 0.5,           # 0~1 (클수록 윤곽가이드 약화)
        ip_scale: float = 0.5,               # 0~1 (클수록 원본 유지↑)
        steps: int = 28,
        strength: float = 0.55,              # 0.45~0.7
        guidance: float = 6.0,
        seed: Optional[int] = None
    ) -> Image.Image:

        img = _to_pil(image).convert("RGB")
        W,H = _resize_to_8x(img.size)
        if (W,H) != img.size:
            img = img.resize((W,H), Image.LANCZOS)

        # 마스크 준비 (없으면 전체 편집)
        if product_mask is None:
            # 전체를 바꾼다 = 흰 마스크
            mask = Image.new("L", (W,H), 255)
        else:
            # 제품/주변 여유를 조금 늘려 변형 공간 확보
            mask = product_mask.convert("L").resize((W,H), Image.NEAREST)
            # MaxFilter는 홀수 커널, 값이 클수록 팽창. 5~7로 시작 추천
            mask = mask.filter(ImageFilter.MaxFilter(5))

        # ControlNet 가이드(윤곽) — allow_deform이 클수록 강도 약화
        cn_img = None
        if hasattr(self.pipe, "controlnet") and self.pipe.controlnet is not None:
            low  = int(60 + 80 * allow_deform)
            high = int(140 + 80 * allow_deform)
            cn_img = _canny_from_rgb(img, low=low, high=high)

        # IP-Adapter (가능할 때만)
        ip_kwargs = {}
        if self.ip_enabled:
            self.pipe.set_ip_adapter_scale(max(0.0, min(1.0, ip_scale)))
            ip_kwargs = {"ip_adapter_image": img}

        full_prompt = f"{prompt}, {user_style}" if user_style else prompt
        neg = NEG

        gen = None
        if seed is not None:
            gen = torch.Generator(device=self.pipe.device).manual_seed(seed)

        out = self.pipe(
            prompt=full_prompt,
            negative_prompt=neg,
            image=img,
            mask_image=mask,       # 흰=수정(여기가 재질/형상 변경될 영역)
            control_image=cn_img,  # canny 가이드(없으면 None)
            num_inference_steps=steps,
            strength=strength,
            guidance_scale=guidance,
            generator=gen,
            **ip_kwargs
        ).images[0]

        return out.convert("RGBA")