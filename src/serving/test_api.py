# ------------------------------------------
# 작성일 : 2025.09. 15
# 버 전 : 1차 초기 버전 
# 특 징 : 1. 세 가지 버튼으로 각각 테스트 가능
#            텍스트 전용
#            이미지 전용
#            통합 생성 (문구 + 이미지)
#         2. 업로드 이미지 + 선택 프롬프트 지원
#         3. 로컬 환경에서도 실행 가능
#         4. 서빙 서버(9001)와 바로 연동 가능
# ------------------------------------------
import streamlit as st
import requests
import base64

SERVING_URL = "http://localhost:9001"  # 로컬 서빙 서버

st.title("광고 생성 테스트 (텍스트 + 이미지 분리 & 통합)")

# -------------------------
# 텍스트 전용 생성
# -------------------------
st.header("텍스트 생성")
text_prompt = st.text_area("텍스트 프롬프트", "따뜻한 카페에서 갓 구운 쿠키")
channel = st.selectbox("채널", ["instagram", "blog"], key="text_channel")
tone = st.selectbox("톤앤매너", ["friendly", "formal", "casual"], key="text_tone")
target = st.text_input("타겟층 (예: 20대 여성)", key="text_target")
preset_text = st.selectbox("선택 프롬프트", ["기본", "밝고 화사한", "고급스러운"], key="text_preset")

if st.button("텍스트 생성", key="btn_text"):
    payload = {
        "prompt": text_prompt,
        "channel": channel,
        "tone": tone,
        "target": target,
        "preset": preset_text
    }
    resp = requests.post(f"{SERVING_URL}/generate/text", json=payload)
    if resp.status_code == 200:
        st.json(resp.json())
    else:
        st.error(f"텍스트 생성 실패: {resp.status_code} {resp.text}")

# -------------------------
# 이미지 전용 생성
# -------------------------
st.header("이미지 생성")
image_prompt = st.text_area("이미지 프롬프트", "밤하늘의 별을 모티브로 한 실버 목걸이")
mode = st.selectbox("모드", ["text2image", "image2image"], key="img_mode")
n_images = st.number_input("생성 이미지 수", min_value=1, max_value=5, value=1, key="img_n")
preset_img = st.selectbox("선택 프롬프트", ["기본", "밝고 화사한", "고급스러운"], key="img_preset")
upload_file = st.file_uploader("업로드 이미지 (선택)", type=["png","jpg","jpeg"], key="img_upload")

if st.button("이미지 생성", key="btn_img"):
    files = {}
    if upload_file:
        files["upload_file"] = (upload_file.name, upload_file.getvalue(), upload_file.type)
    data = {
        "prompt": image_prompt,
        "mode": mode,
        "n_images": n_images,
        "preset": preset_img
    }
    resp = requests.post(f"{SERVING_URL}/generate/image", data=data, files=files)
    if resp.status_code == 200:
        for path in resp.json()["image_paths"]:
            st.image(path)
    else:
        st.error(f"이미지 생성 실패: {resp.status_code} {resp.text}")

# -------------------------
# 통합 생성 (텍스트 + 이미지)
# -------------------------
st.header("문구 + 이미지 통합 생성")
ad_prompt = st.text_area("광고 프롬프트", "따뜻한 카페에서 갓 구운 쿠키")
ad_channel = st.selectbox("채널", ["instagram", "blog"], key="ad_channel")
ad_tone = st.selectbox("톤앤매너", ["friendly", "formal", "casual"], key="ad_tone")
ad_target = st.text_input("타겟층 (예: 50대 여성)", key="ad_target")
ad_preset = st.selectbox("선택 프롬프트", ["기본", "밝고 화사한", "고급스러운"], key="ad_preset")
ad_upload = st.file_uploader("업로드 이미지 (선택)", type=["png","jpg","jpeg"], key="ad_upload")

if st.button("통합 생성", key="btn_ad"):
    files = {}
    if ad_upload:
        files["upload_file"] = (ad_upload.name, ad_upload.getvalue(), ad_upload.type)
    data = {
        "prompt": ad_prompt,
        "channel": ad_channel,
        "tone": ad_tone,
        "target": ad_target,
        "preset": ad_preset
    }
    resp = requests.post(f"{SERVING_URL}/generate/ad", data=data, files=files)
    if resp.status_code == 200:
        res_json = resp.json()
        st.subheader("생성 텍스트")
        st.json(res_json["text"])
        st.subheader("생성 이미지")
        for img_path in res_json["image"]["image_paths"]:
            st.image(img_path)
    else:
        st.error(f"통합 생성 실패: {resp.status_code} {resp.text}")

# pip install streamlit requests
# streamlit run test_api.py