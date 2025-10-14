import streamlit as st
from utils.generations_api import login_user

# 로그인 화면
def login_page():
    """
    로그인 페이지 렌더링
    - 서비스 접속 전 로그인 UI 제공
    - 아이디 / 비밀번호 입력 후 로그인 요청
    - 로그인 성공 시 토큰 저장 및 페이지 새로고침
    - 회원가입 버튼 클릭 시 회원가입 페이지로 이동
    """
    st.markdown(
        """
        <style>
        .centered-text {
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 제목 가운데 정렬
    st.markdown("<h1 class='centered-text' style='color:#0b78db; font-size:80px;'>OpenADProject</h1>", unsafe_allow_html=True)

    st.markdown("")
    # 안내 문구 가운데 정렬
    st.markdown(
        "<p class='centered-text' style= 'font-size:20px'> 로그인 후 서비스를 이용할 수 있습니다.</p>",
        unsafe_allow_html=True
    )

    st.markdown("")


    with st.form("login_form"):
        st.markdown(
            "<h3 class='centered-text'>로그인</h3>",
            unsafe_allow_html=True
        )
        username = st.text_input("아이디", placeholder="아이디를 입력하세요.")
        password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요.")
        st.markdown("")
        login_clicked = st.form_submit_button("로그인", type="primary", width="stretch", icon=":material/input:")
        signup_clicked = st.form_submit_button("회원가입", width="stretch", icon=":material/account_circle:")

    if login_clicked:
        token = login_user(username, password)
        if token:
            st.session_state['access_token'] = token
            st.session_state["username"] = username
            st.success("로그인 성공!")
            st.rerun()
        else:
            st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

    if signup_clicked:
        st.switch_page("pages/signup_page.py")

if __name__ == "__main__":
    login_page()