import os
from openai import OpenAI
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

# ==============================
#  OpenAI 클라이언트 설정
# ==============================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# FastAPI 앱 생성
app = FastAPI()

# ==============================
#  카테고리 정의 & 해시태그 템플릿
# ==============================
CATEGORY_TAGS = {
    # 음식
    "F&B_레스토랑": ["맛집", "#맛집추천", "#오늘뭐먹지", "#먹스타그램", "#koreanfood"],
    "F&B_카페": ["카페", "#카페투어", "커피", "cafe", "coffee"],
    "F&B_디저트": ["#디저트", "dessert"],

    # 뷰티
    "뷰티_헤어": ["#미용실", "#퍼스널컬러", "#퍼스널헤어", "#헤어스타일"],
    "뷰티_네일": ["#네일", "#네일아트", "#이달의아트", "#젤네일"],
    "뷰티_스킨": ["#에스테틱", "#피부관리", "#피부과"],
    "뷰티_속눈썹": ["#속눈썹펌", "#속눈썹펌", "#속눈썹연장"],
    "뷰티_눈썹반영구": ["#반영구", "#자연눈썹반영구", "#눈썹문신"],
    "뷰티_왁싱": ["#왁싱", "#제모"],

    # 소매
    "소매_패션": ["#데일리룩", "#오오티디", "#ootd", "#쇼핑", "#스타일"],
    "소매_선물": ["#선물", "#선물추천"],

    # 교육
    "교육_스터디카페": ["#스터디카페", "#스카", "#작업공간", "#디지털노마드", "#카공"],
    "교육_학원": ["#학원"],
    "교육_취미": ["#원데이클래스", "#자기계발", "#갓생"],
    "교육_운동": ["#운동", "오운완"],

    # 숙박
    "숙박_여행": ["#숙소", "#여행", "#숙소추천"],

    # 보건의료
    "보건_병원": ["병원", "#전문의", "#상담문의"],

    # 전문 서비스
    "서비스_부동산": ["#부동산", "#자산관리", "#매매", "#아파트", "#원룸", "#투룸"],
    "서비스_인테리어": ["#인테리어", "#리모델링", "#집꾸미기"],
}

# ==============================
#  카테고리 추론 함수
# ==============================
def infer_category(product_desc: str) -> str:
    """
    모델에게 상품 설명/상품명을 보고 업종 카테고리를 추론하도록 요청.
    CATEGORY_TAGS 내에 있으면 해당 키 반환,
    없으면 '기타' 반환.
    """
    prompt = f"""
    상품 설명: {product_desc}
    아래 업종 카테고리 중 하나를 가장 적합하게 선택하세요.
    만약 어느 것에도 해당하지 않으면 "기타"라고 출력하세요.

    가능한 카테고리:
    {", ".join(CATEGORY_TAGS.keys())}

    출력 형식: 카테고리명만 단독 출력
    """
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()

# ==============================
#  키워드 추출 함수
# ==============================
def extract_keywords_from_product(product_desc: str, max_keywords: int = 5):
    prompt = f"""
    아래 상품 설명에서 광고용 해시태그로 쓸 수 있는 핵심 키워드 {max_keywords}개를
    선택해 쉼표로 구분하여 출력하세요.
    - 단어만 출력, '#'는 붙이지 마세요.
    - 숫자, 이벤트, 브랜드명 등 광고에 중요한 키워드는 포함 가능.

    상품 설명: {product_desc}
    """
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    keywords_str = response.choices[0].message.content.strip()
    return [kw.strip() for kw in keywords_str.split(",") if kw.strip()]

# ==============================
#  해시태그 생성 함수
# ==============================
def generate_hashtags(location: str, category: str, product_desc: str):
    hashtags = set()

    # 대표 키워드 (기타일 경우는 공백 처리)
    if category in CATEGORY_TAGS:
        rep_keyword = CATEGORY_TAGS[category][0].lstrip("#")
    else:
        rep_keyword = ""

    # 1. 카테고리 기본 태그
    if category in CATEGORY_TAGS:
        hashtags.update(CATEGORY_TAGS[category])
    elif category == "기타":
        # 카테고리가 기타일 경우 모델이 직접 해시태그 생성
        prompt = f"""
        상품 설명: {product_desc}
        업종 카테고리가 사전에 없습니다.
        이 상품/서비스를 홍보하기에 적합한 해시태그 5~8개를 제안해주세요.
        일반적인 홍보용 (#추천, #인기 등)과 업종 관련 키워드를 섞어주세요.

        출력 형식: 해시태그만 공백으로 구분하여 나열
        """
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        extra_tags = response.choices[0].message.content.strip().split()
        hashtags.update(extra_tags)

    # 2. 지역 기반 태그
    if location:
        parts = location.split()
        last = parts[-1]  # 항상 읍/면/동
        first = parts[0]  # 시/도 or 특별시/광역시

        special_cities = [
            "서울특별시", "세종특별자치시", "광주광역시", "부산광역시",
            "대구광역시", "대전광역시", "울산광역시", "인천광역시", "제주특별자치도"
        ]

        def remove_last_char(name: str) -> str:
            """끝 글자가 시/군/구이면 제거"""
            if name[-1] in ["시", "군", "면", "읍"]:
                return name[:-1]
            return name

        if rep_keyword:  # 카테고리에 맞는 대표 키워드가 있을 때만 지역+업종 태그 생성
            if first in special_cities:
                # "서울특별시" -> "서울", "제주특별자치도" -> "제주"
                hashtags.add(f"#{first.replace('특별시','').replace('광역시','').replace('특별자치시','').replace('특별자치도','')}{rep_keyword}")
                hashtags.add(f"#{remove_last_char(parts[1])}{rep_keyword}")   # "강남구" -> "강남구", "서귀포시" -> "서귀포"
                hashtags.add(f"#{remove_last_char(parts[-1])}{rep_keyword}")  # "청담동" -> "청담동", "애월읍" -> "애월"
            else:
                hashtags.add(f"#{remove_last_char(parts[1])}{rep_keyword}")   # "용인시" -> "용인"
                hashtags.add(f"#{remove_last_char(parts[-1])}{rep_keyword}")  # "죽전동" -> "죽전동", "백암면" -> "백암"
        else:
            # 대표 키워드가 없으면 지역명 단독 태그만 생성
            hashtags.add(f"#{remove_last_char(parts[1])}")
            hashtags.add(f"#{remove_last_char(parts[-1])}")

    # 3. 상품 설명 기반 핵심 키워드
    if category in CATEGORY_TAGS:  # 카테고리가 사전에 있을 때만 키워드 추출 적용
        keywords = extract_keywords_from_product(product_desc)
        for kw in keywords:
            hashtags.add(f"#{kw}")

    return list(hashtags)[:8]


# ==============================
#  광고 콘텐츠 생성 함수
# ==============================
def generate_ad_content(
    product_desc: str,
    tone: str = "친근한",
    channel: str = "instagram",
    target_audience: str = None,
    translate_en: bool = False,
    location: str = None
):
    category = infer_category(product_desc)
    hashtags = generate_hashtags(location, category, product_desc)

    channel_map = {
        "instagram": "인스타그램 홍보글 (짧고 매력적인 본문, 이모지 포함)",
        "blog": "블로그 홍보글 (자세하고 서술적인 글)",
        "banner": "배너 광고 문구 (짧고 강렬한 한 문장)",
    }

    prompt = f"""
    당신은 뛰어난 마케팅 카피라이터입니다.
    아래 조건에 맞는 {channel_map.get(channel, channel)}을 작성해주세요.

    상품 설명: {product_desc}
    톤앤매너: {tone}
    업종 카테고리: {category}
    """

    if target_audience:
        prompt += f"\n타겟 고객: {target_audience}"
    if location:
        prompt += f"\n지역: {location} (본문 표현에 자연스럽게 포함 가능)"

    prompt += """
    출력 조건:
    - 상품 설명 속 주요 키워드는 반드시 포함할 것
    - 타겟 고객은 문구 톤에 반영하되, 특정 성별/연령만을 직접적으로 언급하지 마세요.
    - 지역명은 본문에서는 자연스럽게 언급하거나 생략해도 되며, 해시태그에만 반영해도 됩니다.
    - 총 3가지 서로 다른 버전의 홍보 문구 작성 (A/B 테스트 용도)
    - 각 버전은 구분선(---)으로 나누어 출력
    - 한국어 기준
    """
    if translate_en:
        prompt += "\n- 각 버전마다 영어 번역도 바로 이어서 작성"
    if channel == "instagram":
        prompt += "\n- 본문에 이모지 활용하여 시각적으로 매력적으로 작성"
        prompt += f"\n- 끝에는 5~8개의 해시태그 포함: {', '.join(hashtags)}"

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )
    return response.choices[0].message.content.strip()

# ==============================
#  API 요청 스키마
# ==============================
class AdRequest(BaseModel):
    product: str
    tone: str = "친근한"
    channel: str = "instagram"
    target_audience: str | None = None
    translate_en: bool = False
    location: str | None = None

# ==============================
#  엔드포인트
# ==============================
@app.post("/generate")
def generate_ad(request: AdRequest):
    result = generate_ad_content(
        product_desc=request.product,
        tone=request.tone,
        channel=request.channel,
        target_audience=request.target_audience,
        translate_en=request.translate_en,
        location=request.location
    )
    return {"result": result}

@app.get("/test")
def test():
    return {"status": "ok"}
