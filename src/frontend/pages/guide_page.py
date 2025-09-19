import streamlit as st

# 라우트 상수 (페이지 경로 관리)
IMAGE_MAIN_ROUTE = "./pages/image_main_page.py"
TEXT_MAIN_ROUTE  = "./pages/text_main_page.py"

def render_header() -> None:
    """
    상단 타이틀과 한 줄 소개, 사용 안내를 출력합니다.
    """
    st.title(":rainbow[OpenADProject] 사용 가이드")
    st.write("OpenADProject는 소상공인 여러분들의 마케팅 어려움을 덜어드리고, 매출 상승을 위해 제작되었습니다!🍀")
    st.write("OpenADProject는 이미지와 텍스트 생성이 가능해요.  \n이미지와 텍스트 가이드를 읽어보고 버튼을 눌러 시작하세요!")

def bullet(text: str) -> None:
    """
    안내 문구 한 줄을 출력합니다.
    - 줄바꿈/배경 하이라이트 마크다운을 그대로 사용할 수 있습니다.
    """
    st.write(text)

# 이미지 생성 섹션
def render_image_section() -> None:
    """
    '이미지 생성' 섹션을 렌더링하고 CTA 버튼을 제공합니다.
    """
    st.subheader("🤩 매출 상승을 위한 :blue[이미지 생성]", divider="violet")
    bullet("1. 먼저 :red-background[마케팅 유형]을 선택해주세요. 인스타그램과 블로그를 위한 마케팅 이미지 생성이 가능합니다.")
    bullet("2. 이미지 생성을 위해 홍보할 제품이나 참고할 :orange-background[이미지]를 첨부해주세요. 이미지가 없다면 생략 가능합니다.")
    bullet("3. 프롬프트 작성이 어렵다면 :green-background[선택 프롬프트]에서 사용해봐요.  \n이미지의 카테고리, 분위기, 배경 등을 선택할 수 있어요.")
    bullet("4. 직접 요청을 원한다면, :blue-background[텍스트 프롬프트]에서 작성이 가능해요.")
    bullet("⬇️⬇️⬇️ 독창적인 이미지 생성을 원한다면 아래 버튼을 눌러주세요!!😄")

    if st.button("이미지 생성하기", type="primary"):
        st.switch_page(IMAGE_MAIN_ROUTE)

# 텍스트 생성 섹션
def render_text_section() -> None:
    """
    '텍스트 생성' 섹션을 렌더링하고 CTA 버튼을 제공합니다.
    """
    st.subheader("🤗 매출 상승을 위한 :blue[텍스트 생성]", divider="violet")
    bullet("1. 먼저 :red-background[마케팅 유형]을 선택해주세요. 인스타그램과 블로그를 위한 마케팅 문구 생성이 가능합니다.")
    bullet("2. 광고 문구 생성을 위해 홍보할 제품이나 참고할 :orange-background[이미지]를 첨부해주세요.  \n이미지가 없다면 생략 가능합니다.")
    bullet("3. 프롬프트 작성이 어렵다면 :green-background[선택 프롬프트]에서 사용해봐요.  \n이미지의 카테고리, 분위기, 배경 등을 선택할 수 있어요.")
    bullet("4. 직접 요청을 원한다면, :blue-background[텍스트 프롬프트]에서 작성이 가능해요.")
    bullet("⬇️⬇️⬇️ 센스있는 광고 문구 생성을 원한다면 아래 버튼을 눌러주세요!!😄")

    if st.button("텍스트 생성하기", type="primary"):
        st.switch_page(TEXT_MAIN_ROUTE)

def main() -> None:
    """
    메인 가이드 페이지 렌더링 순서
    1) 상단 타이틀/인트로
    2) 이미지 생성 섹션
    3) 텍스트 생성 섹션
    """
    render_header()
    render_image_section()
    render_text_section()

if __name__ == "__main__":
    main()
