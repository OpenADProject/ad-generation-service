# image_ai/io.py
from PIL import Image
from pathlib import Path
import json

def ensure_dir(p: str | Path):
    Path(p).mkdir(parents=True, exist_ok=True)

def load_image(path: str | Path) -> Image.Image:
    return Image.open(path).convert("RGB")

def save_png(img: Image.Image, path: str | Path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")

def divisible_by_8(w: int, h: int) -> tuple[int,int]:
    w8 = (w // 8) * 8
    h8 = (h // 8) * 8
    return max(8, w8), max(8, h8)

def parse_size(size: str | None, src: Image.Image | None = None) -> tuple[int,int]:
    if size:
        W, H = map(int, size.lower().split("x"))
    else:
        W, H = 1080, 1080
        if src is not None:
            ar = src.width / src.height
            if abs(ar - 1.0) > 0.15:
                W, H = (1080, 1352) if ar < 1 else (1344, 760)
    return divisible_by_8(W, H)

def dump_json(obj, path: str | Path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def fit_to_canvas(img: Image.Image, wh: tuple[int, int]) -> Image.Image:
    W, H = wh
    iw, ih = img.size
    scale = min(W / iw, H / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))

    resized = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H))

    avg = resized.resize((1, 1), Image.BILINEAR).getpixel((0, 0))
    canvas.paste(avg, (0, 0, W, H))

    ox, oy = (W - nw) // 2, (H - nh) // 2
    canvas.paste(resized, (ox, oy))
    return canvas