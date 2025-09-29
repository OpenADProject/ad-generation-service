# prompt_utils.py
# JSON 스키마 변경 없이 pipeline에서 그대로 사용할 수 있도록,
# 내부 로직(카테고리 분류 → 규칙 주입 → 키워드 압축 → 77토큰 예산)만 강화한 버전.

from __future__ import annotations
import os
import re
import torch
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

# OpenAI (>=1.0) 호환
_HAS_OPENAI = True
try:
    from openai import OpenAI
except Exception:
    _HAS_OPENAI = False
    OpenAI = None  # type: ignore


def _log(logger, msg: str):
    if logger is None:
        print(msg)
    else:
        logger.info(msg)


# -------------------------------
# 텍스트 전처리/토큰 도우미
# -------------------------------
def _truncate_chars(text: str, limit: int) -> str:
    if limit and len(text) > limit:
        return text[:limit].rstrip()
    return text

def clip_token_len(tokenizer, text: str) -> int:
    """CLIP 토크나이저로 토큰 길이 계산 (truncation=False)."""
    enc = tokenizer(
        text,
        add_special_tokens=True,
        padding=False,
        truncation=False,
        return_tensors="pt",
    )
    return int(enc.input_ids.shape[1])

def _binary_shrink_by_chars(tokenizer, text: str, max_tokens: int) -> str:
    """마지막 수단: 글자 단위 이분탐색으로 max_tokens 이하가 되도록 자름."""
    lo, hi = 1, len(text)
    best = text
    while lo <= hi:
        mid = (lo + hi) // 2
        cand = text[:mid].rstrip()
        if clip_token_len(tokenizer, cand) <= max_tokens:
            best = cand
            lo = mid + 1
        else:
            hi = mid - 1
    return best


# -------------------------------
# 카테고리 분류 (룰 → LLM 백업)
# -------------------------------
# 1) 라이트한 온톨로지: 키워드 → 카테고리
_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "pet": ["pet", "animal", "dog", "cat", "puppy", "kitten", "hamster", "pet toy", "leash", "pet bed"],
    "food": ["food", "fruit", "banana", "coffee", "latte", "bread", "croissant", "cake", "dessert", "drink", "beverage"],
    "fashion": ["fashion", "shoe", "sneaker", "heel", "apparel", "t-shirt", "jacket", "bag", "wallet"],
    "beauty": ["cosmetic", "skincare", "lipstick", "perfume", "makeup", "serum", "cream"],
    "tech": ["phone", "laptop", "camera", "headphone", "earbuds", "gadget", "tablet"],
    "home_decor": ["vase", "candle", "ceramic", "interior", "home decor", "sofa", "chair", "lamp"],
    "jewelry": ["jewelry", "ring", "necklace", "bracelet", "earring", "accessory"],
    "toy": ["toy", "kids toy", "figure", "puzzle", "boardgame"],
    "stationery": ["notebook", "pen", "pencil", "stationery", "planner", "journal"],
    "plant": ["plant", "flower", "bouquet", "succulent"],
    "fitness": ["fitness", "yoga", "dumbbell", "gym", "workout", "supplement"],
}

# 2) 카테고리별 스타일 힌트/네거티브 룰
_CATEGORY_RULES: Dict[str, Dict[str, List[str]]] = {
    "pet": {
        "style": [
            "natural", "cozy", "warm", "soft light", "shallow depth of field"
        ],
        "negative": [
            "packaged pet food", "kibble", "nutrition facts panel", "barcode",
            "text overlay", "watermark", "stock photo logo"
        ],
    },
    "food": {
        "style": [
            "photorealistic", "vibrant colors", "close-up product shot",
            "golden hour sunlight", "soft shadows", "steam realism"
        ],
        "negative": [
            "cartoon food icon", "fake plastic look", "overly saturated",
            "text overlay", "watermark", "stock photo logo"
        ],
    },
    "fashion": {
        "style": [
            "minimalist", "modern", "studio lighting", "soft shadows",
            "symmetrical composition", "high resolution", "sharp focus"
        ],
        "negative": [
            "mannequin", "wrinkled clothes", "messy background",
            "text overlay", "watermark", "stock photo logo"
        ],
    },
    "beauty": {
        "style": [
            "premium look", "clean hero shot", "soft diffusion",
            "high readability", "product shot on marble"
        ],
        "negative": [
            "smudged label", "barcode close-up", "ingredient list",
            "text overlay", "watermark", "stock photo logo"
        ],
    },
    "tech": {
        "style": [
            "sleek", "modern", "studio lighting", "specular highlights",
            "clean background", "premium look"
        ],
        "negative": [
            "low-res screen mock", "glare reflections", "fingerprints",
            "text overlay", "watermark", "stock photo logo"
        ],
    },
    "home_decor": {
        "style": [
            "natural light", "warm", "cozy", "interior styling",
            "bokeh", "soft film grain"
        ],
        "negative": [
            "cluttered background", "harsh flash",
            "text overlay", "watermark", "stock photo logo"
        ],
    },
    "jewelry": {
        "style": [
            "macro detail", "sparkle highlights", "soft shadows",
            "minimal backdrop", "premium"
        ],
        "negative": [
            "skin blemish close-up", "fingerprints", "dust",
            "text overlay", "watermark", "stock photo logo"
        ],
    },
    "toy": {
        "style": [
            "playful", "colorful", "clean hero shot",
            "soft light", "high readability"
        ],
        "negative": [
            "choking hazard imagery", "damaged packaging",
            "text overlay", "watermark", "stock photo logo"
        ],
    },
    "stationery": {
        "style": [
            "flat lay", "minimalist", "clean composition",
            "soft daylight", "sharp focus"
        ],
        "negative": [
            "messy desk", "crumpled paper",
            "text overlay", "watermark", "stock photo logo"
        ],
    },
    "plant": {
        "style": [
            "natural light", "fresh", "dewy look",
            "bokeh", "shallow depth of field"
        ],
        "negative": [
            "wilted leaves", "overly artificial color",
            "text overlay", "watermark", "stock photo logo"
        ],
    },
    "fitness": {
        "style": [
            "dynamic", "energetic", "studio lighting",
            "clear product branding area", "high contrast"
        ],
        "negative": [
            "sweat stains close-up", "unsafe posture",
            "text overlay", "watermark", "stock photo logo"
        ],
    },
}

# 3) 분류 결과 컨테이너
@dataclass
class CategoryResult:
    categories: List[str]
    style_hints: List[str]
    negatives: List[str]


def _rule_based_categories(text: str) -> List[str]:
    t = (text or "").lower()
    found: List[str] = []
    for cat, words in _CATEGORY_KEYWORDS.items():
        for w in words:
            if w in t:
                found.append(cat)
                break
    # 우선순위: pet>food>fashion>beauty>tech>home_decor>jewelry>toy>stationery>plant>fitness
    order = list(_CATEGORY_KEYWORDS.keys())
    found = sorted(set(found), key=lambda c: order.index(c))
    return found


def _llm_categories(client: Optional[OpenAI], text: str, logger=None) -> List[str]:
    """OpenAI로 카테고리 분류 보강 (실패시 빈 리스트)."""
    if not client:
        return []
    label_space = ", ".join(_CATEGORY_RULES.keys())
    try:
        sys = (
            "Classify the product/scene into 1-3 categories from the given list. "
            "Return ONLY a JSON array of category strings from the list. No explanation."
        )
        usr = f"Text: {text}\nCategories: [{label_space}]"
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":sys},{"role":"user","content":usr}],
            temperature=0.0,
            max_tokens=60,
        )
        raw = (resp.choices[0].message.content or "").strip()
        # 매우 단순 파서: ["food","pet"] 형태 기대
        cats = re.findall(r'"([a-z_]+)"', raw.lower())
        cats = [c for c in cats if c in _CATEGORY_RULES]
        if logger: _log(logger, f"[CAT/LLM] {cats} (raw={raw})")
        return list(dict.fromkeys(cats))[:3]
    except Exception as e:
        if logger: _log(logger, f"[CAT/LLM] failed: {e}")
        return []


def classify_categories(user_prompt: str, openai_api_key: Optional[str], logger=None) -> CategoryResult:
    cats = _rule_based_categories(user_prompt)
    client = OpenAI(api_key=openai_api_key) if (openai_api_key and _HAS_OPENAI) else None
    if not cats:
        cats = _llm_categories(client, user_prompt, logger=logger)

    # 카테고리별 룰 모음
    style: List[str] = []
    negs: List[str] = []
    for c in cats or []:
        rules = _CATEGORY_RULES.get(c, {})
        style += rules.get("style", [])
        negs += rules.get("negative", [])

    # 공통 네거티브(광고 사진 안전장치)
    common_neg = ["watermark", "text overlay", "stock photo logo", "cheesy", "overprocessed", "oversaturated"]
    negs = list(dict.fromkeys([*negs, *common_neg]))
    style = list(dict.fromkeys(style))

    if logger:
        _log(logger, f"[CAT/FINAL] cats={cats or ['general']} style={style} neg={negs}")
    return CategoryResult(categories=cats or ["general"], style_hints=style, negatives=negs)


# -------------------------------
# 키워드 추출기 (LLM → 로컬 폴백)
# -------------------------------
class KeywordExtractor:
    def __init__(self, api_key: Optional[str], model: str = "gpt-4o-mini", logger=None):
        self.logger = logger
        self.enabled = bool(api_key and _HAS_OPENAI)
        self.model = model
        self.client = OpenAI(api_key=api_key) if self.enabled else None

    def _local_fallback(self, text: str) -> str:
        # 아주 단순한 로컬 키워드 추출(쉼표/공백 기준 + 불용어 제거 비슷하게)
        t = re.sub(r"[^\w\s가-힣,/-]+", " ", text.lower())
        parts = [p.strip() for p in re.split(r"[,/ ]+", t) if p.strip()]
        # 너무 일반적인 단어 몇 개 제거
        stop = {"the","a","an","of","and","with","for","in","on","at","to","from","this","that"}
        parts = [p for p in parts if p not in stop and len(p) >= 2]
        # 상위 20개만
        out = ", ".join(parts[:20]) if parts else "product hero, clean background"
        if self.logger: _log(self.logger, f"[PROMPT/KEYS] local='{out}'")
        return out

    def extract(self, user_prompt: str, brand: str|None=None, product: str|None=None) -> str:
        text = (user_prompt or "").strip()
        if not text:
            base = "product hero, clean background"
            if self.logger: _log(self.logger, f"[PROMPT/KEYS] fallback='{base}'")
            return base

        if self.enabled and self.client:
            try:
                sys = (
                    "Compress inputs for SDXL/CLIP: return ONLY a single comma-separated English keyword list, "
                    "<=35 words, no sentences. Prefer ad-photography terms; avoid stopwords/pronouns."
                )
                usr = f"User prompt: '''{text}'''\nBrand: {brand or '-'}\nProduct: {product or '-'}\nOutput: comma-separated keywords."
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role":"system","content":sys},{"role":"user","content":usr}],
                    max_tokens=120, temperature=0.2
                )
                out = resp.choices[0].message.content.strip()
                out = re.sub(r"[\n;]+", ", ", out)
                parts = [p.strip() for p in out.split(",") if p.strip()]
                out = ", ".join(parts[:35]) or self._local_fallback(text)
                if self.logger: _log(self.logger, f"[PROMPT/KEYS] openai='{out}'")
                return out
            except Exception as e:
                if self.logger: _log(self.logger, f"[PROMPT/KEYS] OpenAI failed: {e}; falling back")

        return self._local_fallback(text)


# -------------------------------
# SDXL 임베딩 (기존 함수 유지, 로깅 강화)
# -------------------------------
def _token_debug(tokenizer, text, name, logger):
    enc = tokenizer(
        text,
        padding="max_length",
        max_length=tokenizer.model_max_length,
        truncation=True,
        return_overflowing_tokens=True,
        return_tensors="pt",
    )
    ids = enc.input_ids[0]
    pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else 0
    used_len = int((ids != pad_id).sum().item())
    max_len = tokenizer.model_max_length
    overflow_cnt = len(enc.get("overflowing_tokens", []))
    try:
        tokens_preview = tokenizer.convert_ids_to_tokens(ids[:24].tolist())
    except Exception:
        tokens_preview = []

    _log(logger, f"[TOK] {name}: used_len={used_len}/{max_len}, truncated={overflow_cnt>0}, overflow_slices={overflow_cnt}")
    _log(logger, f"[TOK] {name}: ids_head={ids[:24].tolist()}")
    _log(logger, f"[TOK] {name}: tokens_head={tokens_preview}")
    return enc


def encode_prompt_sdxl(
    pipe,
    prompt,
    negative_prompt,
    num_images_per_prompt=1,
    do_classifier_free_guidance=True,
    debug=False,
    logger=None,
):
    """
    SDXL Base/Refiner 공용 인코딩.
    - pipe.encode_prompt 가 있으면 우선 사용 (가장 안전)
    - 없으면 수동 인코딩 (hidden_states[-2], pooled은 output[0] 이용)
    """
    if hasattr(pipe, "encode_prompt"):
        if debug:
            _log(logger, "[ENC] Using pipe.encode_prompt (built-in)")
        out = pipe.encode_prompt(
            prompt=prompt,
            device=pipe.device,
            num_images_per_prompt=num_images_per_prompt,
            do_classifier_free_guidance=do_classifier_free_guidance,
            negative_prompt=negative_prompt,
        )
        if isinstance(out, dict):
            if debug:
                for k, v in out.items():
                    if torch.is_tensor(v):
                        _log(logger, f"[EMB] built-in {k}: {tuple(v.shape)} dtype={v.dtype}")
            return out
        else:
            prompt_embeds, negative_prompt_embeds, pooled, negative_pooled = out
            if debug:
                _log(logger, f"[EMB] built-in prompt_embeds: {tuple(prompt_embeds.shape)}")
                _log(logger, f"[EMB] built-in negative_prompt_embeds: {tuple(negative_prompt_embeds.shape)}")
                _log(logger, f"[EMB] built-in pooled: {tuple(pooled.shape)}")
                _log(logger, f"[EMB] built-in negative_pooled: {tuple(negative_pooled.shape)}")
            return {
                "prompt_embeds": prompt_embeds,
                "negative_prompt_embeds": negative_prompt_embeds,
                "pooled_prompt_embeds": pooled,
                "negative_pooled_prompt_embeds": negative_pooled,
            }

    # 수동 인코딩
    text_encoder_pairs = []
    if getattr(pipe, "text_encoder", None) is not None and getattr(pipe, "tokenizer", None) is not None:
        text_encoder_pairs.append(("TE1", pipe.text_encoder, pipe.tokenizer))
    if getattr(pipe, "text_encoder_2", None) is not None and getattr(pipe, "tokenizer_2", None) is not None:
        text_encoder_pairs.append(("TE2", pipe.text_encoder_2, pipe.tokenizer_2))

    if not text_encoder_pairs:
        raise ValueError("No valid text encoder & tokenizer pairs found on the pipeline.")

    if debug:
        _log(logger, f"[ENC] Manual encode: pairs={[name for name,_,_ in text_encoder_pairs]}")
        _log(logger, f"[ENC] CFG={do_classifier_free_guidance}, num_images_per_prompt={num_images_per_prompt}")

    prompt_embeds_list, pooled_prompt_embeds_list = [], []
    neg_embeds_list, neg_pooled_list = [], []

    for name, te, tok in text_encoder_pairs:
        if debug:
            _token_debug(tok, prompt, f"{name}/POS", logger)
        inputs = tok(
            prompt,
            padding="max_length",
            max_length=tok.model_max_length,
            truncation=True,
            return_tensors="pt",
        )
        ids = inputs.input_ids.to(pipe.device)
        out = te(ids, output_hidden_states=True)
        pooled = out[0]
        hidden = out.hidden_states[-2]

        prompt_embeds_list.append(hidden)
        pooled_prompt_embeds_list.append(pooled)

        if debug:
            _token_debug(tok, negative_prompt, f"{name}/NEG", logger)
        neg_inputs = tok(
            negative_prompt,
            padding="max_length",
            max_length=tok.model_max_length,
            truncation=True,
            return_tensors="pt",
        )
        neg_ids = neg_inputs.input_ids.to(pipe.device)
        neg_out = te(neg_ids, output_hidden_states=True)
        neg_pooled = neg_out[0]
        neg_hidden = neg_out.hidden_states[-2]

        neg_embeds_list.append(neg_hidden)
        neg_pooled_list.append(neg_pooled)

        if debug:
            _log(logger, f"[EMB] {name} prompt_hidden={tuple(hidden.shape)}, pooled={tuple(pooled.shape)}")
            _log(logger, f"[EMB] {name} neg_hidden   ={tuple(neg_hidden.shape)}, neg_pooled={tuple(neg_pooled.shape)}")

    prompt_embeds = torch.cat(prompt_embeds_list, dim=-1)
    negative_prompt_embeds = torch.cat(neg_embeds_list, dim=-1)
    pooled_prompt_embeds = pooled_prompt_embeds_list[-1]
    negative_pooled_prompt_embeds = neg_pooled_list[-1]

    bs, seq, _ = prompt_embeds.shape
    prompt_embeds = prompt_embeds.repeat(1, num_images_per_prompt, 1).view(bs * num_images_per_prompt, seq, -1)
    if do_classifier_free_guidance:
        seq = negative_prompt_embeds.shape[1]
        negative_prompt_embeds = (
            negative_prompt_embeds.repeat(1, num_images_per_prompt, 1)
            .view(num_images_per_prompt, seq, -1)
        )
    pooled_prompt_embeds = pooled_prompt_embeds.repeat(num_images_per_prompt, 1).view(bs * num_images_per_prompt, -1)
    if do_classifier_free_guidance:
        negative_pooled_prompt_embeds = (
            negative_pooled_prompt_embeds.repeat(num_images_per_prompt, 1)
            .view(num_images_per_prompt, -1)
        )

    if debug:
        _log(logger, f"[EMB] COMBINED prompt_embeds={tuple(prompt_embeds.shape)}")
        _log(logger, f"[EMB] COMBINED negative_prompt_embeds={tuple(negative_prompt_embeds.shape)}")
        _log(logger, f"[EMB] COMBINED pooled={tuple(pooled_prompt_embeds.shape)}")
        _log(logger, f"[EMB] COMBINED negative_pooled={tuple(negative_pooled_prompt_embeds.shape)}")

    return {
        "prompt_embeds": prompt_embeds,
        "negative_prompt_embeds": negative_prompt_embeds,
        "pooled_prompt_embeds": pooled_prompt_embeds,
        "negative_pooled_prompt_embeds": negative_pooled_prompt_embeds,
    }


# -------------------------------
# 광고 프롬프트 빌더 (77 토큰 예산)
# -------------------------------
class _AdCompressor:
    """
    '소상공인의 진정성/정/브랜드=사장님' 같은 정성 문구를
    SDXL 친화 키워드로 축약하는 작은 룰셋.
    """
    PHRASE2KEYS = [
        (re.compile(r"진정성|정성|사장님|브랜드|소통|사연|스토리|이야기"), "authentic small business branding, human touch, storytelling"),
        (re.compile(r"따뜻|아늑|포근|감성"), "warm, cozy, inviting"),
        (re.compile(r"깔끔|미니멀|정돈|심플|컴팩트"), "clean, minimalist, high readability"),
        (re.compile(r"임팩트|한눈|눈길|주목"), "impactful, strong focal point, hero shot"),
    ]

    @classmethod
    def compress_semantics(cls, text: str) -> List[str]:
        t = text or ""
        bag: List[str] = []
        for rgx, keys in cls.PHRASE2KEYS:
            if rgx.search(t):
                bag.append(keys)
        return list(dict.fromkeys(bag))


def build_ad_prompt_compose(
    tokenizer,
    user_prompt: str,
    *,
    brand: str | None = None,
    product: str | None = None,
    tone: str = "",
    layout_hint: str = "",
    cta: str = "",
    brand_colors: str = "",
    style_hints: list[str] | None = None,
    ad_strength: float = 0.45,      # 살짝만 강조
    max_tokens_total: int = 77,
    user_budget: int = 48,
    guide_budget: int = 24,
    logger=None,
    openai_api_key: Optional[str] = None,
) -> str:
    """
    - 유저 문장을 키워드로 압축 + '컴포지션 룰북' 자동 주입
    - 77 토큰 예산에 강제 적합
    """
    style_hints = style_hints or []

    # 1) 카테고리 룰(스타일/네거티브) 참고만
    cat = classify_categories(user_prompt, openai_api_key, logger=logger)
    if logger:
        _log(logger, f"[PROMPT/RULE] style_hints+=cat: {cat.style_hints}")

    # 2) 유저 키워드 압축
    extractor = KeywordExtractor(openai_api_key, logger=logger)
    user_keys = extractor.extract(user_prompt, brand=brand, product=product)

    # 3) 소상공인/진정성 같은 정성 문구를 짧은 키워드로 보강
    soft_keys = _AdCompressor.compress_semantics(user_prompt)
    if soft_keys:
        user_keys = (user_keys + ", " + ", ".join(soft_keys)).strip(", ")

    # 4) 최종 스타일 힌트 합치기 (중복 제거)
    style_all = list(dict.fromkeys([*style_hints, *cat.style_hints]))

    # 5) **컴포지션 룰북 (고정 가이드)**
    #    - 단일 장면/콜라주 금지
    #    - 제품 중앙/최대, 모델 보조
    #    - 스튜디오 품질, 가독성
    guide_bits_fixed = [
        "one single photograph, not collage, not grid, not split-screen",
        "single scene, seamless unified background",
        "center composition: product is the hero subject, largest and most prominent, placed at center",
        "model secondary, slightly smaller, behind or beside product, looking at camera",
        "straight-on eye level camera, clean soft lighting, professional studio quality",
        "high readability, premium hero shot with negative space",
        f"[ad_emphasis:{ad_strength:.2f}]",
    ]

    # 사용자가 layout/tone/color를 주면 살짝 얹기
    if layout_hint:
        guide_bits_fixed.insert(1, layout_hint)
    if brand_colors:
        guide_bits_fixed.append(f"brand palette {brand_colors}")
    if tone:
        guide_bits_fixed.append(tone)
    if style_all:
        guide_bits_fixed.append("; ".join(style_all))

    guide = ", ".join([b for b in guide_bits_fixed if b])

    # 6) 토큰 예산 강제
    if tokenizer is not None:
        if clip_token_len(tokenizer, user_keys) > user_budget:
            user_keys = _binary_shrink_by_chars(tokenizer, user_keys, user_budget)
            if logger: _log(logger, f"[PROMPT/KEYS/FIT] user_keys trimmed to ≤{user_budget} tokens")
        if clip_token_len(tokenizer, guide) > guide_budget:
            guide = _binary_shrink_by_chars(tokenizer, guide, guide_budget)
            if logger: _log(logger, f"[PROMPT/GUIDE/FIT] guide trimmed to ≤{guide_budget} tokens")

    # 7) 합치기
    cta_short = (re.sub(r"\s+", " ", cta).strip()[:20]) if cta else ""
    final = f"{user_keys}  ## AD-GUIDE: {guide}"
    if cta_short:
        final += f"  ## CTA: {cta_short}"

    # 8) 최종 77 토큰 안전망
    if tokenizer is not None and clip_token_len(tokenizer, final) > max_tokens_total:
        final = re.sub(r"\s*##\s*CTA:.*$", "", final).strip()
        if clip_token_len(tokenizer, final) > max_tokens_total:
            guide = _binary_shrink_by_chars(
                tokenizer,
                guide,
                max_tokens_total - min(user_budget, clip_token_len(tokenizer, user_keys)) - 2
            )
            final = f"{user_keys}  ## AD-GUIDE: {guide}"
        if clip_token_len(tokenizer, final) > max_tokens_total:
            final = _binary_shrink_by_chars(tokenizer, final, max_tokens_total)
        if logger: _log(logger, "[PROMPT/FIT] final trimmed to ≤77 tokens")

    if logger:
        _log(logger, "[PROMPT/FINAL] " + final)
    return final


# --------------------------------
# (옵션) 레시피/페르소나 API 유지용 스텁
#  - 파이프라인에서 import를 기대하므로 시그니처만 유지
# --------------------------------
def get_recipe_keywords(recipe: str, logger=None) -> List[str]:
    # 기존 인터페이스 유지(사용하지 않으면 빈 리스트)
    return []

def compose_persona_4w1h(
    base_prompt: str,
    persona: Optional[str] = None,
    *,
    who: Optional[str] = None,
    what: Optional[str] = None,
    where: Optional[str] = None,
    how: Optional[str] = None,
    prefer_korean: bool = True,
) -> str:
    # 기존 인터페이스 유지: 현재는 페르소나 확장 없이 원문을 그대로 반환
    return base_prompt or ""

def build_ad_prompt(
    user_prompt: str,
    *,
    brand: str | None = None,
    product: str | None = None,
    tone: str = "",
    layout_hint: str = "",
    cta: str = "",
    brand_colors: str = "",
    style_hints: list[str] | None = None,
    strength: float = 0.8,
    max_chars: int = 900,
    logger=None,
) -> str:
    return build_ad_prompt_compose(
        tokenizer=None,  # 토크나이저 모를 경우 그냥 그대로 출력
        user_prompt=user_prompt,
        brand=brand,
        product=product,
        tone=tone,
        layout_hint=layout_hint,
        cta=cta,
        brand_colors=brand_colors,
        style_hints=style_hints,
        ad_strength=strength,
        logger=logger,
    )