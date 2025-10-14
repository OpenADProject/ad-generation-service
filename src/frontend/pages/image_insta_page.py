import time, requests, base64, threading
from io import BytesIO
from typing import Optional, Tuple, List, Dict, Any
import streamlit as st
from PIL import Image

from utils.generations_api import (
    save_generation,
    list_generations,
    delete_generation, 
    list_user_models,  
) 
from utils.model_api import generate_insta_image
from pages.history_model_page import _render_card

PREVIEW_IMG_PATH = "assets/instagram_image.png"   # 상단 배너/미리보기     


# 공통 유틸
def _bytes_from_image(img: Image.Image) -> bytes:
    """
    PIL 이미지를 PNG 바이트로 변환
    """
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def _data_url_from_image(img: Image.Image) -> str:
    """
    PIL 이미지를 data URL(base64, PNG)로 변환
    """
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"

def _decode_base64_to_bytes(s: str) -> bytes:
    """
    base64 문자열 → 바이트
    - data: 접두사 포함 가능
    """
    # data URI면 접두사 제거
    if s.startswith("data:"):
        s = s.split(",", 1)[-1]
    return base64.b64decode(s, validate=False)

def _image_to_b64(img: Image.Image) -> str:
    """
    PIL 이미지를 base64 문자열로 변환 
    """
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

# 보관함 세션 유틸 
def _init_model_store():
    """
    세션 상태 초기화
    - my_models: [(name, PIL.Image)]
    - uploaded_names: 중복 업로드 방지용 set
    """
    if "my_models" not in st.session_state:
        st.session_state["my_models"] = []          # [(name, PIL.Image)]
    if "uploaded_names" not in st.session_state:
        st.session_state["uploaded_names"] = set()  # 중복 방지용

def _add_to_model_store(uploaded_file) -> tuple[str, Image.Image, bool]:
    """
    업로드 이미지를 세션 보관함에 추가
    Returns: (파일명, PIL.Image, 추가여부)
    """
    name = uploaded_file.name
    img = Image.open(uploaded_file).copy()  # 파일 핸들 분리
    if name in st.session_state["uploaded_names"]:
        return name, img, False
    st.session_state["my_models"].append((name, img))
    st.session_state["uploaded_names"].add(name)
    return name, img, True

def _get_all_models() -> List[Dict[str, Any]]:
    """
    서버에서 모델 목록 조회 (예외 시 빈 리스트 반환)
    """
    try:
        return list_user_models()  
    except Exception as e:
        st.error(f"모델 목록 조회 실패: {e}")
        return []

def _render_models_grid_4col(items: List[Dict[str, Any]]) -> None:
    """
    모델 미리보기 4열 그리드 렌더링
    - base64 이미지 표시, 실패 시 캡션 노출
    """
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
    """
    상단 배너 및 간단 안내 문구 렌더링
    """
    st.image(PREVIEW_IMG_PATH)
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
    st.markdown(
        """
        <p style='font-size:18px; text-align:center;'>
        상품/가게 이미지를 업로드한 뒤, 상품명, 배경, 대상, 사이즈, 모델, 추가 요청사항을 입력해주세요.
        <br><b>모두 입력이 끝나면</b> 맨 아래의 <span style="background-color:#c79dd7; color:white; padding:2px 6px; border-radius:30px;">이미지 생성하기</span> 버튼을 눌러주세요.
        </p>
        """,
        unsafe_allow_html=True
    )

    st.write(" ")
    st.write(" ")

def render_guide(
    label: str = "**이미지 생성 가이드**",
    page: str = "./pages/image_main_page.py",
):
    """
    가이드 이동 버튼 렌더링
    - 클릭 시 지정 페이지로 이동
    """
    """두 개의 버튼을 같은 행에 출력하고, 눌리면 해당 페이지로 이동합니다."""
    if st.button(label, type="primary"):
        st.switch_page(page)
    st.caption("💡 처음이라면 가이드를 확인하고 진행해 보세요!")

# 입력 폼
def build_form() -> Tuple[
    bool, Optional[Image.Image], str, str, str, str, str, Optional[int], str
]:
    """
    인스타 이미지 생성 입력 폼
    - 업로드 이미지, 배경/타깃/사이즈, 모델 선택, 자유 프롬프트 수집

    Returns (총 10개):
        submitted: bool
        uploaded_img: Optional[PIL.Image]
        title: str
        bg_choice: str
        gender_choice: str
        age_choice: str
        size_choice: str
        selected_model_alias: Optional[str]
        selected_model_img: Optional[PIL.Image]
        prompt_text: str
    """
    _init_model_store()  # 보관함 세션키 보장

    with st.form("insta_image_form"):
        # 메인 이미지 업로드
        st.subheader("이미지 등록하기")
        
        st.write("등록된 이미지를 기반으로 원하는 스타일로 생성해 드려요 ✨")
        uploaded_file = st.file_uploader(
            ":orange-background[Browse files] 버튼을 눌러 상품/가게 이미지를 등록해주세요.",
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
        submitted = st.form_submit_button("이미지 생성하기", type="primary", width="stretch")

    # 모델 업로드 파일과 별칭도 함께 반환
    return submitted, uploaded_img, title, bg_choice, gender_choice, age_choice, size_choice, selected_model_alias, selected_model_img, prompt_text

# 이미지 생성 완료 
def render_result(generated_img: Image.Image, download_name: str) -> None:
    """
    생성 결과 이미지 표시 및 다운로드 버튼 제공
    """
    st.success("이미지가 생성되었습니다! 🎉 ")
    st.image(generated_img, caption="생성 결과", use_container_width=True)
    st.download_button(
        "이미지 다운로드 (PNG)",
        data=_bytes_from_image(generated_img),
        file_name=f"{download_name or 'generated'}_image.png",
        mime="image/png",
        type="primary", 
        width="stretch"
    )

# 엔트리 포인트 
def main() -> None:
    """
    페이지 엔트리 포인트
    - 인트로/가이드 → 폼 입력 수집 → 검증 → 이미지 생성 호출
    - 결과 표시 및 생성 이력 저장
    """
    render_intro()
    render_guide()

    # 폼 입력 수집 
    submitted, uploaded_img, title, bg_choice, gender_choice, age_choice, size_choice, selected_model_alias, selected_model_img, prompt_text = build_form()

    if not submitted:
        return

    # 필수값 체크
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

    # API 요청용 base64 준비
    try:
        product_b64 = _image_to_b64(uploaded_img)
        model_b64 = _image_to_b64(selected_model_img) if selected_model_img is not None else None
    except Exception as e:
        st.error(f"이미지 인코딩 실패: {e}")
        return

    target_str = f"{gender_choice}/{age_choice}"

    # 진행 표시: spinner (API 끝날 때까지 표시)
    placeholder = st.empty()
    with placeholder, st.spinner("매력적인 이미지를 생성 중이에요 ⌛"):
        image_bytes, meta = generate_insta_image(
            product_image=product_b64,
            model_image=model_b64,  # None이면 키 빠짐
            prompt=(prompt_text or "").strip(),
            brand_name=title,
            background=bg_choice,
            target=target_str,
            size=size_choice,
            model_alias=(selected_model_alias or ""),
            file_saved=False,
            timeout=600,  
        )

    # 결과 처리
    if image_bytes is None:
        # 서버가 images에만 담아 주는 등 특이 응답일 수 있으니 meta도 보여주기
        raise ValueError(f"이미지 생성 응답에 base64가 없습니다. meta={meta}")

    generated_img = Image.open(BytesIO(image_bytes))
    placeholder.empty()
    with placeholder.container():
        render_result(generated_img, download_name=title)

        # 이력 저장
        input_text = (
            f"[채널: instagram]\n"
            f"상품/상호명: {title}\n"
            f"배경: {bg_choice}\n"
            f"마케팅 대상: {target_str}\n"
            f"이미지 크기: {size_choice}\n"
            f"모델: {selected_model_alias or '선택 안 함'}\n"
            f"요청사항: {prompt_text or 'None'}"
        )
        input_image_path = _data_url_from_image(uploaded_img) if uploaded_img is not None else None
        output_image_path = _data_url_from_image(generated_img)

        try:
            saved = save_generation(
                input_text=input_text,
                input_image_path=input_image_path,
                output_image_path=output_image_path,
            )
            st.info(f"생성 이력이 저장되었습니다 · ID: {saved.get('id','?')}")
        except requests.HTTPError as e:
            st.error(f"이력 저장 실패(HTTP): {e.response.status_code} {e.response.text}")
        except Exception as e:
            st.error(f"이력 저장 실패: {e}")

if __name__ == "__main__":
    main()