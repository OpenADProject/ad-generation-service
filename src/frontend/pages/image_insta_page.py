import time
from io import BytesIO
from typing import Optional, Tuple, List, Dict, Any
import streamlit as st
from PIL import Image
import requests
import base64

from utils.generations_api import (
    save_generation,
    list_generations,
    delete_generation, 
    list_user_models,  
) 
from pages.history_model_page import _render_card

PREVIEW_IMG_PATH = "assets/instagram_image.png"   # 상단 배너/미리보기     

# 공통 유틸
def _bytes_from_image(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def _data_url_from_image(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"

def _decode_base64_to_bytes(s: str) -> bytes:
    # data URI면 접두사 제거
    if s.startswith("data:"):
        s = s.split(",", 1)[-1]
    return base64.b64decode(s, validate=False)

# 보관함 세션 유틸 
def _init_model_store():
    if "my_models" not in st.session_state:
        st.session_state["my_models"] = []          # [(name, PIL.Image)]
    if "uploaded_names" not in st.session_state:
        st.session_state["uploaded_names"] = set()  # 중복 방지용

def _add_to_model_store(uploaded_file) -> tuple[str, Image.Image, bool]:
    """업로드 파일을 보관함 세션에 저장. (name, img, added) 반환"""
    name = uploaded_file.name
    img = Image.open(uploaded_file).copy()  # 파일 핸들 분리
    if name in st.session_state["uploaded_names"]:
        return name, img, False
    st.session_state["my_models"].append((name, img))
    st.session_state["uploaded_names"].add(name)
    return name, img, True


def _get_all_models() -> List[Dict[str, Any]]:
    try:
        return list_user_models()  
    except Exception as e:
        st.error(f"모델 목록 조회 실패: {e}")
        return []

def _render_models_grid_4col(items: List[Dict[str, Any]]) -> None:
    if not items:
        st.info("등록된 모델이 없습니다.")
        return
    cols = st.columns(4)
    for i, it in enumerate(items):
        with cols[i % 4], st.container(border=True):
            alias = it.get("alias", "?")
            st.markdown(alias)

            raw = it.get("file_path", "") or ""
            try:
                img_bytes = _decode_base64_to_bytes(raw)
                st.image(img_bytes, use_container_width=True)
            except Exception as e:
                st.caption(f"이미지 표시 실패: {e}")

# 상단 인트로 영역
def render_intro() -> None:
    st.image(PREVIEW_IMG_PATH)
    st.write(" ")
    st.markdown("인스타그램 홍보 이미지를 손쉽게 만들어보세요! ✨")
    st.markdown("상품/가게 이미지를 업로드한 뒤, 상품명, 배경, 타겟층, 사이즈, 모델, 추가 요청사항을 입력해주세요.")
    st.markdown("**모두 입력이 끝나면** 맨 아래의 :rainbow-background[이미지 생성하기] 버튼을 눌러주세요.")
    st.write(" ")
    st.write(" ")

# 입력 폼
def build_form() -> Tuple[
    bool, Optional[Image.Image], str, str, str, str, str, Optional[int], str
]:
    """
    Returns:
        submitted, uploaded_img, title, bg_choice, gender_choice, age_choice, size_choice, selected_model_alias, selected_model_img, prompt_text
    """
    _init_model_store()  # 보관함 세션키 보장

    with st.form("insta_image_form"):
        # 메인 이미지 업로드
        st.subheader("이미지 등록하기")
        
        st.write("등록된 이미지를 기반으로 원하는 스타일로 생성해 드려요 ✨")
        uploaded_file = st.file_uploader(
            "⬇️ :orange-background[Browse files] 버튼을 눌러 상품/가게 이미지를 등록해주세요. (필수)",
            type=["png", "jpg", "jpeg"],
            key="main_image_uploader",   # ← 고유 key
        )

        uploaded_img: Optional[Image.Image] = None
        if uploaded_file is not None:
            uploaded_img = Image.open(uploaded_file)
            st.image(uploaded_img, caption="업로드된 사진", use_container_width=True)

        st.divider()

        # 요청 사항
        st.subheader("요청 사항 입력하기")
        st.markdown("")

        st.markdown("① 상품 이름 또는 상호명을 입력해주세요.")
        title = st.text_input("", label_visibility="collapsed")
        st.markdown("")
        st.markdown("")

        st.markdown("② 원하시는 이미지 배경을 선택해주세요.")
        bg_choice = st.selectbox(
            label="",
            label_visibility="collapsed",
            index=None,
            options=[
                "화이트(기본)", "매장 내부", "야외 풍경",
                "카페 분위기", "고급스러운 배경",
                "밝고 화사한 배경", "심플 단색 배경",
            ],
            key="bg_choice",
        )
        st.markdown("")
        st.markdown("")

        st.markdown("③ 마케팅 대상을 선택해주세요.")
        col1, col2 = st.columns(2)

        with col1:
            gender_choice = st.selectbox(
                "성별",
                index=None,
                options=["여성", "남성", "성별 무관"],
                key="gender_choice",
            )

        with col2:
            age_choice = st.selectbox(
                "연령",
                index=None,
                options=["10대", "20대", "30대", "40대", "50대 이상", "나이 무관"],
                key="age_choice",
            )
        st.markdown("")
        st.markdown("")

        st.markdown("④ 원하시는 이미지 사이즈를 선택해주세요.")
        size_choice = st.selectbox(
            label="",
            label_visibility="collapsed",
            index=None,
            options=[
                "1080x1080", "1080x1350"
            ],
            key="size_choice",
        )

        st.divider()

        # 모델 선택/등록
        st.subheader("모델 선택하기")
        st.caption("※ 선택사항입니다. 모델을 선택하지 않아도 이미지를 생성할 수 있어요.")
        all_items = _get_all_models()

        # selectbox
        options = [None] + all_items
        selected_obj = st.selectbox(
            "원하시는 이미지 모델을 선택해주세요.",
            options=options,
            format_func=lambda o: "(선택 안 함）" if o is None else o.get("alias", "이름없음"),
            key="model_selectbox",
        )

        selected_model_alias = None
        selected_model_img = None

        if selected_obj:
            selected_model_alias = selected_obj.get("alias", None)
            try:
                b = _decode_base64_to_bytes(selected_obj.get("file_path", "") or "")
                selected_model_img = Image.open(BytesIO(b)).copy()
                st.success(f"선택된 모델: {selected_model_alias}")
            except Exception:
                st.warning("선택된 모델 이미지를 불러오지 못했습니다.")


        # 카드 그리드
        _render_models_grid_4col(all_items)

        st.divider()


        # 자유 프롬프트
        st.subheader("직접 요청하기")
        prompt_text = st.text_area(
            "예시)\n"
                "테이블 위에 커피가 있고, 창가 햇살이 들어오는 분위기와 따뜻하고 감성적인 느낌으로 만들어줘.",
            placeholder="요청사항을 작성해주세요.",
            height=150,
        )

        st.write(" ")
        submitted = st.form_submit_button("이미지 생성하기", type="primary")

    # 모델 업로드 파일과 별칭도 함께 반환
    return submitted, uploaded_img, title, bg_choice, gender_choice, age_choice, size_choice, selected_model_alias, selected_model_img, prompt_text

# 진행/결과 표시 
def simulate_progress(placeholder: st.delta_generator.DeltaGenerator) -> None:
    placeholder.progress(0, "매력적인 이미지를 생성 중이에요 ⌛")
    time.sleep(0.6)
    placeholder.progress(50, "매력적인 이미지를 생성 중이에요 ⌛")
    time.sleep(0.6)
    placeholder.progress(100, "완료!")

def render_result(generated_img: Image.Image, download_name: str) -> None:
    st.success("이미지가 생성되었습니다! 🎉 ")
    st.image(generated_img, caption="생성 결과", use_container_width=True)
    st.download_button(
        "이미지 다운로드 (PNG)",
        data=_bytes_from_image(generated_img),
        file_name=f"{download_name or 'generated'}_image.png",
        mime="image/png",
        use_container_width=True,
    )

# 엔트리 포인트 
def main() -> None:
    render_intro()

    # 폼 입력 수집 
    submitted, uploaded_img, title, bg_choice, gender_choice, age_choice, size_choice, selected_model_alias, selected_model_img, prompt_text = build_form()

    if not submitted:
        return

    # 요청 사항 미입력 시 멘트
    if not uploaded_img:
        st.warning("상품이나 가게 이미지를 등록해주세요.")
        return

    if not title:
        st.warning("상품 이름 또는 상호명을 입력해주세요.")
        return

    if not bg_choice:
        st.warning("이미지 배경을 선택해주세요.")
        return

    if not gender_choice:
        st.warning("마케팅 대상(성별)을 선택해주세요.")
        return

    if not age_choice:
        st.warning("마케팅 대상(연령)을 선택해주세요.")
        return

    if not size_choice:
        st.warning("이미지 사이즈를 선택해주세요.")
        return

    # 생성용 소스 이미지: 업로드 없으면 FALLBACK
    src_img = uploaded_img 

    placeholder = st.empty()
    simulate_progress(placeholder)

    placeholder.empty()
    with placeholder.container():
        render_result(src_img, download_name=title)

        input_text = (
            f"[채널: instagram]\n"
            f"상품/상호명: {title}\n"
            f"배경: {bg_choice}\n"
            f"마케팅 대상: {gender_choice}/{age_choice}\n"
            f"이미지 크기: {size_choice}\n"
            f"모델: {selected_model_alias}\n"
            f"요청사항: {prompt_text or 'None'}"
        )
        try:
            # 입력 이미지가 있다면 input_image_path도 함께 저장 (base64)
            input_image_path = _data_url_from_image(uploaded_img) if uploaded_img is not None else None
            data_url = _data_url_from_image(src_img)
            saved = save_generation(
                input_text=input_text,
                input_image_path=input_image_path,
                output_image_path=data_url
            )
            st.info(f"생성 이력이 저장되었습니다 · ID: {saved.get('id','?')}")
        except requests.HTTPError as e:
            st.error(f"이력 저장 실패(HTTP): {e.response.status_code} {e.response.text}")
        except Exception as e:
            st.error(f"이력 저장 실패: {e}")


if __name__ == "__main__":
    main()