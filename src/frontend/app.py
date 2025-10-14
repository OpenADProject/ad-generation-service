from pathlib import Path
import streamlit as st

def setup_page() -> None:
    """
    전역 페이지 설정
    - 페이지 제목/아이콘 지정
    - 상단 로고 표시(실패 시 무시)
    - 컨테이너 여백/폭 스타일 적용
    """
    st.set_page_config(page_title="OpenADProject", page_icon="./assets/OAP.jpg")
    try:
        st.logo("./assets/logo.png", size="large")
    except Exception:
        pass

    st.markdown(
        """
        <style>
        /* 전체 컨테이너 상단 여백 줄이기 */
        .block-container {
            padding-top: 2rem;   /* 기본은 6rem 정도 */
            padding-bottom: 4rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <style>
            .block-container {
                padding-left: 4rem;
                padding-right: 4rem;
                max-width: 80%;
            }
        </style>
        """,
        unsafe_allow_html=True
    )    

def load_custom_font():
    """
    커스텀 웹폰트 등록 및 전역 적용
    - @font-face로 폰트 선언
    - .stApp 전역에 강제 적용
    - 머티리얼 아이콘 폰트는 예외 처리
    """
    st.markdown("""
    <style>
    /* 폰트 등록: '이름' ↔ 파일 매핑 */
    @font-face {
      font-family: 'NoonnuBasicGothic';
      src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/noon-2410@1.0/NoonnuBasicGothicRegular.woff2') format('woff2');
      font-weight: 400;
      font-style: normal;
      font-display: swap;
    }

    /* 전역 강제 적용 (.stApp 기준 + !important) */
    .stApp, .stApp * {
      font-family: 'NoonnuBasicGothic', 'Noto Sans KR',
                   -apple-system, BlinkMacSystemFont, 'Segoe UI',
                   Roboto, 'Helvetica Neue', Arial, sans-serif !important;
    }

    /* 머티리얼 아이콘은 예외 (텍스트 노출 방지) */
    .material-icons, .material-icons-outlined, .material-icons-round,
    .material-icons-sharp, .material-icons-two-tone,
    .material-symbols-outlined, .material-symbols-rounded, .material-symbols-sharp {
      font-family: 'Material Icons', 'Material Symbols Outlined',
                   'Material Symbols Rounded', 'Material Symbols Sharp' !important;
      -webkit-font-feature-settings: 'liga';
      font-feature-settings: 'liga';
    }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar_status():
    """
    사이드바 상태 영역
    - 로그인 유저 환영 문구 표시
    - 로그아웃 버튼 제공(토큰 삭제 후 rerun)
    """
    with st.sidebar:
        if "access_token" in st.session_state:
            user_id = st.session_state.get("username", "사용자")
            st.markdown(f"**{user_id}님** 환영합니다!🤗")
            if st.button("로그아웃", type="primary", width="stretch", icon=":material/logout:"):
                st.session_state.pop("access_token", None)  # 안전하게 삭제
                st.rerun()  # 상태 갱신 → 로그인 페이지로 이동


# 페이지 정의
def build_pages() -> dict:
    """
    네비게이션 페이지 구성
    - 로그인 전: 로그인/회원가입만 노출
    - 로그인 후: 홈/이미지 생성/문구 생성/보관함 메뉴 반환
    - 경로는 app.py 기준 상대 경로로 안전화
    """
    base = Path(__file__).parent  # app.py 기준 상대 경로 안전화
    p = base / "pages"
    is_logged_in = bool(st.session_state.get("access_token"))

    if not is_logged_in:
        # 로그인 전: 로그인 페이지만 보여주기
        return {
            "🔐 Auth": [
                st.Page(str(p / "login_page.py"), title="로그인", icon=":material/login:"),
                st.Page(str(p / "signup_page.py"), title="회원가입", icon=":material/account_circle:"),
            ]
        }

    # 로그인 후: 전체 메뉴 노출
    return {
        "🏠 Home": [
            st.Page(str(p / "main_page.py"), title="메인 페이지", icon=":material/dashboard:"),
        ],
        "📷 이미지 생성": [
            st.Page(str(p / "image_main_page.py"), title="이미지 생성 가이드", icon=":material/menu_book:"),
            st.Page(str(p / "image_insta_page.py"), title="인스타그램", icon=":material/numbers:"),
        ],
        "✏️ 광고문구 생성": [
            st.Page(str(p / "text_main_page.py"), title="광고 문구 가이드", icon=":material/menu_book:"),
            st.Page(str(p / "text_insta_page.py"), title="인스타그램 / 네이버 플레이스", icon=":material/numbers:"),
            st.Page(str(p / "text_community_page.py"), title="당근마켓 / 지역카페", icon=":material/diversity_1:"),
        ],
        "📁 보관함": [
            st.Page(str(p / "history_image_page.py"), title="이미지 보관함", icon=":material/image:"),
            st.Page(str(p / "history_text_page.py"), title="광고문구 보관함", icon=":material/border_color:"),
            st.Page(str(p / "history_model_page.py"), title="모델 보관함", icon=":material/sentiment_satisfied:"),
        ],
    }

# navigation 설정
def run_navigation(pages: dict) -> None:
    """
    네비게이션 실행
    - st.navigation으로 메뉴 구성
    - 선택된 페이지 run()
    """
    pg = st.navigation(pages)
    pg.run()

def main() -> None:
    """
    앱 엔트리 포인트
    - 전역 설정 → 사이드바 상태 → 페이지 구성 → 네비게이션 실행
    """
    setup_page()
    # load_custom_font()
    render_sidebar_status() 
    pages = build_pages()
    run_navigation(pages)

if __name__ == "__main__":
    main()