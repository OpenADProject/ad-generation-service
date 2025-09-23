import streamlit as st

def render_header() -> None:
    """
    상단 타이틀과 1번 안내를 출력합니다.
    """
    st.header("🤗 매출 상승을 위한 :blue[텍스트 생성] 가이드", divider="violet")
    st.write(" ")


# 채널 선택 버튼
def render_text_buttons(
    left_label: str = "인스타그램 광고문구 생성하기",
    left_page: str = "./pages/text_insta_page.py",
    right_label: str = "블로그 광고문구 생성하기",
    right_page: str = "./pages/text_blog_page.py",
    col_ratio: tuple[int, int] = (1, 1),          # (왼, 오) 컬럼 비율
    gap: str = "small",                           # small / medium / large
):
    """두 개의 버튼을 같은 행에 출력하고, 눌리면 해당 페이지로 이동합니다."""
    st.markdown("1. :red-background[마케팅 유형]을 선택하세요! 인스타그램과 블로그용 광고 문구를 간단하게 만들 수 있습니다.")
    col1, col2 = st.columns(col_ratio, gap=gap)

    with col1:
        if st.button(left_label, type="primary", use_container_width=True):
            st.switch_page(left_page)

    with col2:
        if st.button(right_label, type="primary", use_container_width=True):
            st.switch_page(right_page)

# 하단 가이드
def render_guides() -> None:
    """
    이미지 첨부, 선택 프롬프트, 텍스트 프롬프트 안내를 출력합니다.
    """
    st.write("2. 상품명, 말투 톤, 마케팅 대상을 :green-background[요청 사항]에 입력하면 맞춤형 문구가 생성됩니다.")
    st.write(
        "3. 해외 마케팅을 원한다면, :blue-background[영어 번역 옵션]도 추가할 수 있어요."
    )

def main() -> None:
    """
    텍스트 생성 가이드 페이지 렌더링 순서
    1) 헤더
    2) 채널 선택 버튼
    3) 하단 가이드
    """
    render_header()
    render_text_buttons()
    render_guides()

if __name__ == "__main__":
    main()
