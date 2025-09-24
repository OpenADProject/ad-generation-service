import requests
import streamlit as st

MODEL_API_BASE = st.secrets["MODEL_API_BASE"].rstrip("/")

def generate_insta_text(
    product: str,
    tone: str,
    target_audience: str,
    translate_en: bool,
    channel: str = "instagram",
    timeout: int = 30,
) -> str:
    """
    인스타그램 텍스트 생성 API 호출 함수
    Args:
        product (str): 상품/상호명
        tone (str): 말투 톤
        target_audience (str): 타겟층
        translate_en (bool): 영어 번역 포함 여부
        channel (str): 기본 instagram

    Returns:
        생성된 텍스트(str)
    """
    url = f"{MODEL_API_BASE}/infer/text"
    payload = {
        "product": product,
        "tone": tone,
        "channel": channel,
        "target_audience": target_audience,
        "translate_en": translate_en,
    }

    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("응답에 'text' 필드가 없거나 비어 있습니다.")
    return text.strip()
