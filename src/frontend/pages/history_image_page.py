import streamlit as st
import requests
from datetime import datetime
from typing import List, Dict, Any

# 백엔드 서버 주소
BACKEND_URL = st.secrets["API_BASE"]

def parse_ts(ts: str) -> datetime:
    """ISO8601 created_at 문자열을 datetime으로 변환"""
    if not ts:
        return datetime.min
    if ts.endswith("Z"):
        ts = ts.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return datetime.min

def load_image_generations() -> List[Dict[str, Any]]:
    """이미지 결과물이 있는 생성 이력만 가져와 최신순으로 정렬"""
    resp = requests.get(f"{BACKEND_URL}/generations/", timeout=10)
    if resp.status_code != 200:
        raise RuntimeError("서버 연결 실패")

    all_generations = resp.json()
    items = [it for it in all_generations if it.get("output_image_path")]

    # created_at 기준 최신순
    items.sort(key=lambda it: parse_ts(it.get("created_at", "")), reverse=True)
    return items

def render_image_card(item: Dict[str, Any]) -> None:
    with st.container(border=True):
        st.caption(f"생성 시간: {item.get('created_at', '-')}")
        st.write("**입력 내용:**")
        st.info(item.get("input_text", "(입력 없음)"))

        st.image(item["output_image_path"], caption="생성된 이미지")

        if st.button("삭제하기", key=f"delete_img_{item['id']}", type="primary"):
            del_resp = requests.delete(f"{BACKEND_URL}/generations/{item['id']}", timeout=10)
            if del_resp.status_code == 200:
                st.success("삭제 완료")
                st.rerun()
            else:
                st.error("삭제 실패")

def page_image_history() -> None:
    st.header("이미지 생성 이력", divider="blue")
    try:
        items = load_image_generations()
        if not items:
            st.info("아직 생성된 이미지가 없습니다.")
            return

        for item in items:
            render_image_card(item)

    except Exception as e:
        st.error(f"서버 연결 실패: {e}")
        
if __name__ == "__main__":
    page_image_history()
