# image_ai/flex_edit.py
from __future__ import annotations
import io, base64, json, os, torch, cv2, numpy as np, requests
from typing import Optional, Tuple
from PIL import Image, ImageFilter

API_PROVIDER = os.getenv("ADSGEN_API_PROVIDER", "local")  # "hf" | "local"
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
# HF 인페인팅용 모델 (SDXL Inpaint)
HF_INPAINT_MODEL = os.getenv("ADSGEN_HF_INPAINT_MODEL", "diffusers/stable-diffusion-xl-1.0-inpainting-0.1")

DTYPE  = torch.float16 if torch.cuda.is_available() else torch.float32
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

if API_PROVIDER == "local":
    from diffusers import (
        StableDiffusionXLControlNetInpaintPipeline,
        ControlNetModel,
        AutoencoderKL,
    )

    SDXL_INPAINT = os.getenv("ADSGEN_INPAINT_MODEL", "diffusers/stable-diffusion-xl-1.0-inpainting-0.1")
    CN_CANNY = os.getenv("ADSGEN_CN_CANNY", "diffusers/controlnet-canny-sdxl-1.0")
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

# -------------------------
# HF API backend (inpaint)
# -------------------------
def _img_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def _hf_inpaint(prompt: str, img: Image.Image, mask: Image.Image,
                steps: int, guidance: float, negative: str, seed: Optional[int]) -> Image.Image:
    if not HF_API_TOKEN:
        raise RuntimeError("HF_API_TOKEN이 비어있어요. export HF_API_TOKEN=... 설정해 주세요.")
    url = f"https://api-inference.huggingface.co/models/{HF_INPAINT_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {
        "inputs": {
            "image": _img_to_b64(img.convert("RGBA")),   # 배경 포함
            "mask":  _img_to_b64(mask.convert("L")),
            "prompt": prompt,
        },
        "parameters": {
            "num_inference_steps": steps,
            "guidance_scale": guidance,
            "negative_prompt": negative,
            **({ "seed": seed } if seed is not None else {}),
        },
        "options": {"wait_for_model": True}
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=600)
    if r.status_code != 200:
        raise RuntimeError(f"HF Inpaint API error {r.status_code}: {r.text[:500]}")
    try:
        return Image.open(io.BytesIO(r.content)).convert("RGBA")
    except Exception:
        data = r.json()
        if isinstance(data, dict) and "generated_image" in data:
            img_bytes = base64.b64decode(data["generated_image"])
            return Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        raise RuntimeError("HF Inpaint 응답 파싱 실패")

class FlexEditor:
    """
    API_PROVIDER=hf → Hugging Face Inference API 인페인팅 사용
    API_PROVIDER=local → 기존 SDXL Inpaint(+ControlNet, 선택 IP-Adapter)
    """
    def __init__(self, use_ip=True, use_controlnet=True,
                 device: str = DEVICE, dtype = DTYPE):

        self.backend = API_PROVIDER
        self.ip_enabled = False

        if self.backend == "local":
            vae = AutoencoderKL.from_pretrained(VAE_ID, torch_dtype=dtype) if VAE_ID else None
            controlnet = None
            if use_controlnet:
                controlnet = ControlNetModel.from_pretrained(os.getenv("ADSGEN_CN_CANNY", "diffusers/controlnet-canny-sdxl-1.0"), torch_dtype=dtype)

            self.pipe = StableDiffusionXLControlNetInpaintPipeline.from_pretrained(
                os.getenv("ADSGEN_INPAINT_MODEL", "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"),
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

            if use_ip:
                try:
                    self.pipe.load_ip_adapter(os.getenv("ADSGEN_IP_ADAPTER", "h94/IP-Adapter"),
                                              subfolder=os.getenv("ADSGEN_IP_SUBFOLDER", "sdxl_models"))
                    self.ip_enabled = True
                except Exception:
                    self.ip_enabled = False
        else:
            self.pipe = None  # API 모드에선 로컬 파이프라인 불필요

    def edit(
        self,
        image: Image.Image,
        product_mask: Optional[Image.Image],
        prompt: str,
        user_style: Optional[str] = None,
        allow_deform: float = 0.5,
        ip_scale: float = 0.5,
        steps: int = 28,
        strength: float = 0.55,
        guidance: float = 6.0,
        seed: Optional[int] = None
    ) -> Image.Image:

        img = _to_pil(image).convert("RGB")
        W,H = _resize_to_8x(img.size)
        if (W,H) != img.size:
            img = img.resize((W,H), Image.LANCZOS)

        # 마스크 준비 (없으면 전체 편집)
        if product_mask is None:
            mask = Image.new("L", (W,H), 255)
        else:
            mask = product_mask.convert("L").resize((W,H), Image.NEAREST)
            mask = mask.filter(ImageFilter.MaxFilter(5))

        full_prompt = f"{prompt}, {user_style}" if user_style else prompt
        neg = NEG

        # ---- HF API 분기 ----
        if self.backend == "hf":
            # ControlNet/IP-Adapter는 HF 호스팅 모델에 따라 미지원일 수 있어 단순 인페인팅만 수행
            return _hf_inpaint(full_prompt, img, mask, steps, guidance, neg, seed)

        # ---- 로컬 분기 (기존과 동일) ----
        cn_img = None
        if hasattr(self.pipe, "controlnet") and self.pipe.controlnet is not None:
            low  = int(60 + 80 * allow_deform)
            high = int(140 + 80 * allow_deform)
            cn_img = _canny_from_rgb(img, low=low, high=high)

        ip_kwargs = {}
        if self.ip_enabled:
            self.pipe.set_ip_adapter_scale(max(0.0, min(1.0, ip_scale)))
            ip_kwargs = {"ip_adapter_image": img}

        gen = None
        if seed is not None:
            gen = torch.Generator(device=self.pipe.device).manual_seed(seed)

        out = self.pipe(
            prompt=full_prompt,
            negative_prompt=neg,
            image=img,
            mask_image=mask,
            control_image=cn_img,
            num_inference_steps=steps,
            strength=strength,
            guidance_scale=guidance,
            generator=gen,
            **ip_kwargs
        ).images[0]

        return out.convert("RGBA")