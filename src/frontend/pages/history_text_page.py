import streamlit as st
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any
from utils.generations_api import list_generations, delete_generation
from st_copy import copy_button

# 공통 유틸
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
def load_text_generations() -> List[Dict[str, Any]]:
    """
    텍스트 생성 이력 불러오기
    - 서버에서 전체 생성 이력 조회
    - output_text가 있는 항목만 필터링
    - 생성일 기준 최신순 정렬 후 반환
    """
    all_items = list_generations(skip=0, limit=100)

    # output_text가 있는 아이템만 필터
    items = [it for it in all_items if it.get("output_text")]

    # created_at 기준 최신순 정렬
    def _key(it: Dict[str, Any]):
        dt = parse_ts_kst(it.get("created_at"))
        # created_at이 없거나 파싱 실패 시 가장 오래된 시간으로 간주
        return dt or datetime.min.replace(tzinfo=ZoneInfo("Asia/Seoul"))

    items.sort(key=_key, reverse=True)
    return items

# 렌더링
def render_text_card(item: Dict[str, Any]) -> None:
    """
    개별 텍스트 생성 이력 카드 렌더링
    - 생성 시간, 입력 프롬프트, 결과 문구 표시
    - 복사(copy), 다운로드, 삭제 기능 지원
    - 줄바꿈 처리 및 expander로 출력
    """
    with st.container(border=True):
        created_at = parse_ts_kst(item.get("created_at"))
        created_str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else "-"

        st.caption(f"생성 시간: {created_str}")

        st.write("**입력 내용**")
        input_txt = item.get("input_text", "(입력 없음)")
        # 마크다운 줄바꿈 처리
        st.info(input_txt.replace("\n", "  \n"))
        st.write("")

        with st.expander("생성된 광고 문구", expanded=True):
            output_text = item.get("output_text", "")

            # st-copy 버튼 (expander 안)
            copy_button(
                output_text,
                icon="st",  # 폰트 영향 회피
                tooltip="클립보드에 복사",
                copied_label="복사 완료!",
                key=f"copy_btn_{item['id']}",
            )
            st.write("")  # 헤더와 겹침 방지용 간격
            st.markdown(output_text)


        col1, col2 = st.columns(2)
        with col1:
            txt_bytes = (output_text if output_text.endswith("\n") else output_text + "\n").encode("utf-8")
            st.download_button(
                label="텍스트 다운로드(txt)",
                data=txt_bytes,
                file_name=f"광고문구_{item['id']}.txt",
                mime="text/plain",
                key=f"dl_txt_{item['id']}",
                width="stretch",
                type="primary" 
            )

            
        with col2:
            if st.button("삭제하기", key=f"delete_txt_{item['id']}", type="secondary", width="stretch"):
                try:
                    resp = delete_generation(item["id"])
                    st.success(resp.get("message", "삭제 완료"))
                    st.rerun()
                except Exception as e:
                    st.error(f"삭제 실패: {e}")


def page_text_history() -> None:
    """
    텍스트 보관함 페이지 렌더링
    - 로그인 체크 후 접근 가능
    - 텍스트 생성 이력 불러와 최신순 출력
    - 카드 형태로 정보/문구/버튼 표시
    - 복사, 다운로드, 삭제 기능 지원
    - 이력 없을 시 안내 메시지 출력
    """
    require_login()

    st.image("assets/text_history.png")
    try:
        items = load_text_generations()
    except Exception as e:
        st.error(f"서버 통신 중 오류가 발생했습니다: {e}")
        return

    if not items:
        st.info("아직 생성된 텍스트가 없습니다.")
        return

    for item in items:
        render_text_card(item)


if __name__ == "__main__":
    page_text_history()
