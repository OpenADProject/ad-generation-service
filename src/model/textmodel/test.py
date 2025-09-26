import os
from openai import OpenAI
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==============================
#  카테고리 정의 & 해시태그 템플릿
# ==============================
CATEGORY_TAGS = {
    "카페": ["#카페", "#카페추천", "#카페투어", "#카페스타그램", "#디저트카페"],
    "디저트": ["#디저트", "#디저트맛집", "#디저트스타그램", "#달달구리", "#빵스타그램"],
    "음식점": ["#맛집", "#맛집추천", "#먹스타그램", "#오늘뭐먹지", "#핫플"],
    "패션": ["#패션", "#데일리룩", "#옷스타그램", "#쇼핑", "#스타일"],
    "뷰티": ["#뷰티", "#셀프케어", "#뷰스타그램", "#네일", "#헤어스타일"],
    "헬스": ["#헬스", "#운동", "#피트니스", "#건강", "#다이어트"],
    "학원": ["#학원", "#공부", "#스터디", "#자기계발", "#교육"],
    "병원": ["#병원", "#클리닉", "#건강관리", "#의료", "#상담"],
    "선물": ["#선물추천", "#추석선물", "#명절선물", "#기념일선물", "#부모님선물"],
    "숙박": ["#여행", "#숙소추천", "#펜션", "#호텔", "#여행스타그램"],
    "반려동물": ["#반려동물", "#강아지", "#고양이", "#펫스타그램", "#애견카페"],
    "자동차": ["#자동차", "#정비", "#세차", "#차스타그램", "#튜닝"],
    "부동산": ["#부동산", "#아파트", "#원룸", "#전세", "#매매"],
    "문화": ["#문화생활", "#공연", "#전시회", "#책스타그램", "#영화"],
    "기타": ["#추천", "#핫플", "#일상", "#소통해요", "#오늘"],
}


# ==============================
#  카테고리 추론 함수
# ==============================
def infer_category(product_desc: str) -> str:
    """
    GPT에게 상품 설명/상품명을 보고 업종 카테고리를 추론하도록 요청
    반드시 CATEGORY_TAGS 키 중 하나를 출력해야 함
    """
    prompt = f"""
    상품 설명: {product_desc}
    아래 업종 카테고리 중 하나를 가장 적합하게 선택해서 출력하세요.
    절대로 목록에 없는 단어를 출력하지 마세요.

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

def extract_keywords_from_product(product_desc: str, max_keywords: int = 5):
    """
    상품 설명에서 광고용 핵심 키워드 추출
    - 쉼표로 구분된 단어만 반환
    """
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
    keywords = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]
    return keywords

# ==============================
#  해시태그 생성 함수
# ==============================
def generate_hashtags(location: str, category: str, product_desc: str):
    hashtags = set()

    # 대표 키워드 (카테고리 첫 번째 태그)
    rep_keyword = CATEGORY_TAGS.get(category, [category])[0].lstrip("#")


    # 1. 카테고리 기본 태그
    if category in CATEGORY_TAGS:
        hashtags.update(CATEGORY_TAGS[category])

    # 2. 지역 기반 태그
    if location and category:
        parts = location.split()
        last = parts[-1]  # 항상 읍/면/동
        first = parts[0]  # 시/도 or 특별시/광역시

        special_cities = [
            "서울특별시", "세종특별자치시", "광주광역시", "부산광역시",
            "대구광역시", "대전광역시", "울산광역시", "제주특별자치도"
        ]

        def remove_last_char(name: str) -> str:
            """끝 글자가 시/군/구이면 제거"""
            if name[-1] in ["시", "군", "구"]:
                return name[:-1]
            return name
        if first in special_cities:
            if len(parts) >= 3:
                # "서울특별시" -> "서울"
                hashtags.add(f"#{first.replace('특별시','').replace('광역시','').replace('특별자치시','').replace('특별자치도','')}{rep_keyword}")
                # "강남구" -> "강남"
                hashtags.add(f"#{remove_last_char(parts[1])}{rep_keyword}")
            if len(parts) >= 3:
                # "청담동" 그대로 사용
                hashtags.add(f"#{last}{rep_keyword}")

        #if first in special_cities:
            # 특별/광역시: 시 + 구 + 동
            #if len(parts) >= 3:
             #   hashtags.add(f"#{first.replace('특별시','').replace('광역시','').replace('특별자치시','').replace('특별자치도','')}{category}")
              #  hashtags.add(f"#{remove_last_char(parts[1])}{rep_keyword}")  # 구
            #hashtags.add(f"#{last}{rep_keyword}")  # 동
        else:
            # 일반 시/도: 시 이름(두 번째) + 마지막 동 이름
            if len(parts) >= 2:
                hashtags.add(f"#{remove_last_char(parts[1])}{rep_keyword}")  # 시 이름
            hashtags.add(f"#{last}{rep_keyword}")  # 동 이름

    # 3. 상품 설명 기반 핵심 키워드
    keywords = extract_keywords_from_product(product_desc)
    for kw in keywords:
        hashtags.add(f"#{kw}")

    # 최대 15개
    return list(hashtags)[:15]




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
    """
    상품명/상품설명 기반 인스타그램 광고 콘텐츠 생성 (A/B 테스트용)
    """
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

    prompt += f"""

    출력 조건:
    - 상품 설명 속 주요 키워드는 반드시 포함할 것
    - 타겟 고객은 문구 톤에 반영하되, 특정 성별/연령만을 직접적으로 언급하지 마세요.
    - 지역명은 본문에서는 자연스럽게 언급하거나 생략해도 되며, 해시태그에만 반영하세요.
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
#  실행 부분
# ==============================
if __name__ == "__main__":
    product_desc = input("상품명/상품설명을 입력하세요: ")
    tone = input("톤앤매너 (예: 친근한, 고급스러운): ")
    channel = input("채널 (instagram/blog/banner): ").lower() or "instagram"
    target_audience = input("타겟 고객 (없으면 Enter): ") or None
    translate = input("영어 번역글 포함? (y/n): ").lower().startswith("y")
    location = input("지역명 (예: 서울특별시 강남구 압구정동): ") or None

    print("\n=== 생성된 광고 콘텐츠 (A/B 테스트용) ===")
    print(generate_ad_content(product_desc, tone, channel, target_audience, translate, location))
