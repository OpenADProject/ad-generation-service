# imagemodel/config.py
import os
from dataclasses import dataclass
from typing import Optional

# .env는 있으면 로드(없어도 무시)
try:
    from dotenv import load_dotenv  
    load_dotenv()
except Exception:
    pass


@dataclass
class GenConfig:
    api_provider: str            # "hf" | "local"
    hf_token: Optional[str]
    hf_model: Optional[str]
    hf_provider: str             # "fal-ai" 등 (옵션)
    sd3_model_path: Optional[str]
    low_mem: bool
    cpu_offload: bool
    model_family: str = "sd3.5"
    model_variant: str = "medium"


def load_config(
    api_provider: Optional[str] = None,
    hf_token: Optional[str] = None,
    hf_model: Optional[str] = None,
    hf_provider: Optional[str] = None,
    sd3_model_path: Optional[str] = None,
    low_mem: Optional[bool] = None,
    cpu_offload: Optional[bool] = None,
    # 새 인자
    model_family: Optional[str] = None,
    model_variant: Optional[str] = None,
) -> GenConfig:
    # 1) .env/환경변수 기본값
    env_api_provider = os.getenv("ADSGEN_API_PROVIDER", "local").strip().lower()
    env_hf_token     = os.getenv("HF_API_TOKEN") or os.getenv("HF_TOKEN")
    env_hf_model     = os.getenv("ADSGEN_HF_TXT2IMG_MODEL")
    env_hf_provider  = os.getenv("ADSGEN_HF_PROVIDER", "fal-ai")
    env_sd3_path     = os.getenv("ADSGEN_SD3_MODEL", "/opt/models/hf/sd3.5-medium")
    env_low_mem      = os.getenv("ADSGEN_LOW_MEM", "0") == "1"
    env_offload      = os.getenv("ADSGEN_CPU_OFFLOAD", "0") == "1"
    env_family       = os.getenv("ADSGEN_MODEL_FAMILY", "sd3.5").strip().lower()
    env_variant      = os.getenv("ADSGEN_MODEL_VARIANT", "medium").strip().lower()

    # 2) CLI 인자가 있으면 최우선으로 덮어쓰기
    api_provider   = (api_provider or env_api_provider).strip().lower()
    hf_token       = hf_token or env_hf_token
    hf_model       = hf_model or env_hf_model
    hf_provider    = (hf_provider or env_hf_provider).strip()
    sd3_model_path = sd3_model_path or env_sd3_path
    low_mem        = env_low_mem if low_mem is None else low_mem
    cpu_offload    = env_offload if cpu_offload is None else cpu_offload
    model_family   = (model_family or env_family).strip().lower()
    model_variant  = (model_variant or env_variant).strip().lower()

    return GenConfig(
        api_provider=api_provider,
        hf_token=hf_token,
        hf_model=hf_model,
        hf_provider=hf_provider,
        sd3_model_path=sd3_model_path,
        low_mem=low_mem,
        cpu_offload=cpu_offload,
        model_family=model_family,
        model_variant=model_variant,
    )