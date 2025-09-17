import streamlit as st

def render_header() -> None:
    """
    상단 타이틀과 1번 안내를 출력합니다.
    """
    st.header("🤗 매출 상승을 위한 :blue[텍스트 생성] 가이드", divider="violet")
    st.write(
        "1. 먼저 아래 버튼에 있는 :red-background[마케팅 대상]을 선택해주세요.  \n"
        "인스타그램과 블로그를 위한 마케팅 문구 생성이 가능합니다."
    )

# 채널 선택 버튼
def render_channel_buttons() -> None:
    """
    인스타그램/블로그용 텍스트 생성 버튼을 렌더링합니다.
    """
    st.write("⬇️ 인스타그램에 게시할 광고 문구 생성을 원한다면 아래 버튼을 눌러주세요!!😄")
    if st.button("인스타그램 마케팅을 위한 텍스트 생성하기", type="primary"):
        st.switch_page("./pages/text_insta_page.py")

    st.write("⬇️ 블로그에 게시할 광고 문구 생성을 원한다면 아래 버튼을 눌러주세요!!😄")
    if st.button("블로그 마케팅을 위한 텍스트 생성하기", type="primary"):
        st.switch_page("./pages/text_blog_page.py")

# 하단 가이드
def render_guides() -> None:
    """
    이미지 첨부, 선택 프롬프트, 텍스트 프롬프트 안내를 출력합니다.
    """
    st.write(
        "2. 광고 문구 생성을 위해 홍보할 제품이나 참고할 :orange-background[이미지]를 첨부해주세요.  \n"
        "이미지가 없다면 생략 가능합니다."
    )
    st.write(
        "3. 프롬프트 작성이 어렵다면 :green-background[선택 프롬프트]에서 사용해봐요.  \n"
        "이미지의 카테고리, 분위기, 배경 등을 선택할 수 있어요."
    )
    st.write(
        "4. 직접 요청을 작성하고 싶다면, :blue-background[텍스트 프롬프트]에 사용해봐요."
    )

def main() -> None:
    """
    텍스트 생성 가이드 페이지 렌더링 순서
    1) 헤더
    2) 채널 선택 버튼
    3) 하단 가이드
    """
    render_header()
    render_channel_buttons()
    render_guides()

if __name__ == "__main__":
    main()
