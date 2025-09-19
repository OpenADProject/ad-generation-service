from __future__ import annotations
import streamlit as st
from PIL import Image
from typing import List, Tuple

# 설정
BACKEND_URL = st.secrets["API_BASE"]

# 상태 초기화
def init_state() -> None:
    if "my_models" not in st.session_state:
        st.session_state["my_models"]: List[Tuple[str, Image.Image]] = []  # [(name, Image)]
    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = 0   # file_uploader 초기화용 버전 키
    if "uploaded_names" not in st.session_state:
        st.session_state["uploaded_names"] = set()  # 중복 방지용
        
    # 업로드 대기(미리보기 + 이름 입력 후 등록)용
    if "pending_img" not in st.session_state:
        st.session_state["pending_img"] = None
    if "pending_name" not in st.session_state:
        st.session_state["pending_name"] = ""

# 업로드
def render_uploader() -> None:
    st.subheader("모델 사진 등록하기")

    # 폼 시작
    with st.form("model_upload_form", clear_on_submit=True):
        uploaded_file = st.file_uploader(
            "⬇️ 아래의 :orange-background[Browse files] 버튼을 눌러 모델 사진을 선택하세요. ⬇️",
            type=["png", "jpg", "jpeg"],
        )
        model_name = st.text_input(
            "모델 이름을 입력하세요",
            placeholder="예) 20대 여성, 우리 가게 모델, 스니커즈 착샷 등",
        )

        submitted = st.form_submit_button("등록")

        if submitted:
            if uploaded_file is None:
                st.warning("이미지를 업로드해 주세요.")
            elif not model_name.strip():
                st.warning("모델 이름을 입력해 주세요.")
            elif model_name in st.session_state["uploaded_names"]:
                st.warning("이미 존재하는 모델 이름입니다. 다른 이름을 사용해 주세요.")
            else:
                img = Image.open(uploaded_file).copy()
                st.session_state["my_models"].append((model_name.strip(), img))
                st.session_state["uploaded_names"].add(model_name.strip())
                st.success("모델이 등록되었습니다. :blue-background[내 모델] 탭에서 확인하세요.")

# 기본 모델 데이터
def get_animal_presets() -> List[Tuple[str, str]]:
    return [("고양이", "assets/cat.png"), ("강아지", "assets/dog.png")]

def get_people_presets() -> List[Tuple[str, str]]:
    return [
        ("20대 여성", "assets/female_20.png"),
        ("20대 남성", "assets/male_20.png"),
        ("50대 여성", "assets/female_50.png"),
        ("50대 남성", "assets/male_50.png"),
    ]

# 탭 설정
def render_tab_animals() -> None:
    animals = get_animal_presets()
    cols = st.columns(2)
    for idx, (title, path) in enumerate(animals):
        with cols[idx % 2], st.container(border=True):
            st.header(title)
            st.image(path, use_container_width=True)

def render_tab_people() -> None:
    people = get_people_presets()
    cols = st.columns(2)
    for idx, (title, path) in enumerate(people):
        with cols[idx % 2], st.container(border=True):
            st.header(title)
            st.image(path, use_container_width=True)

def render_tab_mine() -> None:
    st.subheader("내가 등록한 모델")
    if not st.session_state["my_models"]:
        st.info("모델 사진을 등록해주세요.")
        return

    cols = st.columns(2)
    for idx, (name, img) in enumerate(st.session_state["my_models"]):
        with cols[idx % 2], st.container(border=True):
            st.header(name)  # 파일명 대신 사용자가 지정한 이름만 노출
            st.image(img, use_container_width=True)

            # 모델명 변경
            with st.expander("모델명 변경"):
                new_name = st.text_input(
                    "변경할 모델명을 입력하세요.",
                    value=name,
                    key=f"rename_{idx}"
                )
                if st.button("변경", key=f"rename_btn_{idx}", type="primary"):
                    new_name = new_name.strip()
                    if not new_name:
                        st.warning("모델명을 입력해 주세요.")
                    elif new_name != name and new_name in st.session_state["uploaded_names"]:
                        st.warning("이미 존재하는 모델명이 있습니다.")
                    else:
                        # 집합 업데이트
                        st.session_state["uploaded_names"].discard(name)
                        st.session_state["uploaded_names"].add(new_name)
                        st.session_state["my_models"][idx] = (new_name, img)
                        st.success("모델명이 변경되었습니다.")
                        st.rerun()

            if st.button("삭제", key=f"del_{idx}", type="primary"):
                st.session_state["my_models"].pop(idx)
                st.session_state["uploaded_names"].discard(name)
                st.rerun()

# 페이지(엔트리) 함수
def render_history_model_page() -> None:
    st.header("모델 목록", divider="blue")
    init_state()
    render_uploader()

    tab1, tab2, tab3 = st.tabs(["동물", "사람", "내 모델"])
    with tab1:
        render_tab_animals()
    with tab2:
        render_tab_people()
    with tab3:
        render_tab_mine()

# 단독 실행 시
if __name__ == "__main__":
    render_history_model_page()
