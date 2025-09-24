import streamlit as st
from PIL import Image

st.title(":blue[OpenADProject]")
st.markdown("")
st.markdown("AI로 더 쉽고 빠르게 만드는 마케팅 콘텐츠 ✨")
st.markdown("이미지와 문구 생성까지 한 번에! 복잡한 디자인 걱정 없이 바로 활용해보세요 🙌")
st.markdown(" ")


# 각 탭 설명
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True, height=550):
        st.image("assets/main_instagram_image.png", width=500)
        st.write("")
        st.image("assets/main_image.png", caption="OpenADProject로 생성된 이미지")
        st.write("")
        if st.button("인스타그램 이미지 생성하기", type="primary", width="stretch"):
            st.switch_page("./pages/image_insta_page.py")       

with col2:
    with st.container(border=True, height=550):
        st.image("assets/main_instagram_text.png", width=620)
        st.code(
            """지금 레이어드컷 50% 할인 중이에요!  

봄 맞이 변신,  
가볍고 세련되게 스타일 업 해보세요~  
예약은 서둘러 주세요!  

#레이어드컷 #LayeredCut #50%할인"""
        )
        st.code(
            """달콤 상큼한 한 입! 
청포도맛 사탕으로 기분 전환하세요🍬💚  
지금 바로 달콤함 충전 타임!

#청포도사탕 #CandyTime #상큼달콤""")

        if st.button("인스타그램 광고문구 생성하기", type="primary", width="stretch"):
            st.switch_page("./pages/text_insta_page.py")       
