import time
from typing import Optional, Tuple
import streamlit as st
from utils.generations_api import save_generation, list_generations, delete_generation
from utils.model_api import generate_insta_text

BANNER_IMG_PATH   = "assets/instagram_text.png"

def ensure_session() -> None:
    """세션 키 초기화하는 함수"""
    if "insta_text_result" not in st.session_state:
        st.session_state.insta_text_result = None

def render_intro() -> None:
    """상단에 텍스트 생성 가이드를 표시하는 함수"""
    st.image(BANNER_IMG_PATH)
    st.write(" ")
    st.markdown("인스타그램 홍보 문구, 이제 간단하게! ✨")

    st.markdown(
        "상품 이름/상호명, 말투 톤, 마케팅 타겟층, 영어 번역 옵션을 순서대로 입력해 주세요."
    )
    st.markdown(
        "**모두 입력이 끝나면** 맨 아래의 :rainbow-background[텍스트 생성하기] 버튼을 눌러주세요."
    )
    st.write(" ")
    st.write(" ")

# 입력 폼
def build_form() -> Tuple[bool, str, str, str, bool]:
    """
    Returns:
        submitted: 제출 여부
        title: 상품/상호명
        tone: 말투 톤
        target: 타겟층
        english_translation: 영어 번역 포함 여부 (bool)
    """
    with st.form("insta_text_form"):
        st.subheader("요청 사항 입력하기")
        title = st.text_input("① 상품 이름 또는 상호명을 입력해주세요.")
        st.write(" ")

        tone = st.selectbox(
            "② 원하시는 말투 톤을 선택해주세요.",
            options=["친근한", "고급스러운"],
            index=None,
            key="insta_text_tone",
        )
        st.write(" ")

        target = st.text_input("③ 마케팅 대상을 입력해주세요.")
        st.write(" ")

        english_translation_label = st.selectbox(
            "④ 영어 번역을 함께 넣을까요?",
            options=["포함", "포함 안 함"],
            index=None,
            key="english_translation",
        )
        # 사용자가 아직 선택하지 않았다면 None
        if english_translation_label is None:
            english_translation = None
        else:
            english_translation = (english_translation_label == "포함")

        st.divider()
        st.write("⬇️ 모두 입력했다면, 아래의 :rainbow-background[텍스트 생성하기] 버튼을 누르면 텍스트가 생성됩니다. ⬇️")
        submitted = st.form_submit_button("텍스트 생성하기", type="primary")

    return submitted, title, tone, target, english_translation

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

    submitted, title, tone, target, english_translation = build_form()

    st.divider()

    if not submitted:
        return

    if not title:
        st.warning("상품 이름 또는 상호명을 입력해주세요.")
        return

    if not tone:
        st.warning("원하시는 말투 톤을 선택해주세요.")
        return

    if english_translation is None:
        st.warning("영어 번역 포함 여부를 선택해주세요.")
        return
               

    placeholder = st.empty()
    simulate_progress(placeholder)

    # 생성 호출
    generated_text = generate_insta_text(
        product=title,
        tone=tone,
        target_audience=target,
        translate_en=english_translation,
    )

    # 진행바 지우고 결과 렌더
    placeholder.empty()
    with placeholder.container():
        render_result(generated_text)
        st.session_state.insta_text_result = generated_text

        input_text = (
            f"[채널: instagram]\n"
            f"상품/상호명: {title}\n"
            f"톤: {tone}\n"
            f"타겟층: {target}\n"
            f"영어 번역 포함: {'예' if english_translation else '아니오'}\n"
        )
    
        try:
            saved = save_generation(
                input_text=input_text,
                input_image_path=None,
                output_text=generated_text,
            )
            st.info(f"생성 이력이 저장되었어요 · ID: {saved.get('id','?')}")
        except Exception as e:
            st.warning(f"이력 저장은 건너뛰었습니다: {e}")

if __name__ == "__main__":
    main()
