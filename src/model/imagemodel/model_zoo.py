# imagemodel/model_zoo.py
import os

def resolve_model_id(family: str, variant: str) -> str:
    f = family.strip().lower()
    v = variant.strip().lower()

    # -----------------------------
    # 로컬 경로 우선 (오프라인/프리다운로드 환경 대응)
    # -----------------------------
    if f == "sdxl":
        if v == "inpaint":
            local = os.getenv("ADSGEN_SDXL_INPAINT")
        else:
            local = os.getenv("ADSGEN_SDXL_BASE")
        if local and os.path.isdir(local):
            return local

    if f == "sd3.5":
        local = os.getenv("ADSGEN_SD3_MODEL")
        if local and os.path.isdir(local):
            return local

    # -----------------------------
    # 허브 리포 ID 매핑
    # -----------------------------
    ZOO = {
        "sd3.5": {
            "medium":  "stabilityai/stable-diffusion-3.5-medium",
            "large":   "stabilityai/stable-diffusion-3.5-large",
            "inpaint": "stabilityai/stable-diffusion-3.5-inpainting",
        },
        "sdxl": {
            "base":    "stabilityai/stable-diffusion-xl-base-1.0",
            "inpaint": "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
        }
    }

    if f not in ZOO or v not in ZOO[f]:
        raise ValueError(f"Unknown model family/variant: {family}/{variant}")
    return ZOO[f][v]