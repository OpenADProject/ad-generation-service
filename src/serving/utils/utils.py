# 초기 데모용 서빙 서버 (선택 프롬프트 + 이미지 업로드 지원)

import requests
import os
import uuid
import base64
from pathlib import Path

# 환경변수에서 팀 API URL 가져오기
TEXT_API_URL = os.getenv("TEXT_MODEL_API_URL", "http://localhost:9000")
IMAGE_API_URL = os.getenv("IMAGE_MODEL_API_URL", "http://localhost:9100")

# 이미지 저장 폴더
IMAGE_SAVE_DIR = Path("generated_images")
IMAGE_SAVE_DIR.mkdir(exist_ok=True)

def call_text_api(payload: dict):
    """텍스트 팀 API 호출"""
    resp = requests.post(f"{TEXT_API_URL}/generate", json=payload)
    resp.raise_for_status()
    return resp.json()

def call_image_api(payload: dict):
    """이미지 팀 API 호출"""
    resp = requests.post(f"{IMAGE_API_URL}/generate", json=payload)
    resp.raise_for_status()
    data = resp.json()

    # base64로 이미지 받으면 저장
    images = []
    if "images" in data:
        for b64 in data["images"]:
            raw = base64.b64decode(b64)
            filename = IMAGE_SAVE_DIR / f"{uuid.uuid4().hex[:8]}.png"
            with open(filename, "wb") as f:
                f.write(raw)
            images.append(str(filename))
    elif "urls" in data:
        images = data["urls"]
    return images
