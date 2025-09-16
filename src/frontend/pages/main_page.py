import streamlit as st
# st.title("🥳 성공적인 홍보를 위한 :rainbow[OpenADProject] 사용 가이드")
st.title(":rainbow[OpenADProject] 사용 가이드")
st.write("OpenADProject는 소상공인 여러분들의 마케팅 어려움을 덜어드리고, 매출 상승을 위해 제작되었습니다!🍀")
st.write("OpenADProject는 이미지와 텍스트 생성이 가능해요.  \n이미지와 텍스트 가이드를 읽어보고 버튼을 눌러 시작하세요!")

#-------------------------------------------------------------------
st.subheader("🤩 매출 상승을 위한 :blue[이미지 생성]", divider="violet")
st.write("1. 먼저 :red-background[마케팅 유형]을 선택해주세요. 인스타그램과 블로그를 위한 마케팅 이미지 생성이 가능합니다.")
st.write("2. 이미지 생성을 위해 홍보할 제품이나 참고할 :orange-background[이미지]를 첨부해주세요. 이미지가 없다면 생략 가능합니다.")
st.write("3. 프롬프트 작성이 어렵다면 :green-background[선택 프롬프트]에서 사용해봐요.  \n이미지의 카테고리, 분위기, 배경 등을 선택할 수 있어요.")
st.write("4. 직접 요청을 원한다면, :blue-background[텍스트 프롬프트]에서 작성이 가능해요.")
st.write("⬇️⬇️⬇️ 독창적인 이미지 생성을 원한다면 아래 버튼을 눌러주세요!!😄")

if st.button("이미지 생성하기"):
    st.switch_page("./pages/image_main_page.py")

st.subheader("🤗 매출 상승을 위한 :blue[텍스트 생성]", divider="violet")
st.write("1. 먼저 :red-background[마케팅 유형]을 선택해주세요. 인스타그램과 블로그를 위한 마케팅 문구 생성이 가능합니다.")
st.write("2. 광고 문구 생성을 위해 홍보할 제품이나 참고할 :orange-background[이미지]를 첨부해주세요.  \n이미지가 없다면 생략 가능합니다.")
st.write("3. 프롬프트 작성이 어렵다면 :green-background[선택 프롬프트]에서 사용해봐요.  \n이미지의 카테고리, 분위기, 배경 등을 선택할 수 있어요.")
st.write("4. 직접 요청을 원한다면, :blue-background[텍스트 프롬프트]에서 작성이 가능해요.")
st.write("⬇️⬇️⬇️ 센스있는 광고 문구 생성을 원한다면 아래 버튼을 눌러주세요!!😄")

if st.button("텍스트 생성하기"):
    st.switch_page("./pages/text_main_page.py")