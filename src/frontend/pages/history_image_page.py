import streamlit as st
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any
from utils.generations_api import list_generations, delete_generation

# 유틸
def require_login() -> None:
    """로그인 토큰 없으면 작업 중단"""
    token = st.session_state.get("access_token")
    if not token:
        st.warning("로그인이 필요합니다. 먼저 로그인 해주세요.")
        st.stop()

def parse_ts_kst(ts: str | None) -> datetime | None:
    """ISO8601 문자열을 UTC로 파싱 후 KST로 변환. 실패 시 None."""
    if not ts:
        return None
    s = ts.replace("Z", "+00:00") if ts.endswith("Z") else ts
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(ZoneInfo("Asia/Seoul"))
    except Exception:
        return None


# 데이터 로딩
def load_image_generations() -> List[Dict[str, Any]]:
    """이미지 결과물이 있는 생성 이력만 가져와 최신순으로 정렬해서 반환"""

    # 래퍼 내부에서 4xx/5xx -> requests.HTTPError 발생
    all_items = list_generations(skip=0, limit=100)
    
    # 이미지가 있는 것만
    items = [it for it in all_items if it.get("output_image_path")]

    # created_at 기준 최신순
    def _key(it: Dict[str, Any]):
        dt = parse_ts_kst(it.get("created_at"))
        return dt or datetime.min.replace(tzinfo=ZoneInfo("Asia/Seoul"))

    items.sort(key=_key, reverse=True)
    return items

# 렌더
def render_image_card(item: Dict[str, Any]) -> None:
    with st.container(border=True):
        created_at = parse_ts_kst(item.get("created_at"))
        created_str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else "-"

        st.caption(f"생성 시간: {created_str}")

        st.write("**입력 내용**")
        input_txt = item.get("input_text", "(입력 없음)")
        st.info(input_txt.replace("\n", "  \n"))
        st.write("")
        
        st.write("**생성된 광고 이미지**")
        st.image(item["output_image_path"], caption="생성된 이미지")

        if st.button("삭제하기", key=f"delete_img_{item['id']}", type="primary"):
            try:
                resp = delete_generation(item["id"])
                st.success(resp.get("message", "삭제 완료"))
                st.rerun()
            except Exception as e:
                st.error(f"삭제 실패: {e}")


def page_image_history() -> None:
    require_login()

    st.header("이미지 생성 이력", divider="blue")
    try:
        items = load_image_generations()
    except Exception as e:
        st.error(f"서버 통신 중 오류가 발생했습니다: {e}")
        return

    if not items:
        st.info("아직 생성된 이미지가 없습니다.")
        return

    for item in items:
        render_image_card(item)


if __name__ == "__main__":
    page_image_history()
