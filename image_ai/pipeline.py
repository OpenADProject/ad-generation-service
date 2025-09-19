# image_ai/pipeline.py
import argparse, json
from pathlib import Path
from PIL import Image
from .io import ensure_dir, load_image, save_png, parse_size, dump_json, fit_to_canvas
from .lmm import caption_or_concept
from .generator import ReconGenerator
from .flex_edit import FlexEditor

def _load_mask(mask_path: str | None, size: tuple[int,int]) -> Image.Image | None:
    """
    선택 마스크 로더: 흰=편집, 검=보존. 없으면 None (전체 편집).
    """
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
    # flex 전용 옵션
    prompt_override: str | None = None,
    style: str | None = None,
    mask: str | None = None,
    allow_deform: float = 0.5,
    ip_scale: float = 0.5,
    steps: int = 28,
    # recon 전용
    use_ip: str = "auto",
    noise_mode: str = "none",
    ref_mode: str = "ip_txt2img",   # "ip_txt2img" | "img2img"
    # 스타일 참조 (IP-Adapter 두 번째 입력)
    style_ref: str | None = None,
    ip_style_scale: float = 0.4,
):
    ensure_dir(out_dir)
    ref = load_image(in_image)
    W, H = parse_size(size, ref)

    # 1) 프롬프트 (concept 없으면 LMM 캡션으로 폴백)
    base_prompt = caption_or_concept(in_image, concept)

    if mode == "flex":
        # ---------- FLEX ----------
        prompt = prompt_override or base_prompt
        editor = FlexEditor(use_ip=True, use_controlnet=True)
        prod_mask = _load_mask(mask, (W, H))  # 없으면 전체 편집

        # flex에서도 원본을 뻥늘리지 말고 letterbox로 투입
        safe_ref = fit_to_canvas(ref, (W, H))
        result = editor.edit(
            image=safe_ref,
            product_mask=prod_mask,
            prompt=prompt,
            user_style=style,          # 예: "glossy ceramic finish, showroom lighting"
            allow_deform=allow_deform, # 0.3~0.7
            ip_scale=ip_scale,         # 0.4~0.7
            steps=steps,
            strength=strength,         # 0.5~0.7
            guidance=guidance,         # 5.5~7.5
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
            "paths": {"final": str(final_path)},
        }
        dump_json(meta, Path(out_dir, "meta.json"))
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return

    # ---------- RECON ----------
    prompt = (
        f"{base_prompt}, commercial advertising quality, coherent background, "
        f"product integrated into scene, proper lighting and shadows, no text"
    )
    gen = ReconGenerator()
    style_ref_img = load_image(style_ref) if style_ref else None

    result = gen.generate(
        ref_image=ref,
        prompt=prompt,
        size=(W, H),
        seed=seed,
        strength=strength,
        guidance_scale=guidance,
        steps=steps,
        ip_scale=ip_scale,
        use_ip=(None if use_ip=="auto" else use_ip=="true"),
        noise_mode=noise_mode,
        ref_mode=ref_mode,
        style_ref_image=style_ref_img,
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
        "guidance": guidance,
        "ip_adapter_used": gen.has_ip_adapter,
        "ip_adapter_error": getattr(gen, "ip_adapter_error", None),
        "style_ref_used": style_ref is not None,
        "paths": {"final": str(final_path)},
    }
    dump_json(meta, Path(out_dir, "meta.json"))
    print(json.dumps(meta, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="in_image", required=True, help="입력 이미지(제품)")
    p.add_argument("--out", dest="out_dir", default="ads_recon/runs/demo")
    p.add_argument("--size", type=str, default=None, help='예: "1080x1080" (미지정 시 자동)')
    p.add_argument("--concept", type=str, default=None, help="장면/배경 콘셉트(없으면 LMM 캡션)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--strength", type=float, default=0.55, help="변형 강도(0~1)")
    p.add_argument("--guidance", type=float, default=6.0, help="guidance scale")
    p.add_argument("--mode", type=str, default="recon", choices=["recon","flex"], help="recon=재구성, flex=느슨 편집")

    # flex 전용
    p.add_argument("--prompt", dest="prompt_override", type=str, default=None, help="flex에서 사용할 편집 프롬프트")
    p.add_argument("--style", type=str, default=None, help="추가 스타일(선택)")
    p.add_argument("--mask", type=str, default=None, help="편집 마스크 경로(L, 흰=편집/검=보존)")
    p.add_argument("--allow_deform", type=float, default=0.5, help="윤곽 제약 완화(0~1)")
    p.add_argument("--ip_scale", type=float, default=0.5, help="아이덴티티 고정 강도(0~1)")
    p.add_argument("--steps", type=int, default=28)

    # recon 전용
    p.add_argument("--use_ip", type=str, default="auto", choices=["auto", "true", "false"], help="IP-Adapter 사용 여부(auto/true/false)")
    p.add_argument("--noise_mode", type=str, default="none", choices=["none", "soft", "strong"], help="초기 노이즈 주입 모드")
    p.add_argument("--ref_mode", type=str, default="ip_txt2img", choices=["ip_txt2img","img2img"], help="recon에서 원본을 참조만 하고 새로 합성할지 여부")
    p.add_argument("--style_ref", type=str, default=None, help="스타일/무드 레퍼런스 이미지 경로")
    p.add_argument("--ip_style_scale", type=float, default=0.4, help="스타일 참조 강도(0~1)")

    args = p.parse_args()
    run(
        args.in_image, args.out_dir, args.size, args.concept, args.seed,
        args.strength, args.guidance, args.mode,
        args.prompt_override, args.style, args.mask,
        args.allow_deform, args.ip_scale, args.steps,
        args.use_ip, args.noise_mode, args.ref_mode,
        args.style_ref, args.ip_style_scale
    )