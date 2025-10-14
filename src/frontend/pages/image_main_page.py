import streamlit as st
from PIL import Image

# 헤더/인트로
def render_header() -> None:
    """
    상단 타이틀 섹션 렌더링
    - 페이지 헤더 및 첫 안내 문구 출력
    """
    st.header(":material/menu_book: &nbsp; 매출 상승을 위한 :blue[이미지 생성] 가이드")
    st.write("")

# 이미지 생성 버튼 섹션
def render_image_buttons(
    left_label: str = "인스타그램 이미지 생성하기",
    left_page: str = "./pages/image_insta_page.py",
):
    """
    상단 타이틀 섹션 렌더링
    - 페이지 헤더 및 첫 안내 문구 출력
    """
    if st.button(left_label, type="primary", width='stretch'):
        st.switch_page(left_page)

# 추가 안내 섹션
def render_additional_guides() -> None:
    """
    이미지 생성 가이드를 표시하는 함수
    - 업로드, 요청 사항, 모델 선택, 프롬프트 관련 설명
    """
    st.markdown("1. 홍보할 상품이나 매장 :red-background[이미지]를 업로드하세요.")
    st.markdown("2. 상호명, 배경, 마케팅 대상, 이미지 사이즈를 :yellow-background[요청 사항]에 작성해주세요.")
    st.markdown("3. :green-background[모델 선택]도 가능하며, 왼쪽 History 탭의 모델 보관함에서 내 모델을 등록할 수 있습니다.")
    st.markdown("4. 원하는 내용을 :violet-background[직접 요청]하여 맞춤형 이미지를 만들어보세요.")
    st.write("")

def main() -> None:
    """
    페이지 엔트리 포인트
    - 헤더 → 추가 안내 → 이미지 생성 버튼 출력
    """
    render_header()
    render_additional_guides()
    render_image_buttons()

if __name__ == "__main__":
    main()