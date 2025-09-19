import time
from io import BytesIO
from typing import Optional, Tuple
import streamlit as st
from PIL import Image
import requests
import base64
from utils.generations_api import save_generation, list_generations, delete_generation

PREVIEW_IMG_PATH = "assets/instagram_image.png"   # 상단 배너/미리보기
FALLBACK_IMG_PATH = "assets/image.png"            # 업로드 없을 때 예시 출력용


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


def _bytes_from_image(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def render_intro() -> None:
    st.image(PREVIEW_IMG_PATH)
    st.write(" ")
    st.markdown("인스타그램 홍보 부담을 덜어드릴게요. 인스타그램에 업로드할 멋진 이미지를 생성해 드려요!✨")
    st.write(" ")
    st.markdown("**1. 이미지 등록하기**: 상품/가게 이미지나 참고할 이미지가 있다면 등록해주세요. (생략 가능합니다.)")
    st.markdown("**2. 요청 사항 입력하기**: 상품명, 이미지 배경을 입력하여 원하는 이미지를 생성해 봐요.")
    st.markdown("**3. 직접 요청하기**: 주변 물체, 장소, 이미지 분위기 등 요구사항을 직접 작성하면 이미지 품질이 좋아져요.")
    st.markdown("**4. 모두 입력이 완료되면, 맨 아래의 :rainbow-background[이미지 생성하기] 버튼을 누르면 이미지가 생성됩니다.**")
    st.markdown("이제, 아래 단계 별로 하나씩 입력하여 원하는 이미지를 생성해 봐요. 😆")
    st.divider()


def build_form() -> Tuple[bool, Optional[Image.Image], str, str, str, Optional[object]]:
    """
    Returns:
        submitted, uploaded_img, title, bg_choice, prompt_text, model_upload_file
    """
    _init_model_store()  # 보관함 세션키 보장

    with st.form("insta_image_form"):
        # 메인 이미지 업로드
        st.subheader("1. 이미지 등록하기")
        st.write("상품/가게 이미지나 참고할 이미지가 있다면 등록해주세요. (이미지가 없다면 생략 가능합니다.)")
        st.write("⬇️ 아래의 :orange-background[Browse files] 버튼을 누르면 이미지 등록이 가능합니다. ⬇️")
        uploaded_file = st.file_uploader(
            "이미지 업로드",
            type=["png", "jpg", "jpeg"],
            key="main_image_uploader",     # ← 고유 key 부여
        )

        uploaded_img: Optional[Image.Image] = None
        if uploaded_file is not None:
            uploaded_img = Image.open(uploaded_file)
            st.image(uploaded_img, caption="업로드된 사진", use_container_width=True)

        st.divider()

        # 요청 사항
        st.subheader("2. 요청 사항 입력하기")
        st.write("① 상품 이름 또는 상호명을 입력해주세요.")
        title = st.text_input("예시) 순살후라이드, 촉촉쿠키, 해피미용실, 슈퍼헬스장")
        st.write(" ")

        st.write("② 원하시는 이미지 배경을 선택해주세요.")
        bg_choice = st.radio(
            "생성 이미지의 배경을 설정합니다.",
            options=[
                "화이트(기본)", "매장 내부", "야외 풍경",
                "카페 분위기", "고급스러운 배경",
                "밝고 화사한 배경", "심플 단색 배경",
            ],
            key="bg_choice",
        )

        st.divider()

        # 모델 선택/등록
        st.subheader("3. 모델 선택하기")
        st.write("동물, 사람 모델을 선택하거나 직접 모델 이미지를 등록 가능해요.")
        st.write("⬇️ 아래의 :orange-background[Browse files] 버튼을 누르면 모델 이미지 등록이 가능합니다. ⬇️")
        model_upload = st.file_uploader(
            "모델 이미지 업로드",
            type=["png", "jpg", "jpeg"],
            key="model_image_uploader",    # ← 고유 key 부여 (중복 에러 해결)
        )

        st.divider()

        # 자유 프롬프트
        st.subheader("4. 직접 요청하기")
        st.write("주변 물체, 장소, 이미지 분위기 등 이미지 생성에 필요한 요구사항을 작성해봐요. (생략 가능합니다.)")
        prompt_text = st.text_area(
            "요구사항 입력",
            placeholder=(
                "예시)\n"
                "카페 테이블 위에 놓인 아이스 아메리카노가 있고, 창가 햇살이 들어오는 분위기와 "
                "따뜻하고 감성적인 느낌으로 만들어줘."
            ),
            height=150,
        )

        st.write(" ")
        submitted = st.form_submit_button("이미지 생성하기", type="primary")

    # 모델 업로드 파일을 함께 반환
    return submitted, uploaded_img, title, bg_choice, prompt_text, model_upload


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

def _data_url_from_image(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def main() -> None:
    render_intro()

    # model_upload도 함께 받음
    submitted, uploaded_img, title, bg_choice, prompt_text, model_upload = build_form()

    # 참고 이미지
    st.image(FALLBACK_IMG_PATH)

    if not submitted:
        return

    if not title:
        st.warning("상품 이름 또는 상호명을 입력해주세요.")
        return

    # 모델 업로드가 있다면 보관함에 저장
    if model_upload is not None:
        _init_model_store()
        name, img_copy, added = _add_to_model_store(model_upload)
        if added:
            st.success(f"모델 보관함에 '{name}'이(가) 저장되었어요.  \n(내 모델 탭에서 확인 가능합니다.)")
        else:
            st.info(f"'{name}'은(는) 이미 보관함에 있어요.")

    # 생성용 소스 이미지: 업로드 없으면 FALLBACK
    src_img = uploaded_img or Image.open(FALLBACK_IMG_PATH)

    placeholder = st.empty()
    simulate_progress(placeholder)

    placeholder.empty()
    with placeholder.container():
        render_result(src_img, download_name=title)

        input_text = (
            f"[채널: instagram]\n"
            f"상품/상호명: {title}\n"
            f"배경: {bg_choice}\n"
            f"요청사항: {prompt_text or '(없음)'}"
        )
        try:
            data_url = _data_url_from_image(src_img)
            saved = save_generation(input_text=input_text, output_image_path=data_url)
            st.info(f"생성 이력이 저장되었습니다 · ID: {saved.get('id','?')}")
        except requests.HTTPError as e:
            st.error(f"이력 저장 실패(HTTP): {e.response.status_code} {e.response.text}")
        except Exception as e:
            st.error(f"이력 저장 실패: {e}")


if __name__ == "__main__":
    main()
