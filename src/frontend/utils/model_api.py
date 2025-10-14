import requests
import streamlit as st
from typing import Dict, Any, Optional, Tuple

MODEL_API_BASE = st.secrets["MODEL_API_BASE"].rstrip("/")

def generate_text(
    product: str,
    tone: str,
    target_audience: str,
    translate_en: bool,
    location: str, 
    channel: str = "instagram",
    timeout: int = 30,
) -> str:
    """
    텍스트 생성 API 호출

    - POST {MODEL_API_BASE}/infer/text
    - 입력: 상품/상호명, 톤, 타겟층, 지역, 영어 번역 여부, 채널
    - 성공: 생성된 문구 문자열 반환
    - 실패: HTTPError 또는 ValueError 발생

    Returns:
        str: 생성된 텍스트(양 끝 공백 제거)
    """
    url = f"{MODEL_API_BASE}/infer/text"
    payload = {
        "product": product,
        "tone": tone,
        "channel": channel,
        "target_audience": target_audience,
        "translate_en": translate_en,
        "location" : location
    }

    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("응답에 'text' 필드가 없거나 비어 있습니다.")
    return text.strip()

def generate_insta_image(
    *,
    product_image: str,
    model_image: Optional[str],
    prompt: str,
    brand_name: str,
    background: str,
    target: str,
    size: str,
    model_alias: str,
    file_saved: bool = False,
    timeout: int = 60,
) -> Tuple[Optional[bytes], Dict[str, Any]]:
    """
    인스타그램 이미지 생성 API 호출

    - POST {MODEL_API_BASE}/infer/image
    - 입력:
        product_image (base64, data URL 가능),
        model_image (선택, base64/data URL),
        prompt(자유 요청),
        params: brand_name/background/target/size/model_alias/file_saved
    - 응답 파싱:
        이미지 base64는 다양한 키를 탐색하여 추출
        (output_base64/image_base64/image/output_image/data/images)
    - 디코딩 실패 시 ValueError 발생

    Returns:
        Tuple[Optional[bytes], Dict[str, Any]]:
            image_bytes: 생성된 PNG 바이너리 (없으면 None)
            meta: 이미지 원본 키들을 제외한 나머지 메타 정보
    """
    url = f"{MODEL_API_BASE}/infer/image"

    # model_image가 없으면 키 자체를 빼주는 게 안전
    payload = {
        "product_image": product_image,
        "prompt": prompt,
        "params": {
            "brand_name": brand_name,
            "background": background,
            "target": target,
            "size": size,
            "model_alias": model_alias,
            "file_saved": file_saved,
        },
    }
    if model_image:
        payload["model_image"] = model_image

    resp = requests.post(url, json=payload, timeout=timeout)

    resp.raise_for_status()
    data = resp.json()

    img_b64: Optional[str] = None
    for key in ("output_base64", "image_base64", "image", "output_image", "data"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            img_b64 = val.strip()
            break

    if img_b64 is None:
        images = data.get("images")
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, str) and first.strip():
                img_b64 = first.strip()
            elif isinstance(first, dict):
                for k in ("base64", "image_base64", "image", "output_base64"):
                    if isinstance(first.get(k), str) and first[k].strip():
                        img_b64 = first[k].strip()
                        break

    # 디코딩
    image_bytes: Optional[bytes] = None
    if img_b64:
        if img_b64.startswith("data:"):
            img_b64 = img_b64.split(",", 1)[-1]
        import base64
        try:
            image_bytes = base64.b64decode(img_b64, validate=False)
        except Exception as e:
            raise ValueError(f"base64 디코딩 실패: {e}")

    exclude = {"output_base64", "image_base64", "image", "output_image", "data", "images"}
    meta = {k: v for k, v in data.items() if k not in exclude}


    return image_bytes, meta
