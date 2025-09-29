import torch
import os

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
TORCH_DTYPE = torch.float16 if torch.cuda.is_available() else torch.float32


BASE_MODEL_DIR = "/opt/models/hf/hub"

SDXL_BASE_MODEL_PATH = os.path.join(BASE_MODEL_DIR, "stabilityai--stable-diffusion-xl-base-1.0")
VAE_PATH = os.path.join(BASE_MODEL_DIR, "madebyollin--sdxl-vae-fp16-fix")

CONTROLNET_CANNY_PATH = os.path.join(BASE_MODEL_DIR, "diffusers--controlnet-canny-sdxl-1.0")
CONTROLNET_DEPTH_PATH = os.path.join(BASE_MODEL_DIR, "diffusers--controlnet-depth-sdxl-1.0")
CONTROLNET_INPAINT_PATH = os.path.join(BASE_MODEL_DIR, "destitech--controlnet-inpaint-dreamer-sdxl")

IP_ADAPTER_BASE_PATH = os.path.join(BASE_MODEL_DIR, "models--h94--IP-Adapter")
IP_ADAPTER_IMAGE_ENCODER_PATH = "/opt/models/hf/hub/laion--CLIP-ViT-H-14-laion2B-s32B-b79K"
IP_ADAPTER_WEIGHTS_PATH = os.path.join(IP_ADAPTER_BASE_PATH, "sdxl_models", "ip-adapter-plus_sdxl_vit-h.safetensors")

GROUNDING_DINO_PATH = os.path.join(BASE_MODEL_DIR, "IDEA-Research--grounding-dino-tiny")

SAM_MODEL_PATH = os.path.join(BASE_MODEL_DIR, "facebook--sam-vit-huge")

REFINER_MODEL_PATH = os.path.join(BASE_MODEL_DIR, "stabilityai--stable-diffusion-xl-refiner-1.0")
REFINER_STRENGTH = 0.1 

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
GPT_MODEL = "gpt-5-mini"

ENABLE_GPT_ANALYSIS = True

ENABLE_AD_WRAPPER = True  # 광고용 래핑 기능 on/off
AD_BRAND_NAME = None      # 예: "Sunny Pets"
AD_PRODUCT_NAME = None    # 예: "Banana Chew Toy"
AD_TONE = "bold, clean, modern, high-contrast"
AD_LAYOUT_HINT = "hero shot composition with generous negative space for copy at top-right"
AD_CTA = "Shop now"       # 한국어 프롬프트면 자동 번역 CTA 사용
AD_STYLE_HINTS = [
    "studio-grade lighting",
    "clear subject-background separation",
    "subtle depth of field",
    "high legibility background",
]
AD_STRENGTH = 0.8  # 0~1. 1에 가까울수록 광고 템플릿 가중치가 큼
MAX_PROMPT_CHARS = 900  # 너무 길어지면 잘라내는 상한