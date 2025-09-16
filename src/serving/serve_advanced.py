# ------------------------------------------
# 작성일 : 2025.09.15
# 버전   : 2차 Hugging Face 최적화 (.env 적용, GPU/CPU 자동)
# 특징   : 1. 비동기 처리 (async/await)
#          2. base64 이미지 처리 + 업로드 가능
#          3. vLLM 직접 호출 옵션
#          4. 로깅 및 예외 처리 강화
#          5. 분리 + 통합 엔드포인트 제공
#          6. latency 기록
#          7. 동시 요청 추적
#          8. 결과 JSON 자동 저장
#          9. 환경변수(.env) 적용
#          10. Hugging Face 이미지 모델 적용 (GPU/CPU 자동 선택)
#  수정  : 2차 서빙에서 텍스트(OpenAI) + Hugging Face 이미지 모델 직접 호출 by. 2025.09.16 kmk
# ------------------------------------------

import asyncio
import time
import logging
import uuid
import base64
import json
from pathlib import Path
from datetime import datetime
import os
from io import BytesIO

from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
import httpx
import torch

# OpenAI 직접 호출
from openai import OpenAI

# Hugging Face 이미지 모델
from diffusers import StableDiffusionPipeline
from PIL import Image

# ===============================
# .env 로드
# ===============================
load_dotenv()

# ===============================
# 로깅 설정
# ===============================
LOG_DIR = Path(os.getenv("LOG_DIR", "log"))
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "serving.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("serve")

# ===============================
# 설정
# ===============================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TEXT_MODEL_CLIENT = OpenAI(api_key=OPENAI_API_KEY)
VLLM_URL = os.getenv("VLLM_URL", "")

# Hugging Face 이미지 모델 로드
IMAGE_MODEL_PATH = os.getenv("IMAGE_MODEL_PATH", "/opt/models/hf")
device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Loading Hugging Face model from {IMAGE_MODEL_PATH} on {device}...")
IMAGE_MODEL = StableDiffusionPipeline.from_pretrained(IMAGE_MODEL_PATH, torch_dtype=torch.float16 if device=="cuda" else torch.float32)
IMAGE_MODEL.to(device)

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(exist_ok=True)
IMAGE_SAVE_DIR = Path(os.getenv("IMAGE_SAVE_DIR", "generated_images"))
IMAGE_SAVE_DIR.mkdir(exist_ok=True)

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:9000/generations/")

# 동시 요청 추적
active_requests = 0
lock = asyncio.Lock()

# ===============================
# FastAPI 앱
# ===============================
app = FastAPI(title="Unified Serving API (Direct Model + DB Record)")

# ===============================
# 헬퍼: JSON 저장
# ===============================
def save_json(result: dict, prefix="result"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = DATA_DIR / f"{prefix}_{ts}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved JSON: {filename}")

# ===============================
# 헬퍼: 이미지 처리 (base64 -> 파일)
# ===============================
def save_base64_images(data: dict):
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

# ===============================
# 헬퍼: 백엔드 기록
# ===============================
async def record_to_backend(payload: dict):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(BACKEND_API_URL, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info(f"Recorded to backend: {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to record to backend: {e}")

# ===============================
# 텍스트 생성 함수 (OpenAI / vLLM 선택)
# ===============================
def generate_text_content(prompt: str, use_vllm: bool = False):
    if use_vllm and VLLM_URL:
        import requests
        payload = {"model": "llm-model", "prompt": prompt}
        r = requests.post(f"{VLLM_URL}/v1/chat/completions", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()["choices"][0]["message"]["content"]
        return data.strip()
    else:
        response = TEXT_MODEL_CLIENT.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
        )
        return response.choices[0].message.content.strip()

# ===============================
# 이미지 생성 함수 (Hugging Face, GPU/CPU 자동)
# ===============================
def generate_image_local(prompt: str):
    """
    Hugging Face 모델로 이미지 생성 후 base64 반환
    """
    generated = IMAGE_MODEL(prompt)
    image = generated.images[0]

    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return {"images": [img_str]}

# ===============================
# 엔드포인트 공통 구조
# ===============================
async def process_request(request: Request, text: bool = False, image: bool = False, ad: bool = False):
    global active_requests
    async with lock:
        active_requests += 1
    start = time.perf_counter()
    try:
        payload = await request.json()
        prompt = payload.get("prompt", "")

        result = {}
        if text:
            text_data = generate_text_content(prompt)
            result["text"] = text_data

        if image:
            image_data = generate_image_local(prompt if not text else text_data)
            images = save_base64_images(image_data)
            result["images"] = images

        total_latency = time.perf_counter() - start
        result["latency_ms"] = total_latency

        await record_to_backend(result)
        save_json(result, prefix="ad" if ad else "request")
        return result
    finally:
        async with lock:
            active_requests -= 1

# ===============================
# 엔드포인트
# ===============================
@app.post("/generate/text")
async def generate_text(request: Request):
    return await process_request(request, text=True)

@app.post("/generate/image")
async def generate_image(request: Request):
    return await process_request(request, image=True)

@app.post("/generate/ad")
async def generate_ad(request: Request):
    return await process_request(request, text=True, image=True, ad=True)

@app.get("/health")
async def health():
    return {"status": "ok", "active_requests": active_requests}

# ===============================
# 실행 예시
# uvicorn serve_advanced_direct:app --host 0.0.0.0 --port 9001 --reload
