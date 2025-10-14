import streamlit as st
from utils.generations_api import signup_user

# 회원가입 화면
def signup_page():
    """
    회원가입 페이지 렌더링
    - 아이디 / 비밀번호 입력 후 회원가입 처리
    - 비밀번호 확인 검증 (클라이언트 측)
    - 회원가입 성공 시 성공 메시지 및 로그인 이동 버튼 표시
    - 서버 오류 시 상세 에러 메시지 노출
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

    st.markdown("<h1 class='centered-text' style='color:#0b78db; font-size:80px;'>OpenADProject</h1>", unsafe_allow_html=True)
    st.markdown("")
    st.markdown(
        "<p class='centered-text' style= 'font-size:20px'> 가입을 통해 더 다양한 서비스를 만나보세요!</p>",
        unsafe_allow_html=True
    )    
    st.markdown("")

    # 세션 키 초기화
    if "signup_done" not in st.session_state:
        st.session_state.signup_done = False

    with st.form("login_form"):
        st.markdown(
            "<h3 class='centered-text'>회원가입</h3>",
            unsafe_allow_html=True
        )
        new_id = st.text_input("아이디", placeholder="아이디를 입력하세요.")
        st.markdown("")
        pw1 = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요.")
        pw2 = st.text_input("비밀번호 확인", type="password", placeholder="비밀번호를 재입력 해주세요.")
        st.markdown("")
        submitted = st.form_submit_button("가입하기", type="primary", width="stretch", icon=":material/how_to_reg:")

    if submitted:
        # 클라이언트 검증
        if not new_id or not pw1 or not pw2:
            st.error("아이디와 비밀번호를 모두 입력해주세요.")
            return
        if pw1 != pw2:
            st.error("비밀번호가 일치하지 않습니다.")
            return

        # 서버 호출
        ok, res = signup_user(new_id, pw1)
        if ok:
            st.session_state.signup_done = True
            st.success("회원가입 완료! 이제 로그인해 주세요.")
        else:
            if isinstance(res, dict):
                st.error(f"[{res.get('code')}] {res.get('message', '회원가입 실패')}")
                if res.get("errors"):
                    with st.expander("자세한 오류 보기"):
                        st.write(res["errors"])
            else:
                st.error(res)

    # 성공 후 이동 버튼
    if st.session_state.signup_done:
        if st.button("로그인 하기", use_container_width=True):
            st.switch_page("pages/login_page.py")

if __name__ == "__main__":
    signup_page()