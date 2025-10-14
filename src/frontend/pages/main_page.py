import streamlit as st
from PIL import Image

# 상수 정의
IMG_LOGO_TITLE = "OpenADProject"

# 페이지 경로
ROUTE_IMAGE_INSTA = "./pages/image_insta_page.py"
ROUTE_TEXT_INSTA  = "./pages/text_insta_page.py"
ROUTE_TEXT_COMM   = "./pages/text_community_page.py"

# 에셋 경로
ASSET_MAIN_INSTAGRAM_IMAGE = "assets/main_instagram_image.png"
ASSET_MAIN_IMAGE           = "assets/main_image.png"
ASSET_MAIN_INSTAGRAM_TEXT  = "assets/main_instagram_text.png"
ASSET_MAIN_COMMUNITY_TEXT  = "assets/main_community_text.png"

def apply_global_styles() -> None:
    """
    전역 스타일 적용
    - 컨테이너 폭/패딩, 중앙정렬 클래스 정의
    """
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 90% !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
            padding-top: 0rem !important;
            padding-bottom: 6rem !important;
        }
        .centered-text { text-align: center; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_title_and_tagline() -> None:
    """
    상단 타이틀/태그라인 렌더링
    """
    st.markdown(
        f"<h1 class='centered-text' style='color:#0b78db; font-size:60px;'>{IMG_LOGO_TITLE}</h1>",
        unsafe_allow_html=True,
    )
    st.markdown("")
    st.markdown(
        "<p class='centered-text' style='font-size:18px'>"
        "AI로 더 쉽고 빠르게 만드는 마케팅 콘텐츠 ✨<br>"
        "이미지와 문구 생성까지 한 번에! 복잡한 디자인 걱정 없이 바로 활용해보세요 🙌"
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown("")

def render_image_card() -> None:
    """
    좌측: 이미지 생성 카드
    - 예시 이미지, 결과 샘플, 생성 버튼
    """
    with st.container(border=True):
        st.image(ASSET_MAIN_INSTAGRAM_IMAGE)
        st.image(ASSET_MAIN_IMAGE, caption="OpenADProject로 생성된 이미지")
        if st.button("이미지 생성하기", type="primary", width="stretch", icon=":material/imagesmode:"):
            st.switch_page(ROUTE_IMAGE_INSTA)

def render_insta_text_card() -> None:
    """
    중앙: 인스타그램 문구 생성 카드
    - 예시 배너, 샘플 카피, 생성 버튼
    """
    with st.container(border=True):
        st.image(ASSET_MAIN_INSTAGRAM_TEXT)
        st.markdown(
            """
오래된 주택과 유럽 감성의 완벽한 조화✨

낮에도 즐기는 와인 한잔🍷  
고소한 커피와 달콤한 디저트까지  
모두 준비했어요.

1층부터 3층까지 감성 가득한 루프탑 카페에서 특별한 시간을 경험해보세요. 

The perfect harmony of an old house and European vibes✨

Enjoy a glass of wine🍷  
even during the day, with rich coffee and sweet desserts ready for you. 

Experience a special time at our rooftop café full of ambiance from the 1st to 3rd floor.

#성남카페 #카페투어 #커피 # 디저트 #카페 #백현동카페 #와인 # 유럽감성
            """
        )
        if st.button("광고 문구 생성하기", type="primary", width="stretch", icon=":material/border_color:"):
            st.switch_page(ROUTE_TEXT_INSTA)

def render_community_text_card() -> None:
    """
    우측: 커뮤니티 문구 생성 카드
    - 예시 배너, 샘플 카피, 생성 버튼
    """
    with st.container(border=True):
        st.image(ASSET_MAIN_COMMUNITY_TEXT)
        st.markdown(
            """
안녕하세요, 송도동 이웃 여러분 😊

처음 가게를 열 때부터 ‘동네에서 가까운 작은 쉼터’ 같은 네일샵을 만들고 싶었어요.   

손톱 케어뿐 아니라 나만의 스타일을 찾아가는 즐거움도 드리고 싶었고요. 
 
때로는 바쁜 일상에 지친 이웃분들이  
잠시 쉬어 가실 수 있도록 따뜻한 마음으로 서비스를 준비합니다. 

송도동 주변에 계시다면 편안한 마음으로 들러 주시고, 소소한 이야기 나누는 시간도 함께 나눠요. 

여러분 덕분에 저희 가게가  더 좋은 곳이  
되었습니다. 

언제든 반갑게 맞이할게요! 감사합니다 🌼
            """
        )
        if st.button("광고 문구 생성하기", type="primary", width="stretch", icon=":material/edit_note:"):
            st.switch_page(ROUTE_TEXT_COMM)

def render_main_page() -> None:
    """
    메인 페이지 렌더링
    - 전역 스타일 → 타이틀/태그라인 → 3열 카드
    """
    apply_global_styles()
    render_title_and_tagline()

    col1, col2, col3 = st.columns(3)
    with col1:
        render_image_card()
    with col2:
        render_insta_text_card()
    with col3:
        render_community_text_card()


def main() -> None:
    """
    엔트리 포인트
    """
    render_main_page()


if __name__ == "__main__":
    main()
