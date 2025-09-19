# image_ai/pipeline.py
import os
import argparse
import json
from pathlib import Path
from PIL import Image

from .io import (
    ensure_dir,
    load_image,
    save_png,
    parse_size,
    dump_json,
    fit_to_canvas,
)
from .lmm import caption_or_concept
from .generator import ReconGenerator      # SD3.5 Medium / 또는 HF API 라우팅 포함
from .flex_edit import FlexEditor          # SDXL Inpaint + ControlNet (+ HF API 가능)

def _load_mask(mask_path: str | None, size: tuple[int, int]) -> Image.Image | None:
    if not mask_path:
        return None
    m = Image.open(mask_path).convert("L")
    if m.size != size:
        m = m.resize(size, Image.NEAREST)
    return m

def run(
    in_image: str,
    out_dir: str,
    size: str | None,
    concept: str | None,
    seed: int,
    strength: float,
    guidance: float,
    mode: str = "recon",
    # flex 전용
    prompt_override: str | None = None,
    style: str | None = None,
    mask: str | None = None,
    allow_deform: float = 0.5,
    ip_scale: float = 0.5,
    steps: int = 24,
    # recon 전용
    use_ip: str = "auto",
    noise_mode: str = "none",
    ref_mode: str = "ip_txt2img",
    style_ref: str | None = None,
    ip_style_scale: float = 0.4,
):
    ensure_dir(out_dir)

    # 입력 이미지 & 사이즈
    ref = load_image(in_image)
    W, H = parse_size(size, ref)

    # API 제공자 힌트 (로컬 / HF)
    provider = os.getenv("ADSGEN_API_PROVIDER", "").lower().strip()
    is_hf_api = provider == "hf"

    # 1) 프롬프트 (concept 없으면 LMM 캡션 폴백)
    base_prompt = caption_or_concept(in_image, concept)

    # -----------------------------
    # FLEX (SDXL Inpaint + ControlNet)
    # -----------------------------
    if mode == "flex":
        prompt = prompt_override or base_prompt

        editor = FlexEditor(use_ip=True, use_controlnet=True)
        prod_mask = _load_mask(mask, (W, H))

        # 원본 비율 유지해서 캔버스에 안전히 투입
        safe_ref = fit_to_canvas(ref, (W, H))

        result = editor.edit(
            image=safe_ref,
            product_mask=prod_mask,
            prompt=prompt,
            user_style=style,
            allow_deform=allow_deform,
            ip_scale=ip_scale,
            steps=steps,
            strength=strength,
            guidance=guidance,
            seed=seed,
        )

        final_path = Path(out_dir, "final.png")
        save_png(result, final_path)

        meta = {
            "mode": "flex",
            "size": [W, H],
            "prompt_base": base_prompt,
            "prompt_used": prompt if not style else f"{prompt}, {style}",
            "seed": seed,
            "strength": strength,
            "guidance": guidance,
            "allow_deform": allow_deform,
            "ip_scale": ip_scale,
            "steps": steps,
            "provider": provider or "local",
            "paths": {"final": str(final_path)},
        }
        dump_json(meta, Path(out_dir, "meta.json"))
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return

    # -----------------------------
    # RECON (SD3.5 Medium / or HF API)
    # -----------------------------
    # 로컬 SD3.5 Medium 경로일 때는 합성용 보일러플레이트를 좀 더 붙임
    prompt = (
        f"{base_prompt}, commercial advertising quality, coherent background, "
        f"product integrated into scene, proper lighting and shadows, no text"
    )

    gen = ReconGenerator()

    # HF API(Turbo 등) 사용 시엔 스텝/가이던스를 그대로 전달
    # 로컬 SD3.5 Medium일 땐 권장 범위로 클램핑
    effective_steps = steps
    effective_guidance = guidance
    if not is_hf_api:
        # SD3.5 Medium 권장 스텝 18~28
        effective_steps = max(18, min(28, steps))

    result = gen.generate(
        ref_image=ref,
        prompt=prompt,
        size=(W, H),
        seed=seed,
        strength=strength,
        guidance_scale=effective_guidance,
        steps=effective_steps,
        ip_scale=ip_scale,
        use_ip=(None if use_ip == "auto" else use_ip == "true"),
        noise_mode=noise_mode,
        ref_mode=ref_mode,
        style_ref_image=None,
        ip_style_scale=ip_style_scale,
    )

    final_path = Path(out_dir, "final.png")
    save_png(result, final_path)

    meta = {
        "mode": "recon",
        "size": [W, H],
        "prompt": base_prompt,
        "seed": seed,
        "strength": strength,
        "guidance": effective_guidance,
        "steps": effective_steps,
        "provider": provider or "local",
        "hf_model": os.getenv("ADSGEN_HF_TXT2IMG_MODEL", None) if is_hf_api else None,
        "ip_adapter_used": getattr(gen, "has_ip_adapter", False),
        "ip_adapter_error": getattr(gen, "ip_adapter_error", None),
        "style_ref_used": False,
        "paths": {"final": str(final_path)},
    }
    dump_json(meta, Path(out_dir, "meta.json"))
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_image", required=True)
    p.add_argument("--out", dest="out_dir", default="ads_recon/runs/demo")
    p.add_argument("--size", type=str, default=None)
    p.add_argument("--concept", type=str, default=None)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--strength", type=float, default=0.55)
    p.add_argument("--guidance", type=float, default=6.0)
    p.add_argument("--mode", type=str, default="recon", choices=["recon", "flex"])

    # flex 전용
    p.add_argument("--prompt", dest="prompt_override", type=str, default=None)
    p.add_argument("--style", type=str, default=None)
    p.add_argument("--mask", type=str, default=None)
    p.add_argument("--allow_deform", type=float, default=0.5)
    p.add_argument("--ip_scale", type=float, default=0.6)
    p.add_argument("--steps", type=int, default=24)

    # recon 전용
    p.add_argument("--use_ip", type=str, default="auto", choices=["auto", "true", "false"])
    p.add_argument("--noise_mode", type=str, default="none", choices=["none", "soft", "strong"])
    p.add_argument("--ref_mode", type=str, default="ip_txt2img", choices=["ip_txt2img", "img2img"])
    p.add_argument("--style_ref", type=str, default=None)
    p.add_argument("--ip_style_scale", type=float, default=0.4)

    args = p.parse_args()
    run(
        args.in_image,
        args.out_dir,
        args.size,
        args.concept,
        args.seed,
        args.strength,
        args.guidance,
        args.mode,
        args.prompt_override,
        args.style,
        args.mask,
        args.allow_deform,
        args.ip_scale,
        args.steps,
        args.use_ip,
        args.noise_mode,
        args.ref_mode,
        args.style_ref,
        args.ip_style_scale,
    )