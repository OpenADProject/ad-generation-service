import os
from openai import OpenAI
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

# 환경 변수 로드
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# FastAPI 앱 생성
app = FastAPI()

# 요청 데이터 구조 정의
class AdRequest(BaseModel):
    product: str
    tone: str = "친근한"
    channel: str = "instagram"
    target_audience: str | None = None
    translate_en: bool = False


def generate_ad_content(
    product: str,
    tone: str = "친근한",
    channel: str = "instagram",
    target_audience: str = None,
    translate_en: bool = False,
):
    """
    광고 콘텐츠 생성기 (A/B 테스트용 3가지 버전 출력)
    - product: 상품명/설명
    - tone: 톤앤매너 (친근한, 고급스러운 등)
    - channel: 광고 채널 (instagram, blog, banner)
    - target_audience: 타겟 고객 (20대 여성, 직장인 점심 고객 등)
    - translate_en: 영어 번역 포함 여부
    """
    
    channel_map = {
        "instagram": "인스타그램 홍보글 (짧고 매력적인 본문)",
        "blog": "블로그 홍보글 (자세하고 서술적인 글)",
        "banner": "배너 광고 문구 (짧고 강렬한 한 문장)",
    }

    prompt = f"""
    당신은 뛰어난 마케팅 카피라이터입니다.
    아래 조건에 맞는 {channel_map.get(channel, channel)}을 작성해주세요.

    상품: {product}
    톤앤매너: {tone}
    """

    if target_audience:
        prompt += f"\n타겟 고객: {target_audience}"

    prompt += """
    출력 조건:
    - 총 3가지 서로 다른 버전의 홍보 문구를 작성 (A/B 테스트 용도)
    - 각 버전은 구분선(---)으로 나누어 출력
    - 한국어 기준으로 작성
    """

    if translate_en:
        prompt += "\n- 각 버전마다 영어 번역도 바로 이어서 작성"

    if channel == "instagram":
        prompt += "\n- 끝에는 상품 특성에 맞는 해시태그 5~10개 포함 (한국어/영어 혼합 가능)"

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )

    return response.choices[0].message.content.strip()


# API 엔드포인트
@app.post("/generate")
def generate_ad(request: AdRequest):
    result = generate_ad_content(
        request.product,
        request.tone,
        request.channel,
        request.target_audience,
        request.translate_en
    )
    return {"result": result}


@app.get("/test")
def test():
    return {"status": "ok"}
