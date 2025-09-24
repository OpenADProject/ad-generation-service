import streamlit as st
from utils.generations_api import login_user





# 로그인 화면
def login_page():
    st.title(":blue[Login]")
    st.markdown("")
    st.markdown("OpenADProject에 오신 걸 환영합니다! 👋  \n로그인 후 서비스를 이용할 수 있습니다.")
    st.markdown("")

    with st.form("login_form"):
        username = st.text_input("ID", placeholder="아이디를 입력하세요.")
        st.markdown("")
        password = st.text_input("Password", type="password", placeholder="비밀번호를 입력하세요.")
        st.markdown("")
        submitted = st.form_submit_button("**Login**", type="primary")
        if submitted:
            token = login_user(username, password)
            if token:
                st.success("로그인에 성공했습니다!")
                # 로그인 성공 시 session_state에 토큰 저장
                st.session_state['token'] = token
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")


if __name__ == "__main__":
    login_page()