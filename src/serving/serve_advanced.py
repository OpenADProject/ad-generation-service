# ------------------------------------------
# 작성일 : 2025.09.15
# 버전   : 1차 심화 
# 특징   : 1. 비동기 처리 (async/await)
#          2. base64 이미지 처리 + 업로드 가능
#          3. vLLM 직접 호출 옵션
#          4. 로깅 및 예외 처리 강화
#          5. 분리 + 통합 엔드포인트 제공
#          6. latency 기록
#          7. 동시 요청 추적
#          8. 결과 JSON 자동 저장
#          9. 환경변수(.env) 적용
# ------------------------------------------

import asyncio
import time
import logging
import uuid
import base64
import json
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
import httpx
from dotenv import load_dotenv
import os

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
TEXT_API_URL = os.getenv("TEXT_API_URL", "http://localhost:9000")
IMAGE_API_URL = os.getenv("IMAGE_API_URL", "http://localhost:9100")
VLLM_URL = os.getenv("VLLM_URL", "http://localhost:9002")

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(exist_ok=True)

IMAGE_SAVE_DIR = Path(os.getenv("IMAGE_SAVE_DIR", "generated_images"))
IMAGE_SAVE_DIR.mkdir(exist_ok=True)

# 동시 요청 추적
active_requests = 0
lock = asyncio.Lock()

# ===============================
# FastAPI 앱
# ===============================
app = FastAPI(title="Unified Serving API")

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
# 헬퍼: API 호출 (latency 측정 + 동시 요청 추적)
# ===============================
async def post_with_metrics(client, url, payload, endpoint_name: str):
    global active_requests
    async with lock:
        active_requests += 1
        logger.info(f"[{endpoint_name}] started, active={active_requests}")

    start = time.perf_counter()
    try:
        resp = await client.post(url, json=payload, timeout=60.0)
        resp.raise_for_status()
        duration = time.perf_counter() - start
        logger.info(f"[{endpoint_name}] success {duration:.2f}s (active={active_requests})")
        return resp.json(), duration
    except Exception as e:
        duration = time.perf_counter() - start
        logger.error(f"[{endpoint_name}] failed {duration:.2f}s: {e}")
        raise HTTPException(status_code=500, detail=f"{endpoint_name} error: {str(e)}")
    finally:
        async with lock:
            active_requests -= 1
            logger.info(f"[{endpoint_name}] finished, active={active_requests}")

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
# 텍스트 생성 엔드포인트
# ===============================
@app.post("/generate/text")
async def generate_text(request: Request):
    payload = await request.json()
    async with httpx.AsyncClient() as client:
        if TEXT_API_URL:
            data, latency = await post_with_metrics(client, f"{TEXT_API_URL}/generate", payload, "TEXT_API")
        else:
            # vLLM 직접 호출 (OpenAI-compatible)
            system = "You are an assistant that writes marketing copy. Return JSON with headline, caption, hashtags."
            user = f"Prompt: {payload.get('prompt', '')}"
            vllm_payload = {"model": "llm-model", "messages":[{"role":"system","content":system},{"role":"user","content":user}]}
            resp = await client.post(f"{VLLM_URL}/v1/chat/completions", json=vllm_payload, timeout=60.0)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            try:
                data = json.loads(content)
            except Exception:
                data = {"headline":"", "caption":content, "hashtags":[]}
            latency = 0.0  # 단순화

    save_json({"text": data, "latency_ms": latency}, prefix="text")
    return {"result": data, "latency": latency}

# ===============================
# 이미지 생성 엔드포인트
# ===============================
@app.post("/generate/image")
async def generate_image(request: Request):
    payload = await request.json()
    async with httpx.AsyncClient() as client:
        data, latency = await post_with_metrics(client, f"{IMAGE_API_URL}/generate", payload, "IMAGE_API")
    images = save_base64_images(data)
    save_json({"images": images, "latency_ms": latency}, prefix="image")
    return {"result": images, "latency": latency}

# ===============================
# 통합 광고 생성 엔드포인트 (텍스트 + 이미지)
# ===============================
@app.post("/generate/ad")
async def generate_ad(request: Request):
    payload = await request.json()
    async with httpx.AsyncClient() as client:
        # 1. 텍스트 생성
        text_data, text_latency = await post_with_metrics(client, f"{TEXT_API_URL}/generate", payload, "TEXT_API")

        # 2. 이미지 생성 (텍스트 결과를 프롬프트로 넘김)
        img_payload = {"prompt": text_data.get("output", text_data.get("caption", "default prompt"))}
        image_data, img_latency = await post_with_metrics(client, f"{IMAGE_API_URL}/generate", img_payload, "IMAGE_API")

    images = save_base64_images(image_data)
    total_latency = text_latency + img_latency

    result = {
        "text": text_data,
        "images": images,
        "latency_ms": {"text": text_latency, "image": img_latency, "total": total_latency}
    }
    save_json(result, prefix="ad")
    return result

# ===============================
# 헬스체크
# ===============================
@app.get("/health")
async def health():
    return {"status": "ok", "active_requests": active_requests}

# ===============================
# 실행 예시
# ===============================
# uvicorn serve:app --host 0.0.0.0 --port 9100 --reload
