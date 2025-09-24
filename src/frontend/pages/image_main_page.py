import streamlit as st
from PIL import Image

# 헤더/인트로
def render_header() -> None:
    """
    상단 섹션: 타이틀 및 첫 번째 안내 출력
    """
    st.header("🤩 매출 상승을 위한 :blue[이미지 생성] 가이드", divider="violet")
    st.write("")

# 이미지 생성 버튼 섹션
def render_image_buttons(
    left_label: str = "인스타그램 이미지 생성하기",
    left_page: str = "./pages/image_insta_page.py",
    right_label: str = "블로그 이미지 생성하기",
    right_page: str = "./pages/image_blog_page.py",
    col_ratio: tuple[int, int] = (1, 1),          # (왼, 오) 컬럼 비율
    gap: str = "small",                           # small / medium / large
):
    """두 개의 버튼을 같은 행에 출력하고, 눌리면 해당 페이지로 이동합니다."""
    st.markdown("1. :red-background[마케팅 유형]을 선택하세요! 인스타그램과 블로그용 이미지를 손쉽게 만들 수 있습니다.")
    col1, col2 = st.columns(col_ratio, gap=gap)

    with col1:
        if st.button(left_label, type="primary", use_container_width=True):
            st.switch_page(left_page)

    with col2:
        if st.button(right_label, type="primary", use_container_width=True):
            st.switch_page(right_page)

# 추가 안내 섹션
def render_additional_guides() -> None:
    """
    이미지 업로드, 선택 프롬프트, 텍스트 프롬프트 안내를 출력합니다.
    """
    st.markdown("2. 홍보할 상품이나 매장 :yellow-background[이미지]를 업로드하세요.")
    st.markdown("3. 상호명, 배경, 마케팅 대상, 이미지 사이즈를 :green-background[요청 사항]에 작성해주세요.")
    st.markdown("4. :blue-background[모델 선택]도 가능하며, 왼쪽 History 탭의 모델 보관함에서 내 모델을 등록할 수 있습니다.")
    st.markdown("5. 원하는 내용을 :violet-background[직접 요청]하여 맞춤형 이미지를 만들어보세요.")

def main() -> None:
    """
    이미지 생성 메인 페이지 렌더링 순서
    1) 헤더
    2) 인스타그램 버튼
    3) 블로그 버튼
    4) 추가 안내
    """
    render_header()
    render_image_buttons()
    render_additional_guides()

if __name__ == "__main__":
    main()