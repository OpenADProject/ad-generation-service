import time
from typing import Optional, Tuple

import streamlit as st
from PIL import Image

BANNER_IMG_PATH   = "assets/instagram_text.png"
PREVIEW_TEXT_PATH = "assets/text.png"   # 하단 미리보기 이미지(선택)

def ensure_session() -> None:
    """세션 키 초기화하는 함수"""
    if "insta_text_result" not in st.session_state:
        st.session_state.insta_text_result = None

def render_intro() -> None:
    """상단에 텍스트 생성 가이드를 표시하는 함수"""
    st.image(BANNER_IMG_PATH)
    st.write(" ")
    st.markdown("인스타그램 홍보 부담을 덜어드릴게요. 인스타그램에 업로드할 센스있는 광고 문구를 생성해 드려요!✨")
    st.write(" ")
    st.markdown("**1. 이미지 등록하기**: 상품/가게 이미지나 참고할 이미지가 있다면 등록해주세요. (생략 가능합니다.)")
    st.markdown("**2. 요청 사항 입력하기**: 상품명을 입력하고 문구 톤을 선택하여 상황에 맞는 광고 문구를 생성해 봐요.")
    st.markdown("**3. 직접 요청하기**: 제품 특징, 말투 등의 요구사항을 직접 작성하면 텍스트 품질이 좋아져요.")
    st.markdown("**4. 모두 입력이 완료되면, 맨 아래의 :rainbow-background[텍스트 생성하기] 버튼을 누르면 텍스트가 생성됩니다.**")
    st.markdown("이제, 아래 단계 별로 하나씩 입력하여 원하는 텍스트를 생성해 봐요. 😆")
    st.divider()

# 입력 폼
def build_form() -> Tuple[bool, Optional[Image.Image], str, str, str]:
    """
    입력 폼을 렌더링하고 결과를 반환합니다.
    Returns:
        submitted: 제출 여부
        uploaded_img: 업로드 이미지 (없으면 None)
        title: 상품/상호명
        tone: 말투 톤 선택값
        prompt_text: 자유 프롬프트
    """
    with st.form("insta_text_form"):
        # 이미지 업로드
        st.subheader("1. 이미지 등록하기")
        st.write("상품/가게 이미지나 참고할 이미지가 있다면 등록해주세요. (이미지가 없다면 생략 가능합니다.)")
        st.write("⬇️ 아래의 :orange-background[Browse files] 버튼을 누르면 이미지 등록이 가능합니다. ⬇️")
        uploaded_file = st.file_uploader("이미지 업로드", type=["png", "jpg", "jpeg"])

        uploaded_img: Optional[Image.Image] = None
        if uploaded_file is not None:
            uploaded_img = Image.open(uploaded_file)
            st.image(uploaded_img, caption="업로드된 사진", use_container_width=True)

        st.divider()

        # 요청 사항 입력
        st.subheader("2. 요청 사항 입력하기")
        st.write("① 상품 이름 또는 상호명을 입력해주세요.")
        title = st.text_input("예시) 순살후라이드, 촉촉쿠키, 해피미용실, 슈퍼헬스장")
        st.write(" ")

        st.write("② 원하시는 말투 톤을 선택해주세요.")
        tone = st.radio(
            "광고 문구 톤을 설정해요.",
            options=["친절한 서비스직 말투", "친구같은 반말", "격식있는 정중한 말투"],
            key="insta_text_tone",
        )

        st.divider()

        # 자유 프롬프트
        st.subheader("3. 직접 요청하기")
        st.write("원하는 문구 톤, 제품 특징 등 텍스트 생성에 필요한 요구사항을 작성해봐요. (생략 가능합니다.)")
        prompt_text = st.text_area(
            "요구사항 입력",
            placeholder=(
                "예시)\n"
                "신선한 원두로 내린 부드러운 라떼와 직접 구운 쿠키가 어울리는 카페야. "
                "친구같은 반말 톤으로 상큼하게 표현해줘."
            ),
            height=150,
        )

        st.write(" ")
        st.write("⬇️ 모두 입력했다면, 아래의 :rainbow-background[텍스트 생성하기] 버튼을 누르면 텍스트가 생성됩니다. ⬇️")
        submitted = st.form_submit_button("텍스트 생성하기", type="primary")

    return submitted, uploaded_img, title, tone, prompt_text

# 생성 로딩/모델 호출/결과
def simulate_progress(placeholder: st.delta_generator.DeltaGenerator) -> None:
    """진행 상황을 표시하는 함수"""
    placeholder.progress(0,  "센스있는 텍스트를 생성 중이에요 ⌛")
    time.sleep(0.6)
    placeholder.progress(45, "센스있는 텍스트를 생성 중이에요 ⌛")
    time.sleep(0.6)
    placeholder.progress(80, "마무리 중이에요... ✨")
    time.sleep(0.6)
    placeholder.progress(100, "완료!")


def generate_text(title: str, tone: str, prompt_text: str) -> str:
    """
    실제 생성 모델 호출을 감싸는 함수
    TODO: 백엔드 연동 시 여기서 POST /text-generations 호출.
    """
    # resp = requests.post(API_URL, json={...}).json()
    # return resp["text"]
    return f"[{tone}] {title}를 소개합니다! 감성과 센스를 담아 딱 맞게 표현했어요 ✨"  # 데모 문자열


def render_result(text: str) -> None:
    """생성 결과 표시와 다운로드 버튼"""
    st.success("텍스트가 생성되었습니다! 🎉")
    st.code(text)  # 우측 상단 복사 아이콘 자동 제공
    st.download_button(
        "텍스트 다운로드",
        data=text.encode("utf-8"),
        file_name="insta_caption.txt",
        mime="text/plain",
    )

def main() -> None:
    """
    인스타그램 텍스트 생성 페이지 렌더링 순서
    1) 세션 초기화 → 인트로
    2) 입력 폼
    3) 제출 시 진행바 + 생성 + 결과 출력
    """
    ensure_session()
    render_intro()

    submitted, uploaded_img, title, tone, prompt_text = build_form()

    st.divider()
    st.image(PREVIEW_TEXT_PATH)  # 선택: 하단 예시 이미지

    if not submitted:
        return

    if not title:
        st.warning("상품 이름 또는 상호명을 입력해주세요.")
        return

    placeholder = st.empty()
    simulate_progress(placeholder)

    # 생성 호출
    generated_text = generate_text(title=title, tone=tone, prompt_text=prompt_text)

    # 진행바 지우고 결과 렌더
    placeholder.empty()
    with placeholder.container():
        render_result(generated_text)
        st.session_state.insta_text_result = generated_text


if __name__ == "__main__":
    main()
