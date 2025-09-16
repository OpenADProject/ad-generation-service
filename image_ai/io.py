# image_ai/io.py
from PIL import Image
from pathlib import Path
import json, os

def ensure_dir(p: str | Path):
    Path(p).mkdir(parents=True, exist_ok=True)

def load_image(path: str | Path) -> Image.Image:
    return Image.open(path).convert("RGB")

def save_png(img: Image.Image, path: str | Path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")

def divisible_by_8(w: int, h: int) -> tuple[int,int]:
    # SDXL 제약: 8로 나눠떨어져야 함
    w8 = (w // 8) * 8
    h8 = (h // 8) * 8
    return max(8, w8), max(8, h8)

def parse_size(size: str | None, src: Image.Image | None = None) -> tuple[int,int]:
    if size:
        W, H = map(int, size.lower().split("x"))
    else:
        # 기본 인스타 1:1
        W, H = 1080, 1080
        if src is not None:
            ar = src.width / src.height
            if abs(ar - 1.0) > 0.15:
                # 원본 비율이 많이 다르면 4:5 혹은 16:9로 맞춤
                W, H = (1080, 1352) if ar < 1 else (1344, 760)
    return divisible_by_8(W, H)

def dump_json(obj, path: str | Path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def fit_to_canvas(img: Image.Image, wh: tuple[int, int]) -> Image.Image:
    """
    종횡비 유지 + 패딩(letterbox)으로 목표 캔버스(8의 배수)에 맞춤.
    - 원본을 절대 찌그러뜨리지 않음
    - 빈 공간은 평균 색으로 채워 자연스럽게 보정
    """
    W, H = wh
    iw, ih = img.size
    scale = min(W / iw, H / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))

    resized = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H))

    # 배경색은 resized 평균색
    avg = resized.resize((1, 1), Image.BILINEAR).getpixel((0, 0))
    canvas.paste(avg, (0, 0, W, H))

    ox, oy = (W - nw) // 2, (H - nh) // 2
    canvas.paste(resized, (ox, oy))
    return canvas