import streamlit as st
from PIL import Image


# 두 개의 컬럼 생성 (비율 1:2)
col1, col2 = st.columns([1, 2])

with col1:
    st.image("assets/OAP.jpg", width=200)

with col2:
    st.markdown(
        """
        ### OpenADProject  

        **OpenADProject**는 소상공인 여러분들의 마케팅 부담을 덜고,  
        매출 상승을 돕기 위해 제작된 AI 기반 콘텐츠 생성 플랫폼입니다.🍀  

        이제는 복잡한 디자인 도구나 카피라이팅 고민 없이,  
        원하는 이미지와 텍스트를 자동으로 생성하여<br>
        쉽고 빠르게 마케팅에 활용해보세요!
        """,
        unsafe_allow_html=True
    )


st.divider()

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("")

with col2:
    st.image("assets/main_image.png", width=200, caption="OpenAD로 생성된 이미지")