import streamlit as st
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any
from utils.generations_api import list_generations, delete_generation
import base64
from io import BytesIO

# 유틸
def require_login() -> None:
    """
    로그인 상태 확인
    - 토큰 없으면 경고 후 페이지 중단
    """
    token = st.session_state.get("access_token")
    if not token:
        st.warning("로그인이 필요합니다. 먼저 로그인 해주세요.")
        st.stop()

def parse_ts_kst(ts: str | None) -> datetime | None:
    """
    ISO8601 타임스탬프를 KST로 변환
    - UTC 기준 → 한국 시간대로 변환
    - 실패 시 None 반환
    """
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
    """
    이미지 생성 이력 불러오기
    - 서버에서 전체 생성 이력 조회
    - 이미지가 있는 항목만 필터링
    - 생성일 기준 최신순 정렬 후 반환
    """

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
    """
    개별 이미지 생성 이력 카드 렌더링
    - 생성 시간, 입력 텍스트, 결과 이미지 표시
    - 이미지 다운로드 기능
    - 삭제 버튼 제공 (삭제 후 페이지 새로고침)
    """
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

        col1, col2 = st.columns(2)
        with col1:
            try:
                # base64 데이터라면 분리
                if item["output_image_path"].startswith("data:image"):
                    header, b64data = item["output_image_path"].split(",", 1)
                    img_bytes = base64.b64decode(b64data)
                else:
                    # 혹시 파일 경로라면 로드
                    with open(item["output_image_path"], "rb") as f:
                        img_bytes = f.read()

                st.download_button(
                    label="이미지 다운로드",
                    data=img_bytes,
                    file_name=f"generated_{item['id']}.png",
                    mime="image/png",
                    width="stretch",
                    type="primary"
                )
            except Exception as e:
                st.error(f"다운로드 실패: {e}")

        with col2:
            if st.button("삭제하기", key=f"delete_txt_{item['id']}", width="stretch"):
                try:
                    resp = delete_generation(item["id"])
                    st.success(resp.get("message", "삭제 완료"))
                    st.rerun()
                except Exception as e:
                    st.error(f"삭제 실패: {e}")


def page_image_history() -> None:
    """
    이미지 보관함 페이지 렌더링
    - 로그인 체크 후 접근 가능
    - 이미지 생성 이력 불러와 최신순 출력
    - 카드 형태로 정보/이미지/버튼 표시
    - 다운로드 및 삭제 기능 지원
    - 이력 없을 시 안내 메시지 출력
    """
    require_login()
    st.image("assets/image_history.png")
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
