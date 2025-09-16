import streamlit as st

st.header("🤗 매출 상승을 위한 :blue[텍스트 생성] 가이드", divider="violet")
st.write("1. 먼저 아래 버튼에 있는 :red-background[마케팅 대상]을 선택해주세요.  \n인스타그램과 블로그를 위한 마케팅 문구 생성이 가능합니다.")

st.write("⬇️ 인스타그램에 게시할 광고 문구 생성을 원한다면 아래 버튼을 눌러주세요!!😄")
if st.button("인스타그램 마케팅을 위한 텍스트 생성하기"):
    st.switch_page("./pages/text_insta_page.py")

st.write("⬇️ 블로그에 게시할 광고 문구 생성을 원한다면 아래 버튼을 눌러주세요!!😄")    
if st.button("블로그 마케팅을 위한 텍스트 생성하기"):
    st.switch_page("./pages/text_blog_page.py")


st.write("2. 광고 문구 생성을 위해 홍보할 제품이나 참고할 :orange-background[이미지]를 첨부해주세요.  \n이미지가 없다면 생략 가능합니다.")
st.write("3. 프롬프트 작성이 어렵다면 :green-background[선택 프롬프트]에서 사용해봐요.  \n이미지의 카테고리, 분위기, 배경 등을 선택할 수 있어요.")
st.write("4. 직접 요청을 작성하고 싶다면, :blue-background[텍스트 프롬프트]에 사용해봐요.")

