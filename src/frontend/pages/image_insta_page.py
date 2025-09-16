import time
from io import BytesIO
from typing import Optional, Tuple
import streamlit as st
from PIL import Image

PREVIEW_IMG_PATH = "assets/instagram_image.png"   # 상단 배너/미리보기
FALLBACK_IMG_PATH = "assets/image.png"            # 업로드 없을 때 예시 출력용


def _bytes_from_image(img: Image.Image) -> bytes:
    """PIL.Image → PNG 바이트"""
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# 인트로/헤더
def render_intro() -> None:
    """상단 배너에 인스타 이미지 생성 가이드를 표시합니다."""
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

# 입력 폼
def build_form() -> Tuple[bool, Optional[Image.Image], str, str, str]:
    """
    입력 폼을 렌더링하고 결과를 반환합니다.
    Returns:
        submitted: 제출 여부
        uploaded_img: 업로드 이미지 (없으면 None)
        title: 상품/상호명
        bg_choice: 배경 선택값
        prompt_text: 자유 프롬프트
    """
    with st.form("insta_image_form"):
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

        # 자유 프롬프트
        st.subheader("3. 직접 요청하기")
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
        st.write("⬇️ 모두 입력했다면, 아래의 :rainbow-background[이미지 생성하기] 버튼을 누르면 이미지가 생성됩니다. ⬇️")
        submitted = st.form_submit_button("이미지 생성하기", type="primary")

    return submitted, uploaded_img, title, bg_choice, prompt_text

# 생성 진행(로딩바) & 결과 출력
def simulate_progress(placeholder: st.delta_generator.DeltaGenerator) -> None:
    """진행 상황 표시하는 함수"""
    placeholder.progress(0, "매력적인 이미지를 생성 중이에요 ⌛")
    time.sleep(0.6)
    placeholder.progress(50, "매력적인 이미지를 생성 중이에요 ⌛")
    time.sleep(0.6)
    placeholder.progress(100, "완료!")


def render_result(generated_img: Image.Image, download_name: str) -> None:
    """생성 결과와 다운로드 버튼을 출력합니다."""
    st.success("이미지가 생성되었습니다! 🎉 ")
    st.image(generated_img, caption="생성 결과", use_container_width=True)
    st.download_button(
        "이미지 다운로드 (PNG)",
        data=_bytes_from_image(generated_img),
        file_name=f"{download_name or 'generated'}_image.png",
        mime="image/png",
        use_container_width=True,
    )

def main() -> None:
    """
    인스타그램 이미지 생성 페이지 렌더링 순서
    1) 인트로
    2) 폼 입력
    3) 제출 시 진행표시/결과 출력
       (업로드가 없으면 예시 이미지를 사용해 데모 진행)
    """
    render_intro()

    submitted, uploaded_img, title, bg_choice, prompt_text = build_form()

    # 미리보기 이미지 
    st.image(FALLBACK_IMG_PATH)

    if not submitted:
        return

    if not title:
        st.warning("상품 이름 또는 상호명을 입력해주세요.")
        return

    # 데모 진행: 업로드 이미지가 없으면 예시 이미지로 대체
    src_img = uploaded_img or Image.open(FALLBACK_IMG_PATH)

    placeholder = st.empty()
    simulate_progress(placeholder)

    placeholder.empty()
    with placeholder.container():
        # TODO: 실제 생성 API 연동 시 src_img, title, bg_choice, prompt_text를 전달
        render_result(src_img, download_name=title)


if __name__ == "__main__":
    main()