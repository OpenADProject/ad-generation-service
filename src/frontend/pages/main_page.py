import streamlit as st
from PIL import Image

# # 두 개의 컬럼 생성 (비율 1:2)
# col1, col2 = st.columns([1, 2])

# with col1:
#     st.image("assets/OAP.jpg", width=200)

# with col2:
#     st.markdown(
#         """
#         ### OpenADProject  

#         **OpenADProject**는 소상공인 여러분들의 마케팅 부담을 덜고,  
#         매출 상승을 돕기 위해 제작된 AI 기반 콘텐츠 생성 플랫폼입니다.🍀  

#         이제는 복잡한 디자인 도구나 카피라이팅 고민 없이,  
#         원하는 이미지와 텍스트를 자동으로 생성하여<br>
#         쉽고 빠르게 마케팅에 활용해보세요!
#         """,
#         unsafe_allow_html=True
#     )


# st.divider()

# col1, col2 = st.columns([2, 1])

# with col1:
#     st.markdown("")

# with col2:
#     st.image("assets/main_image.png", , caption="OpenAD로 생성된 이미지")

st.title(":blue[OpenADProject]")
st.markdown("")
st.markdown("AI로 더 쉽고 빠르게 만드는 마케팅 콘텐츠 ✨")
st.markdown("이미지와 문구 생성까지 한 번에! 복잡한 디자인 걱정 없이 바로 활용해보세요 🙌")
st.markdown(" ")


# 각 탭 설명
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True, height=550):
        st.image("assets/main_instagram_image.png", width=580)
        st.write("")
        st.image("assets/main_image.png", caption="OpenAD로 생성된 이미지")
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
