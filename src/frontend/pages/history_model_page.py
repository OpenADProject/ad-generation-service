from __future__ import annotations

import base64
import streamlit as st
from typing import List, Dict, Any

from utils.generations_api import (
    upload_user_model,
    list_user_models,
    rename_user_model,
    delete_user_model,
)

API_BASE = st.secrets["API_BASE"].rstrip("/")

# 프리셋 ID
PRESET_ANIMAL_IDS = {1, 2}
PRESET_PEOPLE_IDS = {3, 4, 5, 6}
PRESET_IDS = PRESET_ANIMAL_IDS | PRESET_PEOPLE_IDS


# 로그인 요구
def require_login() -> None:
    """로그인 토큰 없으면 작업 중단"""
    token = st.session_state.get("access_token")
    if not token:
        st.warning("로그인이 필요합니다. 먼저 로그인 해주세요.")
        st.stop()

# base64 디코딩
def _decode_base64_to_bytes(s: str) -> bytes:
    if s.startswith("data:"):
        s = s.split(",", 1)[-1]
    return base64.b64decode(s, validate=False)


# 아이템 분류
def load_presets(items: List[Dict[str, Any]]):
    animals = [it for it in items if it.get("id") in PRESET_ANIMAL_IDS]
    people = [it for it in items if it.get("id") in PRESET_PEOPLE_IDS]
    return animals, people

def split_items(items: List[Dict[str, Any]]):
    animals, people = load_presets(items)
    mine = [it for it in items if it.get("id") not in PRESET_IDS]
    return animals, people, mine


# 렌더링
def _render_card(item: Dict[str, Any]) -> None:
    alias = item.get("alias", "?")
    st.subheader(alias)

    raw = (item.get("file_path") or "").strip()
    try:
        # URL이면 그대로 표시, 아니면 base64로 가정
        if raw.startswith("http://") or raw.startswith("https://"):
            st.image(raw, use_container_width=True)
        else:
            img_bytes = _decode_base64_to_bytes(raw)
            st.image(img_bytes, use_container_width=True)
    except Exception as e:
        st.caption(f"이미지 표시 실패: {e}")


def render_tab(title: str, items: List[Dict[str, Any]]) -> None:
    if not items:
        st.info(f"{title}이(가) 없습니다.")
        return

    cols = st.columns(2)
    for i, it in enumerate(items):
        with cols[i % 2], st.container(border=True):
            _render_card(it)

            # 내 모델에서만 수정/삭제 노출 (프리셋 제외)
            if it.get("id") not in PRESET_IDS:
                mid = it.get("id")
                alias = it.get("alias", "")

                with st.expander("모델명 변경"):
                    new_alias = st.text_input("새 별칭", value=alias, key=f"rename_{mid}")
                    if st.button("변경", key=f"btn_rename_{mid}", type="primary"):
                        try:
                            rename_user_model(mid, new_alias.strip())
                            st.success("변경 완료")
                            st.rerun()
                        except Exception as e:
                            st.error(f"수정 실패: {e}")

                if st.button("삭제", key=f"del_{mid}", type="primary"):
                    try:
                        delete_user_model(mid)
                        st.success("삭제 완료")
                        st.rerun()
                    except Exception as e:
                        st.error(f"삭제 실패: {e}")


def render_uploader() -> None:
    with st.form("model_upload_form", clear_on_submit=True):
        f = st.file_uploader("이미지 선택", type=["png", "jpg", "jpeg"])
        alias = st.text_input("모델 이름(별칭)", placeholder="예) 여자 어린이, 곰돌이 인형, 화장품 모델")
        submitted = st.form_submit_button("등록", type="primary")
        if submitted:
            if not f:
                st.warning("이미지를 업로드해 주세요.")
                return
            if not alias.strip():
                st.warning("모델 이름을 입력해 주세요.")
                return
            try:
                upload_user_model(alias=alias.strip(), file_name=f.name, file_bytes=f.getvalue())
                st.success("등록 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"업로드 실패: {e}")


# 페이지 엔트리
def render_history_model_page() -> None:
    require_login()  # 로그인별로 목록/업로드 가능

    st.header("모델 목록", divider="blue")

    try:
        items = list_user_models()
    except Exception as e:
        st.error(f"목록 조회 실패: {e}")
        items = []

    # 업로드(내 모델에만 영향) — 로그인 사용자별로 동작
    render_uploader()

    animals, people, mine = split_items(items)
    tab1, tab2, tab3 = st.tabs(["동물", "사람", "내 모델"])
    with tab1:
        render_tab("동물 프리셋", animals)
    with tab2:
        render_tab("사람 프리셋", people)
    with tab3:
        render_tab("내 모델", mine)


if __name__ == "__main__":
    render_history_model_page()
