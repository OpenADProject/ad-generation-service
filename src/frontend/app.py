"""
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

from pathlib import Path
import streamlit as st

def setup_page() -> None:
    """
    Streamlit 전역 설정을 초기화합니다.
    - 앱 제목과 아이콘을 지정
    - 로고 이미지를 상단에 표시
    """
    st.set_page_config(page_title="OpenADProject", page_icon="./assets/OAP.jpg")
    try:
        st.logo("./assets/logo.png", size="large")
    except Exception:
        pass

# 페이지 정의
def build_pages() -> dict:
    """
    네비게이션 메뉴에 들어갈 페이지 구조를 정의합니다.
    - Home: 메인 사용법 안내
    - 이미지 생성: 인스타/블로그용 이미지 생성 기능
    - 텍스트 생성: 인스타/블로그용 텍스트 생성 기능
    - History: 생성한 이미지/텍스트 보관함
    """
    base = Path(__file__).parent  # app.py 기준 상대 경로 안전화
    p = base / "pages"

    return {
        "Home": [
            st.Page(str(p / "main_page.py"), title="💡 OpenAD 사용법"),
        ],
        "📷 이미지 생성": [
            st.Page(str(p / "image_main_page.py"), title="이미지 생성 가이드"),
            st.Page(str(p / "image_insta_page.py"), title="인스타그램 이미지 생성"),
            st.Page(str(p / "image_blog_page.py"), title="블로그 이미지 생성"),
        ],
        "✏️ 텍스트 생성": [
            st.Page(str(p / "text_main_page.py"), title="텍스트 생성 가이드"),
            st.Page(str(p / "text_insta_page.py"), title="인스타그램 텍스트 생성"),
            st.Page(str(p / "text_blog_page.py"), title="블로그 텍스트 생성"),
        ],
        "📁 History": [
            st.Page(str(p / "history_image_page.py"), title="이미지 보관함"),
            st.Page(str(p / "history_text_page.py"), title="텍스트 보관함"),
        ],
    }

# navigation 설정
def run_navigation(pages: dict) -> None:
    """
    Streamlit의 navigation 기능을 실행합니다.
    - build_pages()로 정의된 딕셔너리를 받아 네비게이션 구성
    - 선택된 페이지를 실행(run)
    """
    pg = st.navigation(pages)
    pg.run()

def main() -> None:
    setup_page()
    pages = build_pages()
    run_navigation(pages)

if __name__ == "__main__":
    main()