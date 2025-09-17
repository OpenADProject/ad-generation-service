import streamlit as st
import requests

# 백엔드 서버 주소
BACKEND_URL = st.secrets["API_BASE"]

st.header("텍스트 생성 이력", divider="violet")

try:
    # GET 요청으로 모든 이력 조회
    response = requests.get(f"{BACKEND_URL}/generations/")
    
    if response.status_code == 200:
        all_generations = response.json()
        
        # 텍스트 결과물이 있는 데이터만 필터링
        text_generations = [
            item for item in all_generations if item.get("output_text")
        ]
        
        if not text_generations:
            st.info("아직 생성된 텍스트가 없습니다.")
            
        # 최신순으로 화면에 표시
        for item in reversed(text_generations):
            with st.container(border=True):
                # 생성 시간과 입력값 표시
                st.caption(f"생성 시간: {item['created_at']}")
                st.write("**입력 내용:**")
                st.info(item['input_text'])
                
                # 생성된 텍스트를 복사하기 편하게 code 블록으로 표시
                st.write("**생성된 광고 문구:**")
                st.code(item['output_text'])
                
                # 삭제 버튼
                if st.button("삭제하기", key=f"delete_txt_{item['id']}", type="primary"):
                    del_response = requests.delete(f"{BACKEND_URL}/generations/{item['id']}")
                    if del_response.status_code == 200:
                        st.success()
                        st.rerun()
                    else:
                        st.error("삭제 실패")

    else:
        st.error("서버 연결 실패")

except Exception as e:
    st.error(f"서버 연결 실패: {e}")