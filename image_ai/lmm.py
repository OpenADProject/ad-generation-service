# image_ai/lmm.py
import os, base64
from typing import Optional

def caption_or_concept(img_path: str, user_concept: Optional[str]) -> str:
    """
    - user_concept가 있으면 그대로 사용
    - 없으면 OpenAI(옵션)로 캡션→컨셉 요약. 키 없으면 기본 프롬프트로 폴백
    """
    if user_concept:
        return user_concept

    if not os.getenv("OPENAI_API_KEY"):
        return "clean studio background, soft light, minimal, product focused"

    try:
        from openai import OpenAI
        client = OpenAI()
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        msg = client.chat.completions.create(
            model=os.getenv("ADSGEN_LMM_MODEL", "gpt-4.1-mini"),
            messages=[{
                "role":"user",
                "content":[
                    {"type":"input_text","text":"이 사진을 광고 배경 콘셉트로 요약해줘. 10~15단어, 장면/조명/무드 중심. 제품 언급 X."},
                    {"type":"input_image","image_url":{"url":f"data:image/png;base64,{b64}"}}
                ]
            }],
            temperature=0.5,
            max_tokens=100
        )
        return msg.choices[0].message.content.strip()
    except Exception:
        return "clean studio background, soft light, minimal, product focused"