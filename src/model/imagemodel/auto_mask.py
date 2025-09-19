from __future__ import annotations
from typing import Literal, Optional
import numpy as np
from PIL import Image

# Pillow Resampling 호환 (구버전 Pillow 방지)
if not hasattr(Image, "Resampling"):
    class _R:
        NEAREST = Image.NEAREST
        LANCZOS = Image.LANCZOS
        BILINEAR = Image.BILINEAR
    Image.Resampling = _R()

def _to_rgba(img: Image.Image) -> Image.Image:
    return img.convert("RGBA") if img.mode != "RGBA" else img

def _hard_binary(mask: Image.Image, thresh: int = 128) -> Image.Image:
    """하드 엣지 이진화(0/255)."""
    m = mask.convert("L")
    arr = np.array(m, dtype=np.uint8)
    arr = (arr >= thresh).astype(np.uint8) * 255
    return Image.fromarray(arr, mode="L")

def _alpha_to_bg_mask(rgba: Image.Image, invert: bool = True) -> Image.Image:
    """
    RGBA의 알파를 배경마스크로 변환.
    반환 규약: 배경=255, 전경=0 (인페인팅 마스크 규약)
    """
    a = np.array(rgba.split()[-1], dtype=np.uint8)
    fg = (a >= 128).astype(np.uint8) * 255  # 전경=255
    bg = 255 - fg if invert else fg
    return Image.fromarray(bg, "L")

# ---------------------------
# Rembg 단독
# ---------------------------
def rembg_auto_mask(image: Image.Image) -> Image.Image:
    """
    rembg로 전경 추출 → 배경 마스크(배경=255, 제품=0).
    페더/블러 없음(하드 이진화).
    """
    try:
        from rembg import remove  # pip install rembg
    except Exception as e:
        raise RuntimeError("rembg가 설치되어 있지 않습니다. `pip install rembg`") from e

    rgba = _to_rgba(image)
    out_rgba = Image.fromarray(remove(np.array(rgba)))
    bg_mask = _alpha_to_bg_mask(out_rgba, invert=True)
    return _hard_binary(bg_mask, 128)

# ---------------------------
# SAM 단독
# ---------------------------
def _sam_generate_fg_mask(image: Image.Image, checkpoint_path: str) -> Image.Image:
    """
    SAM에서 전경 마스크(전경=255, 배경=0) 하나를 반환.
    가장 큰 면적 후보를 선택.
    """
    try:
        from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
        import torch
    except Exception as e:
        raise RuntimeError(
            "segment-anything(SAM)가 설치되어 있지 않습니다. "
            "`pip install git+https://github.com/facebookresearch/segment-anything.git`"
        ) from e

    device = "cuda" if torch.cuda.is_available() else "cpu"
    last_err = None
    sam = None
    for key in ("vit_h", "vit_l", "vit_b"):
        try:
            sam = sam_model_registry[key](checkpoint=checkpoint_path).to(device)
            break
        except Exception as e:
            last_err = e
    if sam is None:
        raise RuntimeError(f"SAM 로드 실패: {last_err}")

    gen = SamAutomaticMaskGenerator(
        model=sam,
        points_per_side=24,
        pred_iou_thresh=0.88,
        stability_score_thresh=0.92,
        min_mask_region_area=256,
    )

    rgb = image.convert("RGB")
    masks = gen.generate(np.array(rgb))
    if not masks:
        return Image.new("L", rgb.size, 0)

    best = max(masks, key=lambda m: m.get("area", 0))
    m = (best["segmentation"].astype(np.uint8)) * 255  # 전경=255
    return Image.fromarray(m, "L")

def sam_auto_mask(image: Image.Image, checkpoint_path: Optional[str]) -> Image.Image:
    """
    SAM → 배경 마스크(배경=255, 전경=0)
    """
    import os
    checkpoint_path = checkpoint_path or os.getenv("SAM_CHECKPOINT")
    if not checkpoint_path:
        raise RuntimeError("SAM 체크포인트 경로가 없습니다. `--sam_checkpoint` 또는 `SAM_CHECKPOINT`를 지정하세요.")
    fg = _sam_generate_fg_mask(image, checkpoint_path)
    bg = Image.eval(fg, lambda x: 255 - x)
    return _hard_binary(bg, 128)

# ---------------------------
# BEST: rembg 후 SAM으로 리파인
# ---------------------------
def _iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter) / float(union + 1e-6)

def best_auto_mask(image: Image.Image, checkpoint_path: Optional[str]) -> Image.Image:
    """
    1) rembg로 전경 대략 분리 → fg_rembg
    2) SAM으로 후보 생성 → fg_sam
    3) 둘의 교집합으로 하드하고 깔끔한 윤곽 유지 (필요시 IoU가 낮으면 rembg만 사용)
    최종 반환: 배경 마스크(배경=255, 전경=0)
    """
    # rembg 전경
    bg_rembg = rembg_auto_mask(image)            # 배경=255, 전경=0
    fg_rembg = Image.eval(bg_rembg, lambda x: 255 - x)

    # SAM 전경 (실패하면 rembg만)
    try:
        fg_sam = _sam_generate_fg_mask(image, checkpoint_path or "")
    except Exception:
        return bg_rembg  # rembg만으로

    A = (np.array(fg_rembg, dtype=np.uint8) >= 128)
    B = (np.array(fg_sam,   dtype=np.uint8) >= 128)

    iou = _iou(A, B)
    if iou < 0.2:  # 너무 동떨어지면 rembg만 사용
        fg_final = fg_rembg
    else:
        # 더 깔끔한 경계 보존을 위해 '교집합' 사용 (배경 포함 위험 ↓)
        C = (np.logical_and(A, B).astype(np.uint8) * 255)
        fg_final = Image.fromarray(C, "L")

    bg_final = Image.eval(fg_final, lambda x: 255 - x)
    return _hard_binary(bg_final, 128)

# ---------------------------
# 엔트리
# ---------------------------
def auto_mask(
    image: Image.Image,
    method: Literal["rembg", "sam", "best"] = "rembg",
    sam_checkpoint: Optional[str] = None
) -> Image.Image:
    """
    반환: 배경 마스크(배경=255, 전경=0) — 인페인트 마스크 규약
    """
    if method == "rembg":
        return rembg_auto_mask(image)
    if method == "sam":
        return sam_auto_mask(image, sam_checkpoint)
    # best = rembg → sam 리파인
    return best_auto_mask(image, sam_checkpoint)