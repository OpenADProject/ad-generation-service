"""
1. 기능 개요
- 채널: 인스타그램 / 블로그 (택1)
- 출력: 텍스트 / 이미지 (둘 다 지원)
- 입력: 텍스트 or 텍스트&이미지 → 선택 프롬프트 / 텍스트 프롬프트 택 1 필수
    - A) 이미지 업로드
    - B) 선택 프롬프트
        - 홍보물 분류(상품: 음식/의류/화장품/가전, 서비스: 헬스장/미용실/음식점)
        - 주변의 물체 /장소 / 이미지 분위기
        - 문구 톤: 친근 / 반말 / 정중
    - C) 텍스트 프롬프트
        - 자유 형식의 요청사항 작성 (예시 문구 제공)
- 개발 목표
    - 사용자(소상공인) 연령을 고려하여 작동 하기 편리한 설계
    - 메인 화면에 작동 방법, 각 기능마다 사용 방법 제시
"""

import streamlit as st

st.set_page_config(page_title="OpenADProject", page_icon="./assets/OAP.jpg")

st.logo("./assets/logo.png", size="large")

# CSS 추가
st.markdown(
    """
    <style>
    /* 네비게이션 타이틀 크기 키우기 */
    .st-emotion-cache-1v0mbdj {   /* streamlit 내부 클래스 (버전에 따라 다를 수 있음) */
        font-size: 40px !important;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# 페이지 정의
pages = {
    "Home": [
        st.Page("./pages/main_page.py", title="💡 OpenAD 사용법"),
    ],
    "📷 이미지 생성": [
        st.Page("./pages/image_main_page.py", title="이미지 생성 가이드"),
        st.Page("./pages/image_insta_page.py", title="인스타그램 이미지 생성"),
        st.Page("./pages/image_blog_page.py", title="블로그 이미지 생성")
    ],
    "✏️ 텍스트 생성": [
        st.Page("./pages/text_main_page.py", title="텍스트 생성 가이드"),
        st.Page("./pages/text_insta_page.py", title="인스타그램 텍스트 생성"),
        st.Page("./pages/text_blog_page.py", title="블로그 텍스트 생성")
    ],
    "📁 History": [
        st.Page("./pages/history_image_page.py", title="이미지 보관함"),
        st.Page("./pages/history_text_page.py", title="텍스트 보관함"),
    ],
}

# navigation 설정
pg = st.navigation(pages)

pg.run()

