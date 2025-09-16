import streamlit as st
import time
from PIL import Image


# # TODO: 백엔드 연결 시 아래 함수에 실제 API 호출 붙이기
# def save_text_generation(input_text: str, output_text: str) -> dict:
#     """백엔드가 정해지면 여기서 POST /text-generations/ 호출"""
#     raise NotImplementedError

# def list_text_generations() -> list[dict]:
#     """백엔드가 정해지면 여기서 GET /text-generations/ 호출"""
#     raise NotImplementedError

# def delete_text_generation(gen_id: int) -> bool:
#     """백엔드가 정해지면 여기서 DELETE /text-generations/{id} 호출"""
#     raise NotImplementedError

st.image("assets/instagram_text.png")
st.write(" ")
st.markdown("인스타그램 홍보 부담을 덜어드릴게요. 인스타그램에 업로드할 센스있는 광고 문구를 생성해 드려요!✨")
st.write(" ")
st.markdown("**1. 이미지 등록하기**: 상품/가게 이미지나 참고할 이미지가 있다면 등록해주세요. (생략 가능합니다.)")
st.markdown("**2. 요청 사항 입력하기**: 상품명을 입력하고 문구 톤을 선택하여 상황에 맞는 광고 문구를 생성해 봐요.")
st.markdown("**3. 직접 요청하기**: 제품 특징, 말투 등의 요구사항을 직접 작성하면 텍스트 품질이 좋아져요.")
st.markdown("**4. 모두 입력이 완료되면, 맨 아래의 :rainbow-background[텍스트 생성하기] 버튼을 누르면 텍스트가 생성됩니다.**")
st.markdown("이제, 아래 단계 별로 하나씩 입력하여 원하는 텍스트를 생성해 봐요. 😆")
st.divider()

# 결과 보관용 세션키
if "insta_text_result" not in st.session_state:
    st.session_state.insta_text_result = None

with st.form("insta_text_form"):
    # 이미지 업로드
    st.subheader("1. 이미지 등록하기")
    st.write("상품/가게 이미지나 참고할 이미지가 있다면 등록해주세요. (이미지가 없다면 생략 가능합니다.)")
    st.write("⬇️ 아래의 :orange-background[Browse files] 버튼을 누르면 이미지 등록이 가능합니다. ⬇️")
    uploaded_file = st.file_uploader("이미지 업로드", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="업로드된 사진",  use_container_width=True)

    st.divider()

    st.subheader("2. 요청 사항 입력하기")
    # 상품 이름/상호명 입력
    st.write("① 상품 이름 또는 상호명을 입력해주세요.")
    title = st.text_input("예시) 순살후라이드, 촉촉쿠키, 해피미용실, 슈퍼헬스장")
    st.write(" ")
    st.write(" ")

    # 말투 톤 성택
    st.write("② 원하시는 말투 톤을 선택해주세요.")
    insta_text_tone = st.radio(
            "광고 문구 톤을 설정해요.",
            options=[
                "친절한 서비스직 말투", "친구같은 반말", "격식있는 정중한 말투"
            ],
            key="insta_text_tone",
        )

    st.divider()

    st.subheader("3. 직접 요청하기")
    # 자유 프롬프트
    st.write("원하는 문구 톤, 제품 특징 등 텍스트 생성에 필요한 요구사항을 작성해봐요. (생략 가능합니다.)")
    prompt_text = st.text_area(
        "요구사항 입력",
        placeholder=(
            "예시)\n"
            "신선한 원두로 내린 부드러운 라떼와 직접 구운 쿠키가 어울리는 카페야. 친구같은 반말 톤으로 상큼하게 표현해줘."
        ),
        height=150
    )
    st.write(" ")
    st.write(" ")

    st.write("⬇️ 모두 입력했다면, 아래의 :rainbow-background[텍스트 생성하기] 버튼을 누르면 텍스트가 생성됩니다. ⬇️")
    submitted = st.form_submit_button("텍스트 생성하기")

st.divider()

st.image("assets/text.png")

# 제출 처리
if submitted:
    if not title:
        st.warning("상품 이름 또는 상호명을 입력해주세요.")
    else:
        placeholder = st.empty()

        # 진행바
        placeholder.progress(0, "센스있는 텍스트를 생성 중이에요 ⌛")
        time.sleep(0.6)
        placeholder.progress(45, "센스있는 텍스트를 생성 중이에요 ⌛")
        time.sleep(0.6)
        placeholder.progress(80, "마무리 중이에요... ✨")
        time.sleep(0.6)
        placeholder.progress(100, "완료!")

        # 실제 모델 호출 로직을 여기에 넣기!
        # resp = requests.post(...).json(); generated_text = resp["text"]
        generated_text = f"[{insta_text_tone}] {title}를 소개합니다! 감성과 센스를 담아 딱 맞게 표현했어요 ✨"
        
        # 진행바 지우고 결과 표시로 교체
        placeholder.empty()
        with placeholder.container():
            st.success("텍스트가 생성되었습니다! 🎉")

            # 텍스트 복사 -> 마크다운 코드 형태
            st.code(generated_text)  # 우상단 복사 아이콘 자동 제공

            # 다운로드 버튼(선택)
            st.download_button(
                "텍스트 다운로드",
                data=generated_text.encode("utf-8"),
                file_name="insta_caption.txt",
                mime="text/plain"
            )