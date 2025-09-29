# =======================================
# pipeline.py — 안정성 보완 포함된 버전
# =======================================
# 광고 이미지 만들 때 쓰는 파이프라인 코드
# =======================================

import os
import io
import base64
import logging
import torch
import torch.nn.functional as F
from PIL import Image

import config
from transformers import CLIPVisionModelWithProjection
from diffusers import (
    StableDiffusionXLPipeline,
    StableDiffusionXLImg2ImgPipeline,
    AutoencoderKL,
)

from prompt_utils import encode_prompt_sdxl, build_ad_prompt_compose, KeywordExtractor

# -------------------------------
# Helpers (잡다한 도우미 함수들)
# -------------------------------

def _weighted(text: str, w: float = 1.25) -> str:
    # 프롬프트에서 특정 단어 강조하려고 쓰는 함수
    clean = " ".join(text.split())
    return f"({clean}:{w:.2f})"

def _clip_fit(tokenizer, text: str, max_tokens: int) -> str:
    # 토큰 길이 제한 걸어서 자르는 함수
    if tokenizer is None:
        return text
    enc = tokenizer(text, add_special_tokens=True, padding=False, truncation=False, return_tensors="pt")
    if int(enc.input_ids.shape[1]) <= max_tokens:
        return text
    lo, hi = 1, len(text)
    best = text
    while lo <= hi:
        mid = (lo + hi) // 2
        cand = text[:mid].rstrip()
        enc = tokenizer(cand, add_special_tokens=True, padding=False, truncation=False, return_tensors="pt")
        if int(enc.input_ids.shape[1]) <= max_tokens:
            best = cand
            lo = mid + 1
        else:
            hi = mid - 1
    return best

def _clip_text_embed(pipe, text: str):
    # 텍스트를 CLIP으로 벡터화 하는 부분 (프롬프트 비교용)
    te = getattr(pipe, "text_encoder_2", None) or getattr(pipe, "text_encoder", None)
    tok = getattr(pipe, "tokenizer_2", None) or getattr(pipe, "tokenizer", None)
    if te is None or tok is None:
        raise RuntimeError("No text encoder/tokenizer on pipeline")

    inputs = tok(text, return_tensors="pt", padding=True, truncation=True,
                 max_length=tok.model_max_length).to(pipe.device)
    with torch.no_grad():
        out = te(**inputs, output_hidden_states=True)
        pooled = out[0]
    return F.normalize(pooled, dim=-1)

def _intent_action_score(pipe, user_text: str) -> float:
    # 프롬프트가 "행동(잡고 있음)"인지 "정적(그냥 놓여있음)"인지 점수 계산
    act_refs = [
        "subject physically holding the product",
        "clear hand or paw gripping the item",
        "tactile interaction with the object",
        "posing while holding the product close",
    ]
    static_refs = [
        "static studio product photo without interaction",
        "product centered, model nearby but not touching",
        "clean catalog shot, no action or holding",
        "non-interactive advertisement still",
    ]

    q = _clip_text_embed(pipe, user_text)

    act = torch.stack([_clip_text_embed(pipe, t).squeeze(0) for t in act_refs], dim=0).mean(dim=0, keepdim=True)
    sta = torch.stack([_clip_text_embed(pipe, t).squeeze(0) for t in static_refs], dim=0).mean(dim=0, keepdim=True)
    act = F.normalize(act, dim=-1)
    sta = F.normalize(sta, dim=-1)

    s_act = float((q @ act.T).squeeze())
    s_sta = float((q @ sta.T).squeeze())
    score = (s_act - s_sta) * 0.5 + 0.5
    return max(0.0, min(1.0, score))


# -------------------------------
# OutputManager (이미지 저장 담당)
# -------------------------------
class OutputManager:
    def __init__(self, output_dir="outputs", logger=None):
        self.output_dir = output_dir
        self.logger = logger or logging.getLogger("AdImagePipeline")
        os.makedirs(self.output_dir, exist_ok=True)

    def save(self, image: Image.Image, base_filename: str) -> str:
        # 이미지 파일로 저장
        path = os.path.join(self.output_dir, f"{base_filename}.png")
        image.save(path)
        if self.logger:
            self.logger.info(f"Image saved to {path}")
        return path

    def to_base64(self, image: Image.Image) -> str:
        # 이미지를 base64로 변환 (API 응답용)
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")


# -------------------------------
# ModelManager (모델 관리)
# -------------------------------
class ModelManager:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.loaded_models = {}
        self.logger.info(f"[ModelManager] Initialized. Device: {config.DEVICE}, DType: {config.TORCH_DTYPE}")

    def _bytes_to_mb(self, b): return round(b / (1024**2), 2)

    def load_model(self, key, model_class, model_path, use_fp16_variant=False, **kwargs):
        # 모델 로드 (캐시 있으면 재사용)
        if key in self.loaded_models:
            return self.loaded_models[key]
        self.logger.info(f"Loading model '{key}' from {model_path}...")
        if model_path is not None and not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path not found: {model_path}")

        vram_before = torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
        pretrained_kwargs = {"torch_dtype": self.config.TORCH_DTYPE, "use_safetensors": True, **kwargs}
        if use_fp16_variant:
            pretrained_kwargs["variant"] = "fp16"

        model = model_class.from_pretrained(model_path, **pretrained_kwargs)
        if hasattr(model, "to"):
            model.to(self.config.DEVICE)

        if torch.cuda.is_available():
            vram_after = torch.cuda.memory_allocated()
            self.logger.info(f"Model '{key}' loaded. +{self._bytes_to_mb(vram_after - vram_before)} MB")
        self.loaded_models[key] = model
        return model

    def unload(self, *keys):
        # 모델 메모리 해제
        keys_to_unload = keys if keys else list(self.loaded_models.keys())
        for k in keys_to_unload:
            if k in self.loaded_models:
                del self.loaded_models[k]
                self.logger.info(f"Model '{k}' unloaded.")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# -------------------------------
# Main Pipeline (실제 실행 부분)
# -------------------------------
class ImageGenerationPipeline:
    def __init__(self, config, logger, output_dir="outputs"):
        self.config = config
        self.logger = logger
        self.model_manager = ModelManager(config, logger)
        self.output_manager = OutputManager(output_dir=output_dir, logger=logger)
        # 공통 네거티브 프롬프트 (안나왔으면 하는 요소들)
        self.negative_prompt = (
            "blurry, low quality, deformed, disfigured, watermark, text, signature, "
            "overprocessed, oversaturated, cheesy, "
            "collage, tiled layout, grid layout, split frame, split-screen, diptych, triptych, "
            "panels, storyboard, montage, photo montage, multiple frames, picture-in-picture, "
            "generic stock photo look, overly corporate studio advertisement"
        )

    def run(self, inputs):
        try:
            self.logger.info("===== STEP 0: SETUP =====")
            user_prompt = inputs.get("prompt", "a clean product photo")
            params = inputs.get("params", {}) or {}
            background_text = (params.get("background") or "").strip()

            # 브랜드 정체성 강조 단어
            identity_anchors = [
                _weighted("authentic small business branding", 1.35),
                _weighted("human touch, made with care", 1.30),
                _weighted("cozy neighborhood store atmosphere", 1.25),
            ]
            # 배경 관련 단어
            bg_anchors = []
            if background_text:
                bg_kw = KeywordExtractor(getattr(self.config, "OPENAI_API_KEY", None), logger=self.logger).extract(background_text)
                parts = [w.strip() for w in bg_kw.split(",")[:6]]
                bg_kw = ", ".join(parts) or "natural background"
                bg_anchors.append(_weighted(bg_kw, 1.15))

            # 앵커 앞에 붙여서 프롬프트 강화
            if identity_anchors or bg_anchors:
                user_prompt = f"{', '.join(identity_anchors + bg_anchors)}. {user_prompt}"

            self.logger.info(f"[PROMPT/POS] {user_prompt}")
            self.logger.info(f"[PROMPT/NEG] {self.negative_prompt}")

            # 입력 이미지 불러오기
            product_image = self._load_b64(inputs.get("product_image"))
            model_image = self._load_b64(inputs.get("model_image"))

            width, height = map(int, params["size"].split("x"))
            seed = params.get("seed", 12345)
            generator = torch.Generator(device=self.config.DEVICE).manual_seed(seed)
            self.logger.info(f"Input loaded. {width}x{height}, seed={seed}")

            # 기본 모델 로드
            image_encoder = CLIPVisionModelWithProjection.from_pretrained(
                self.config.IP_ADAPTER_IMAGE_ENCODER_PATH,
                torch_dtype=self.config.TORCH_DTYPE,
                local_files_only=True
            ).to(self.config.DEVICE)
            vae = self.model_manager.load_model("vae", AutoencoderKL, self.config.VAE_PATH)
            pipe = self.model_manager.load_model(
                "pipe_base",
                StableDiffusionXLPipeline,
                self.config.SDXL_BASE_MODEL_PATH,
                image_encoder=image_encoder,
                vae=vae,
                use_fp16_variant=True
            )

            # 액션/정적 판단
            action_score = _intent_action_score(pipe, user_prompt)
            is_action = (action_score >= 0.55)
            self.logger.info(f"[INTENT] score={action_score:.3f}, is_action={is_action}")

            # IP-Adapter 불러오기
            ip_root = self.config.IP_ADAPTER_BASE_PATH
            weight_name = os.path.basename(self.config.IP_ADAPTER_WEIGHTS_PATH)
            subfolder = os.path.relpath(os.path.dirname(self.config.IP_ADAPTER_WEIGHTS_PATH), ip_root)
            self.logger.info(f"Loading IP-Adapter: root={ip_root}, subfolder={subfolder}, weight={weight_name}")
            pipe.load_ip_adapter(
                ip_root,
                subfolder=subfolder,
                weight_name=weight_name,
                image_encoder_folder=self.config.IP_ADAPTER_IMAGE_ENCODER_PATH,
                local_files_only=True
            )

            # 안전 체크 (IP-Adapter가 제대로 로드됐는지 확인)
            has_ip = False
            try:
                encproj = getattr(pipe.unet, "encoder_hid_proj", None)
                if encproj is not None and hasattr(encproj, "image_projection_layers"):
                    has_ip = True
            except Exception:
                has_ip = False
            self.logger.info(f"[IP-GUARD] has_ip={has_ip}")

            # conditioning 이미지 만들기
            ip_image = None
            if model_image is not None and product_image is not None:
                ip_image = self._merge_side_by_side(model_image, product_image, target_height=512)
                cond_desc = "merged"
            elif model_image is not None:
                ip_image, cond_desc = model_image, "model_only"
            elif product_image is not None:
                ip_image, cond_desc = product_image, "product_only"
            else:
                raise ValueError("Need at least one image")

            # scale 값 설정
            if cond_desc == "product_only":
                ip_scale = 0.50
            elif cond_desc == "merged":
                ip_scale = 0.20
            else:
                ip_scale = 0.15
            if is_action:
                ip_scale = min(ip_scale, 0.30)
            if has_ip:
                pipe.set_ip_adapter_scale(ip_scale)
            else:
                self.logger.warning("Skipping set_ip_adapter_scale because has_ip=False")

            # anchors_text 추가
            tok = getattr(pipe, "tokenizer_2", None) or getattr(pipe, "tokenizer", None)
            anchors_text = _clip_fit(tok, ", ".join(identity_anchors + bg_anchors), max_tokens=16)
            if anchors_text:
                user_prompt = f"{anchors_text}. {user_prompt}"

            # 레이아웃 규칙
            if is_action:
                layout_fixed = (
                    "one photograph, continuous background; "
                    "subject physically holding the product; tactile contact; "
                    "single product only; eye-level camera; natural soft light"
                )
            else:
                layout_fixed = (
                    "one photograph, continuous background; "
                    "center composition: product at center; model nearby; "
                    "eye-level camera; high readability"
                )
            if bg_anchors:
                layout_fixed += "; " + ", ".join(bg_anchors)

            # 최종 프롬프트 조립
            ad_prompt = build_ad_prompt_compose(
                tokenizer=tok,
                user_prompt=user_prompt,
                brand=params.get("brand_name"),
                product=params.get("product"),
                tone="authentic, warm",
                layout_hint=layout_fixed,
                cta="",
                brand_colors="",
                style_hints=[],
                ad_strength=0.45,
                openai_api_key=getattr(self.config, "OPENAI_API_KEY", None),
                logger=self.logger,
                user_budget=36,
                guide_budget=24
            )

            # 프롬프트 인코딩
            prompt_embeds = encode_prompt_sdxl(pipe, ad_prompt, self.negative_prompt, debug=True, logger=self.logger)

            # 이미지 생성
            gen_kwargs = {
                **prompt_embeds,
                "num_inference_steps": 32,
                "width": width,
                "height": height,
                "generator": generator,
            }
            if has_ip:
                gen_kwargs["ip_adapter_image"] = ip_image

            self.logger.info(f"[RUN] cond={cond_desc}, ip_scale={ip_scale}, has_ip={has_ip}")
            image = pipe(**gen_kwargs).images[0]
            self.output_manager.save(image, "01_direct_generation_output")

            # Refiner (선택)
            if params.get("use_refiner", False):
                refiner = self.model_manager.load_model(
                    "refiner",
                    StableDiffusionXLImg2ImgPipeline,
                    self.config.REFINER_MODEL_PATH,
                    use_fp16_variant=True,
                    vae=vae
                )
                ref_embeds = encode_prompt_sdxl(refiner, ad_prompt, self.negative_prompt, debug=True, logger=self.logger)
                image = refiner(**ref_embeds, image=image, strength=self.config.REFINER_STRENGTH, generator=generator).images[0]
                self.output_manager.save(image, "02_refined_output")

            # 출력
            if params.get("file_saved", False):
                path = self.output_manager.save(image, "final_ad")
                return {"status": "success", "filepath": path}
            else:
                return {"status": "success", "image_base64": self.output_manager.to_base64(image)}

        finally:
            self.model_manager.unload()

    # -------------------------------
    # 내부 유틸
    # -------------------------------
    def _load_b64(self, b64_str):
        if not b64_str:
            return None
        return Image.open(io.BytesIO(base64.b64decode(b64_str))).convert("RGB")

    def _merge_side_by_side(self, left: Image.Image, right: Image.Image, target_height: int = 512) -> Image.Image:
        # 두 이미지를 나란히 붙여서 하나로 합치기
        if left.mode != "RGB": left = left.convert("RGB")
        if right.mode != "RGB": right = right.convert("RGB")
        def _resize(img, h):
            w = int(round(img.width * (h / img.height)))
            return img.resize((w, h), Image.LANCZOS)
        L, R = _resize(left, target_height), _resize(right, target_height)
        merged = Image.new("RGB", (L.width + R.width, target_height), (255, 255, 255))
        merged.paste(L, (0, 0))
        merged.paste(R, (L.width, 0))
        return merged