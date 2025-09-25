# serve_ready.py
# ------------------------------------
# 1. 프론트 → 서빙: JSON 통일
# 2. 서빙 → 모델 호출: 텍스트API / 이미지API (병렬 호출)
# 3. 서빙 → 백엔드: 생성 결과 기록 (비동기)
# 4. 프론트에는 API 응답 그대로 전달
# ------------------------------------

import json
import os
import logging
import re
import time
import asyncio
from datetime import datetime
from typing import Dict, Any
from asyncio import Semaphore
import httpx
from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
from pathlib import Path
from logging.handlers import RotatingFileHandler
import base64

# ===============================
# 환경 변수 로드
# ===============================
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path)

TEXT_API_URL = os.getenv("TEXT_API_URL", "http://34.123.118.58:8080/generate")
IMAGE_API_URL_JSON = os.getenv("IMAGE_API_URL_JSON", "http://34.123.118.58:8090/generate_image")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:9000/generations/")
BACKEND_API_TOKEN = os.getenv("BACKEND_API_TOKEN", "")

MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", 10))
semaphore = Semaphore(MAX_CONCURRENT)

# ===============================
# 로그 경로 설정
# ===============================
LOG_DIR = Path(__file__).resolve().parent / "log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / "serve_ready.log"

handler = RotatingFileHandler(
    filename=log_file,
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)
formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler, logging.StreamHandler()],
)

# ===============================
# FastAPI 앱 생성
# ===============================
app = FastAPI(title="AdGen Serving API", version="2.7")


# ===============================
# 유틸 함수
# ===============================
def validate_base64(b64_str: str) -> bool:
    pattern = re.compile(r"^[A-Za-z0-9+/=\n\r]+$")
    return bool(b64_str) and bool(pattern.match(b64_str))


def clean_base64(b64_str: str) -> str:
    """
    base64 문자열에서 header(data:image/png;base64,) 제거
    """
    if not b64_str:
        return ""
    if "," in b64_str:
        return b64_str.split(",")[1]
    return b64_str


async def call_api_with_retry(url: str, payload: Dict[str, Any], timeout: int = 60, retries: int = 3) -> Dict[str, Any]:
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                start_time = time.time()
                logging.info(f"API 호출 시작: {url}")
                res = await client.post(url, json=payload)
                res.raise_for_status()
                elapsed = time.time() - start_time
                logging.info(f"API 호출 성공: {url}, 소요시간: {elapsed:.2f}s")
                return res.json()
        except Exception as e:
            logging.error(f"[API 호출 오류] {url} 시도 {attempt+1}/{retries}: {repr(e)}")
            if attempt == retries - 1:
                raise


async def call_text_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await call_api_with_retry(TEXT_API_URL, payload, timeout=60)


async def call_image_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await call_api_with_retry(IMAGE_API_URL_JSON, payload, timeout=300)


async def save_generation_history(record: Dict[str, Any], owner_id: int) -> None:
    try:
        record["owner_id"] = owner_id
        headers = {}
        if BACKEND_API_TOKEN:
            headers["Authorization"] = f"Bearer {BACKEND_API_TOKEN}"

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(BACKEND_API_URL, json=record, headers=headers)
            res.raise_for_status()
            logging.info("백엔드 생성 기록 저장 완료")
    except Exception as e:
        logging.error(f"[Backend 저장 오류] {repr(e)}")


# ===============================
# 엔드포인트
# ===============================
@app.post("/infer/text")
async def infer_text(request: Request):
    async with semaphore:
        body = await request.json()
        owner_id = body.get("owner_id", 0)

        if "product" not in body:
            raise HTTPException(status_code=400, detail="product 값이 필요합니다")

        payload = body
        try:
            text_result = await call_text_api(payload)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"텍스트 API 호출 실패: {str(e)}")

        output_text = text_result.get("result", "")

        asyncio.create_task(
            save_generation_history({
                "input_text": body.get("product", ""),
                "input_image_path": "",
                "output_text": output_text,
                "output_image_path": "",
            }, owner_id)
        )

        return {"text": output_text, "success": True}


@app.post("/infer/image")
async def infer_image(request: Request):
    async with semaphore:
        body = await request.json()
        owner_id = body.get("owner_id", 0)

        product_b64 = clean_base64(body.get("product_image", ""))
        model_b64 = clean_base64(body.get("model_image", ""))
        prompt = body.get("prompt", "")
        params = body.get("params", {})

        if not (product_b64 or model_b64):
            raise HTTPException(status_code=400, detail="최소 한 개의 이미지(base64)가 필요합니다")

        if product_b64 and not validate_base64(product_b64):
            raise HTTPException(status_code=400, detail="product_image base64 형식이 올바르지 않습니다")
        if model_b64 and not validate_base64(model_b64):
            raise HTTPException(status_code=400, detail="model_image base64 형식이 올바르지 않습니다")

        payload = {
            "model_image": model_b64,
            "product_image": product_b64,
            "prompt": prompt,
            "params": params
        }

        try:
            image_result = await call_image_api(payload)
            logging.info(f"[이미지 API 응답] {json.dumps(image_result)[:2000]}")
        except Exception as e:
            logging.error(f"[이미지 API 호출 실패] {str(e)}")
            raise HTTPException(status_code=500, detail=f"이미지 API 호출 실패: {str(e)}")

        asyncio.create_task(
            save_generation_history({
                "input_text": prompt,
                "input_image_path": product_b64 or model_b64 or "",
                "output_text": "",
                "output_image_path": image_result.get("output_base64", ""),
            }, owner_id)
        )

        return image_result


@app.post("/infer/all")
async def infer_all(request: Request):
    async with semaphore:
        body = await request.json()
        owner_id = body.get("owner_id", 0)

        product_b64 = clean_base64(body.get("product_image", ""))
        model_b64 = clean_base64(body.get("model_image", ""))

        if not (product_b64 or model_b64):
            raise HTTPException(status_code=400, detail="최소 한 개의 이미지(base64)가 필요합니다")

        text_payload = {k: v for k, v in body.items() if k in ["product", "tone", "channel", "target_audience", "translate_en"]}
        image_payload = {
            "model_image": model_b64,
            "product_image": product_b64,
            "prompt": body.get("prompt", ""),
            "params": body.get("params", {})
        }

        logging.info("텍스트 API + 이미지 API 병렬 호출 시작")
        text_task = asyncio.create_task(call_text_api(text_payload))
        image_task = asyncio.create_task(call_image_api(image_payload))

        try:
            text_result, image_result = await asyncio.gather(text_task, image_task)
            logging.info(f"[이미지 API 응답] {json.dumps(image_result)[:2000]}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"API 호출 실패: {str(e)}")
        logging.info("텍스트 API + 이미지 API 병렬 호출 완료")

        output_text = text_result.get("result", "")

        asyncio.create_task(
            save_generation_history({
                "input_text": body.get("product", ""),
                "input_image_path": product_b64 or model_b64 or "",
                "output_text": output_text,
                "output_image_path": image_result.get("output_base64", ""),
            }, owner_id)
        )

        return {
            "text": output_text,
            "image_result": image_result,
            "success": True
        }


# -----------------------------------
# 헬스 체크
# -----------------------------------
@app.get("/health_check")
async def health_check():
    result = {}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(TEXT_API_URL, json={"prompt": "테스트", "params": {}, "product": "dummy"})
            result["text_api"] = {"connected": res.status_code == 200, "status": res.status_code,
                                  "error": None if res.status_code == 200 else res.text}
    except Exception as e:
        result["text_api"] = {"connected": False, "status": None, "error": str(e)}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            dummy_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAgMBgkK8VgAAAABJRU5ErkJggg=="
            res = await client.post(IMAGE_API_URL_JSON,
                                    json={"model_image": "", "product_image": dummy_b64, "prompt": "테스트", "params": {}})
            result["image_api"] = {"connected": res.status_code == 200, "status": res.status_code,
                                   "error": None if res.status_code == 200 else res.text}
    except Exception as e:
        result["image_api"] = {"connected": False, "status": None, "error": str(e)}

    return result


@app.get("/test")
def test():
    return {"status": "server_ok"}

# ===============================
# 실행 예시
# uvicorn src.serving.serve_advanced:app --host 0.0.0.0 --port 9001 --reload
# ===============================
