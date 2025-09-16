import time
import streamlit as st
from PIL import Image
from io import BytesIO

st.image("assets/instagram_image.png")
st.write(" ")
st.markdown("인스타그램 홍보 부담을 덜어드릴게요. 인스타그램에 업로드할 멋진 이미지를 생성해 드려요!✨")
st.write(" ")
st.markdown("**1. 이미지 등록하기**: 상품/가게 이미지나 참고할 이미지가 있다면 등록해주세요. (생략 가능합니다.)")
st.markdown("**2. 요청 사항 입력하기**: 상품명, 이미지 배경을 입력하여 원하는 이미지를 생성해 봐요.")
st.markdown("**3. 직접 요청하기**: 주변 물체, 장소, 이미지 분위기 등 요구사항을 직접 작성하면 이미지 품질이 좋아져요.")
st.markdown("**4. 모두 입력이 완료되면, 맨 아래의 :rainbow-background[이미지 생성하기] 버튼을 누르면 이미지가 생성됩니다.**")
st.markdown("이제, 아래 단계 별로 하나씩 입력하여 원하는 이미지를 생성해 봐요. 😆")
st.divider()

with st.form("insta_image_form"):
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

    # 이미지 배경 성택
    st.write("② 원하시는 이미지 배경을 선택해주세요.")
    bg_choice = st.radio(
        "생성 이미지의 배경을 설정합니다.",
        options=[
            "화이트(기본)", "매장 내부", "야외 풍경",
            "카페 분위기", "고급스러운 배경",
            "밝고 화사한 배경", "심플 단색 배경"
        ],
        key="bg_choice",
    )

    st.divider()

    st.subheader("3. 직접 요청하기")
    # 자유 프롬프트
    st.write("주변 물체, 장소, 이미지 분위기 등 이미지 생성에 필요한 요구사항을 작성해봐요. (생략 가능합니다.)")
    prompt_text = st.text_area(
        "요구사항 입력",
        placeholder=(
            "예시)\n"
            "카페 테이블 위에 놓인 아이스 아메리카노가 있고, 창가 햇살이 들어오는 분위기와 따뜻하고 감성적인 느낌으로 만들어줘."
        ),
        height=150
    )

    st.write(" ")
    st.write(" ")

    st.write("⬇️ 모두 입력했다면, 아래의 :rainbow-background[이미지 생성하기] 버튼을 누르면 이미지가 생성됩니다. ⬇️")
    submitted = st.form_submit_button("이미지 생성하기")

st.image("assets/image.png")

# 제출 처리
if submitted:
    if not title:
        st.warning("상품 이름 또는 상호명을 입력해주세요.")
    else:
        placeholder = st.empty()

        # 진행바
        placeholder.progress(0, "매력적인 이미지를 생성 중이에요 ⌛")
        time.sleep(0.6)
        placeholder.progress(50, "매력적인 이미지를 생성 중이에요 ⌛")
        time.sleep(0.6)
        placeholder.progress(100, "완료!")

        # 결과로 업로드한 이미지를 다시 출력
        image = Image.open(uploaded_file)
        buf = BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)

        placeholder.empty()
        with placeholder.container():
            st.success("이미지가 생성되었습니다! 🎉 ")
            st.image(image, caption="생성 결과", use_container_width=True)

            st.download_button(
                "이미지 다운로드 (PNG)",
                data=buf.getvalue(),
                file_name=f"{title or 'generated'}_image.png",
                mime="image/png",
                use_container_width=True,
            )


