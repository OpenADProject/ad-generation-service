import streamlit as st

def render_header() -> None:
    """
    상단 타이틀 섹션 렌더링
    - 페이지 헤더 및 안내 문구 출력
    """
    st.header(":material/menu_book: &nbsp; 매출 상승을 위한 :blue[광고문구 생성] 가이드")
    st.write(" ")


# 채널 선택 버튼
def render_text_buttons(
    left_label: str = "인스타그램 / 네이버 플레이스 광고문구 생성",
    left_page: str = "./pages/text_insta_page.py",
    right_label: str = "당근마켓 / 지역카페 광고문구 생성",
    right_page: str = "./pages/text_community_page.py",
    col_ratio: tuple[int, int] = (1, 1),          # (왼, 오) 컬럼 비율
    gap: str = "small",                           # small / medium / large
):
    """
    광고 문구 생성 채널 선택 버튼 렌더링
    - 인스타그램/네이버 플레이스, 당근마켓/지역카페용 버튼
    - 클릭 시 해당 생성 페이지로 이동
    """
    col1, col2 = st.columns(col_ratio, gap=gap)

    with col1:
        if st.button(left_label, type="primary", width="stretch"):
            st.switch_page(left_page)

    with col2:
        if st.button(right_label, type="primary", width="stretch"):
            st.switch_page(right_page)

# 하단 가이드
def render_guides() -> None:
    """
    광고 문구 생성 방법 안내 문구 출력
    - 입력 항목 및 기능 설명
    """
    st.markdown("1. :red-background[인스타그램 / 네이버플레이스], :orange-background[당근마켓 / 지역카페] 광고 문구를 간단히 생성해 보세요.")
    st.write("2. 상품명, 말투 톤, 마케팅 대상을 :blue-background[요청 사항]에 입력하면 맞춤형 문구가 생성됩니다.")
    st.write("3. 해외 마케팅을 원한다면, :green-background[영어 번역 옵션]도 추가할 수 있어요.")
    st.write("4. :violet-background[지역]을 선택하면 해시태그에 반영되어, 마케팅 효과를 더욱 높일 수 있어요.")
    st.write("")

def main() -> None:
    """
    메인 페이지 엔트리 포인트
    - 헤더 → 가이드 → 채널 선택 버튼 순서로 렌더링
    """
    render_header()
    render_guides()
    render_text_buttons()

if __name__ == "__main__":
    main()
