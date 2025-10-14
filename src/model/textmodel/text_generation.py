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


CHANNEL_PROMPTS = {
    "instagram": """
    당신은 감각적인 SNS 마케팅 전문가입니다.
    주어진 정보를 토대로 인스타그램 홍보 글을 작성해주세요.
    """,
    "community": """
    당신은 ○○동에서 작은 가게를 운영하는 사장님입니다.
    광고처럼 보이지 않고, 지역 주민들에게 따뜻하게 말 건네듯 글을 작성해주세요.
    """
}

TONE_PROMPTS = {
    "친근한": """
    - 소상공인이 직접 쓰는 글처럼 소박하면서도 정감 있게 작성하세요.
    - 말투는 편안하고 따뜻하며, 동네 주민에게 말하듯 친근하게 표현해주세요.
    - 그렇지만 반말은 안됩니다. 너무 격식적이지 않아도 되지만 예의는 있어야합니다.
    - 어울리는 이모지를 적절하게 사용해주세요.
    """,

    "고급스러운": """
    - 말투는 세련되고 정제되며, 고급스러운 이미지를 강조하세요.
    - 고급 레스토랑, 와인바, 에스테틱 같은 프리미엄 공간을 떠올리게 하는 톤을 사용하세요.
    - 전문 용어는 과하지 않게, 단정하고 품격 있게 작성해주세요.
    - 불필요한 이모지 사용은 최소화해주세요.
    """,

    "전문적인": """
    - 말투는 신뢰감을 주는 프로페셔널한 톤으로 작성하세요.
    - 구체적인 데이터, 과정, 제작 방식 등 전문적인 정보를 포함하세요.
    - 관련 업계 용어나 검증된 지식을 포함 해주세요. 
    - 고객에게 정보를 정확하게 제공하는 전문가의 느낌을 주되, 지나치게 딱딱하지 않게 하세요.
    - 불필요한 이모지 사용은 최소화해주세요.
    """,

    "감성적인": """
    - 말투는 감성을 자극하는 따뜻하고, 일상 속 특별한 순간을 담아내듯 서정적인 분위기로 작성하세요.
    - 적절한 비유나 시적인 표현을 사용하여 독자가 감정을 느낄 수 있게 하세요.
    - 어울리는 이모지를 적절하게 사용해주세요.
    """
}


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
        "community": "지역 커뮤니티 홍보글 (자세하고 서술적인 글, 친근하고 생활 밀착형, 이웃에게 알리는 톤)"
    }

    prompt = CHANNEL_PROMPTS.get(channel, "") + TONE_PROMPTS.get(tone, "") + f"""

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
    - 지역명은 본문에서는 자연스럽게 언급하거나 생략해도 되며, 인스타그램 홍보글의 경우 해시태그에만 반영해도 됩니다.
    - 총 3가지 서로 다른 버전의 홍보 문구 작성 (A/B 테스트 용도)
    - 각 버전은 구분선(---)으로 나누어 출력
    - 한국어 기준
    """
    if translate_en:
        prompt += "\n- 각 버전마다 영어 번역도 바로 이어서 작성"

    if channel == "instagram":
        # prompt += "\n- 본문에 이모지 활용하여 시각적으로 매력적으로 작성"
        prompt += f"\n- 끝에는 5~8개의 해시태그 포함: {', '.join(hashtags)}"

    elif channel == "community":
        prompt += """
        - 첫 문장은 "안녕하세요, ○○동 이웃 여러분 😊"처럼 따뜻한 인사로 시작할 것
        - 길이는 6~8문장 정도로 작성
        - 가게 운영 이야기, 메뉴 개발 계기, 고객 감사 인사 등을 자연스럽게 포함
        - 너무 상업적이지 않고, 사장님이 직접 쓰는 글처럼 진솔한 톤
        - 문장 끝에는 "언제든 들러주세요", "항상 감사합니다" 같은 따뜻한 마무리 멘트
        - 이모지는 톤앤매너에 따라 자연스럽게 섞되 과하지 않게 사용할 것
        - 해시태그는 넣지 말 것
        - 지역명은 반드시 본문에 자연스럽게 포함
        """

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
