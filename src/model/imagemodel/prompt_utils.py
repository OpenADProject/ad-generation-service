# =======================================
# prompt_utils.py — 최종 완성본 (Full Code)
# =======================================
# [UPDATE] AI Vision을 통한 모델 타입 분석 기능(_get_model_type_from_llm) 추가
# =======================================
from __future__ import annotations
import os, re, json, time
from typing import Optional, Dict
import torch
import config

_HAS_OPENAI = True
try: from openai import OpenAI
except Exception: _HAS_OPENAI = False; OpenAI = None

def _log(logger, msg):
    if logger: logger.info(msg)
    else: print(msg)

def _validate_compose_json(obj: dict):
    req = ["final_prompt_en", "keywords_kor", "negatives_en", "interaction_detected"]
    if not isinstance(obj, dict): raise ValueError("LLM returned non-JSON")
    for k in req:
        if k not in obj: raise ValueError(f"Missing required key: {k}")
    for lk in ["keywords_kor", "negatives_en"]:
        if lk in obj and not isinstance(obj[lk], list): obj[lk] = [obj[lk]] if obj[lk] else []
    if not isinstance(obj["final_prompt_en"], str): obj["final_prompt_en"] = str(obj["final_prompt_en"] or "")
    if not isinstance(obj["interaction_detected"], bool): obj["interaction_detected"] = False
    return obj

def _get_product_category_from_llm(prompt_text: str, product_image_b64: str | None, api_key: Optional[str], logger=None) -> str:
    """사용자 프롬프트와 이미지를 기반으로 제품의 카테고리를 추론합니다."""
    if not (api_key and _HAS_OPENAI and OpenAI): raise RuntimeError("OpenAI not available")
    client = OpenAI(api_key=api_key)

    _log(logger, "Asking LLM to determine product category...")

    content = []
    user_prompt = (
        f"Analyze the following user request and the attached image to determine the main product's category.\n\n"
        f"User Request: \"{prompt_text}\""
    )
    content.append({"type": "text", "text": user_prompt})

    if product_image_b64:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{product_image_b64}", "detail": "low"}})

    sys_prompt = (
        "You are a product category classifier. Based on the user's text and image, classify the product into ONE of the following categories: "
        "'food', 'cosmetics', 'fashion', 'electronics', 'furniture', 'other'. "
        "Respond with ONLY the single category name in lowercase (e.g., 'food')."
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": content}
            ],
            max_tokens=10,
        )
        category = resp.choices[0].message.content.strip().lower()
        
        valid_categories = ['food', 'cosmetics', 'fashion', 'electronics', 'furniture', 'other']
        if category not in valid_categories:
            _log(logger, f"LLM returned an invalid category: '{category}'. Defaulting to 'other'.")
            return 'other'
            
        _log(logger, f"LLM determined product category: {category}")
        return category
    except Exception as e:
        _log(logger, f"Could not determine product category from LLM: {e}. Falling back to 'other'.")
        return 'other'

def _get_model_type_from_llm(model_image_b64: str | None, api_key: Optional[str], logger=None) -> str:
    """AI Vision을 사용해 이미지 속 모델이 'human'인지 'animal'인지 분류합니다."""
    if not model_image_b64:
        _log(logger, "No model image provided, defaulting model type to 'human'.")
        return 'human'
    if not (api_key and _HAS_OPENAI and OpenAI):
        raise RuntimeError("OpenAI not available")
    
    client = OpenAI(api_key=api_key)
    _log(logger, "Asking LLM with Vision to determine model type (human/animal)...")

    content = [
        {
            "type": "text",
            "text": (
                "Analyze the attached image. Is the main subject a 'human' or an 'animal'? "
                "Respond with ONLY the single word 'human' or 'animal' in lowercase."
            )
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{model_image_b64}",
                "detail": "low"
            }
        }
    ]

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": content}],
            max_tokens=10,
        )
        model_type = resp.choices[0].message.content.strip().lower()
        
        if model_type not in ['human', 'animal']:
            _log(logger, f"LLM returned an invalid model type: '{model_type}'. Defaulting to 'human'.")
            return 'human'
            
        _log(logger, f"LLM Vision determined model type: {model_type}")
        return model_type
    except Exception as e:
        _log(logger, f"Could not determine model type from LLM Vision: {e}. Falling back to 'human'.")
        return 'human'

def _llm_compose_prompt_from_inputs(prompt_context: dict, product_image: str | None, model_image: str | None, api_key: Optional[str], logger=None) -> dict:
    if not (api_key and _HAS_OPENAI and OpenAI): raise RuntimeError("OpenAI not available")
    client = OpenAI(api_key=api_key)
    
    content = []
    
    category = prompt_context.get("product_category", "default")
    category_guidelines = {
        "food": "For 'food' items, emphasize freshness, delicious textures, vibrant colors. The scene must be mouth-watering.",
        "cosmetics": "For 'cosmetics', focus on luxurious textures, elegant packaging. The scene must feel clean and premium.",
        "fashion": "For 'fashion' items, highlight the material and fit. The mood must be stylish.",
        "electronics": "For 'electronics', focus on sleek design, modern materials, and a futuristic aesthetic.",
        "furniture": "For 'furniture', showcase the material, design, and comfort in a harmonious living space.",
        "other": "Create an appealing and desirable commercial photograph."
    }
    
    user_text = (
        "You are an expert AI Creative Director. Your task is to create a powerful but concise photorealistic ad prompt. "
        "Combine all the user's requests and art direction guidelines into a single, cohesive, and descriptive paragraph. "
        "**Crucially, keep the final prompt under 70 tokens.** Describe the main subject, the action, and the background style briefly and effectively.\n\n"
        "[CRITICAL RULE] You must NOT change, modify, or add to the core product itself. For example, if the user provides a 'banana', the final prompt must be about the banana fruit, NOT a 'banana-flavored drink' or 'banana cosmetic'. Stick to the original product.\n\n"
        "--- User's Request ---\n"
        f"{json.dumps(prompt_context, ensure_ascii=False, indent=2)}\n\n"
        "--- Art Direction Guidelines ---\n"
        f"1.  **Product Category Direction:** The product category is '{category}'. "
        f"{category_guidelines.get(category, 'Create an appealing commercial photograph.')}\n"
        "2.  **Scene & Placement Direction:** Use the 'template_hint' and 'placement_hint' to describe the scene.\n\n"
        "Generate the final English prompt as one single paragraph."
    )

    content.append({"type": "text", "text": user_text})

    if product_image:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{product_image}"}})
    if model_image:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{model_image}"}})
    
    sys = (
        "First, analyze the user's 'core_request' to determine if it describes a direct physical interaction between the subject and a product. "
        "Set the 'interaction_detected' boolean flag based on this analysis. "
        "Second, generate the other fields based on your role as an expert AI Creative Director. "
        "Your output MUST be a JSON object with four keys: "
        "{\"final_prompt_en\": string, \"keywords_kor\": [string], \"negatives_en\": [string], \"interaction_detected\": boolean}"
    )

    model_to_use = "gpt-4o-mini"
    _log(logger, f"[LLM] Acting as AI Creative Director with model: {model_to_use}")

    resp = client.chat.completions.create(
        model=model_to_use,
        messages=[{"role": "system", "content": sys}, {"role": "user", "content": content}],
        max_tokens=500,
        response_format={"type":"json_object"},
    )
    raw = resp.choices[0].message.content.strip()
    data = _validate_compose_json(json.loads(raw))
    _log(logger, f"[PROMPT/LLM] JSON ok: keys={list(data.keys())}")
    return data

def get_relative_scale_from_llm(model_image: str, product_image: str, api_key: Optional[str], logger=None) -> float:
    if not (api_key and _HAS_OPENAI and OpenAI): raise RuntimeError("OpenAI not available")
    client = OpenAI(api_key=api_key)
    _log(logger, "Asking LLM to determine relative scale of product to model...")
    content = [
        {"type": "text", "text": "You are a precise photo editor. Look at the two images provided... Respond with ONLY a single float number..."}, # 프롬프트 일부 생략
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{model_image}", "detail": "low"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{product_image}", "detail": "low"}},
    ]
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": content}],
            max_tokens=10,
        )
        response_text = resp.choices[0].message.content.strip()
        scale = float(response_text)
        _log(logger, f"LLM determined relative scale: {scale}")
        return max(0.05, min(scale, 1.5))
    except Exception as e:
        _log(logger, f"Could not determine relative scale from LLM: {e}. Falling back to default scale.")
        return 0.3

def encode_prompt_sdxl(pipe, prompt, negative_prompt):
    (prompt_embeds, negative_prompt_embeds, pooled_prompt_embeds, negative_pooled_prompt_embeds) = pipe.encode_prompt(
        prompt=prompt, num_images_per_prompt=1, do_classifier_free_guidance=True, negative_prompt=negative_prompt)
    return { "prompt_embeds": prompt_embeds, "negative_prompt_embeds": negative_prompt_embeds, "pooled_prompt_embeds": pooled_prompt_embeds, "negative_pooled_prompt_embeds": negative_pooled_prompt_embeds }

def build_ad_prompt_compose(tokenizer, raw_inputs: dict, *, logger=None, openai_api_key: Optional[str]=None) -> dict:
    prompt = raw_inputs.get("prompt")
    params = raw_inputs.get("params", {})
    
    briefing = {
        "core_request": prompt,
        "template_hint": params.get("template_hint"),
        "placement_hint": params.get("placement_hint"),
        "product_category": raw_inputs.get("product_category", "other")
    }
    
    product_image = raw_inputs.get("product_image")
    model_image = raw_inputs.get("model_image")
    
    if params.get("brand_name"): briefing["brand"] = params.get("brand_name")
    if params.get("target") or params.get("model_alias"): briefing["subject"] = params.get("target") or params.get("model_alias")

    try:
        data = _llm_compose_prompt_from_inputs(briefing, product_image, model_image, openai_api_key, logger=logger)
        _log(logger, "[PROMPT] AI Director composed prompt with multimodal vision.")
        return data
    except Exception as e:
        _log(logger, f"[ERROR] Prompt composition by AI Director failed: {e}. Falling back to a simple prompt.")
        return {
            "final_prompt_en": f"a high-quality commercial photograph of a product, related to '{prompt or 'something'}', clean studio background",
            "keywords_kor": [],
            "negatives_en": [],
            "interaction_detected": False
        }