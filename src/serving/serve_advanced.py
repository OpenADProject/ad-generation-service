# ------------------------------------------
# 작성일 : 2025.09.17
# 버전   : 통합 서빙 (텍스트 + 이미지, CLI 경로 적용, JSON 기반 동적 옵션)
# 특징   :
# 1. 비동기 처리 (async/await)
# 2. base64 이미지 처리 + 업로드 가능
# 3. vLLM 직접 호출 옵션
# 4. 로깅 및 예외 처리 강화
# 5. 통합 엔드포인트 제공
# 6. latency 기록
# 7. 동시 요청 추적
# 8. 결과 JSON 자동 저장
# 9. 환경변수(.env) 적용
# 10. 이미지팀 CLI 호출 기반 이미지 생성 (JSON 기반 옵션 반영)
# 11. 외부 텍스트 API POST 호출 분기 지원
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
import subprocess
import httpx

from fastapi import FastAPI, Request
from dotenv import load_dotenv
from openai import OpenAI

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
TEXT_EXTERNAL_URL = os.getenv("TEXT_EXTERNAL_URL", "")
VLLM_URL = os.getenv("VLLM_URL", "")

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(exist_ok=True)

IMAGE_SAVE_DIR = Path(os.getenv("IMAGE_SAVE_DIR", "generated_images"))
IMAGE_SAVE_DIR.mkdir(exist_ok=True)

HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")

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
# 헬퍼: 이미지 처리 (파일 -> base64)
# ===============================
def save_base64_images(file_paths: list):
    images_b64 = []
    for f in file_paths:
        with open(f, "rb") as img_f:
            images_b64.append(base64.b64encode(img_f.read()).decode())
    return images_b64

# ===============================
# 텍스트 생성 함수
# ===============================
def generate_text_content(prompt: str, use_vllm: bool = False):
    # 외부 텍스트 API 우선
    if TEXT_EXTERNAL_URL:
        try:
            resp = httpx.post(TEXT_EXTERNAL_URL, json={"prompt": prompt}, timeout=30)
            resp.raise_for_status()
            data = resp.json().get("text", "")
            if data:
                logger.info("Used external text API.")
                return data.strip()
        except Exception as e:
            logger.warning(f"External text API call failed: {e}")

    # vLLM 사용
    if use_vllm and VLLM_URL:
        import requests
        payload = {"model": "llm-model", "prompt": prompt}
        r = requests.post(f"{VLLM_URL}/v1/chat/completions", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()["choices"][0]["message"]["content"]
        return data.strip()

    # OpenAI 기본 호출
    response = TEXT_MODEL_CLIENT.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )
    return response.choices[0].message.content.strip()

# ===============================
# 이미지 생성 함수 (JSON 기반 동적 옵션 적용)
# ===============================
def generate_image_local_from_json(json_payload: dict):
    prompt = json_payload.get("prompt")
    if not prompt:
        return {"error": "prompt is required"}

    out_dir = Path(json_payload.get("output_path", IMAGE_SAVE_DIR)) / f"gen_{uuid.uuid4().hex[:8]}"
    out_dir.mkdir(parents=True, exist_ok=True)

    cli_cwd = json_payload.get("cli_path", "src")
    input_image = json_payload.get("input_image")

    # 기본값 설정
    size = json_payload.get("size", "768x768")
    steps = str(json_payload.get("steps", 6))
    guidance = str(json_payload.get("guidance", 2.0))
    seed = str(json_payload.get("seed", 11))
    use_ip = str(json_payload.get("use_ip", "false")).lower()
    ref_mode = json_payload.get("ref_mode", "ip_txt2img")

    cmd = [
        "python", "-m", "model.imagemodel.pipeline",
        "--mode", "recon",
        "--out", str(out_dir),
        "--concept", prompt,
        "--size", size,
        "--steps", steps,
        "--guidance", guidance,
        "--seed", seed,
        "--use_ip", use_ip,
        "--ref_mode", ref_mode
    ]

    if input_image and Path(input_image).exists():
        cmd.extend(["--in", input_image])

    env = os.environ.copy()
    try:
        subprocess.run(cmd, check=True, env=env, cwd=cli_cwd)
        generated_files = list(out_dir.glob("*.png"))
        if not generated_files:
            logger.warning("No images generated by CLI.")
            return {"images": []}
        return {"images": save_base64_images(generated_files)}
    except subprocess.CalledProcessError as e:
        logger.error(f"Image generation failed: {e}")
        return {"images": [], "error": str(e)}

# ===============================
# 통합 광고 생성 처리
# ===============================
async def process_request(request: Request, text: bool = False, image: bool = False):
    global active_requests
    async with lock:
        active_requests += 1
    start = time.perf_counter()

    text_data = {}
    images = []
    text_latency = 0.0
    img_latency = 0.0

    try:
        payload = await request.json()
        prompt = payload.get("prompt", "")

        # 텍스트 생성
        if text:
            t0 = time.perf_counter()
            content = generate_text_content(prompt)
            t1 = time.perf_counter()
            text_latency = (t1 - t0) * 1000
            text_data = {"output": content}

        # 이미지 생성
        if image:
            t0 = time.perf_counter()
            image_data = generate_image_local_from_json(payload)
            images = image_data.get("images", [])
            t1 = time.perf_counter()
            img_latency = (t1 - t0) * 1000

        total_latency = text_latency + img_latency

        result = {
            "text": text_data,
            "images": images,
            "latency_ms": {"text": text_latency, "image": img_latency, "total": total_latency}
        }

        save_json(result, prefix="ad")
        return result

    except Exception as e:
        logger.error(f"process_request failed: {e}")
        return {"error": str(e)}

    finally:
        async with lock:
            active_requests -= 1

# ===============================
# FastAPI 엔드포인트
# ===============================
@app.post("/generate/ad")
async def generate_ad(request: Request):
    return await process_request(request, text=True, image=True)

@app.get("/health")
async def health():
    return {"status": "ok", "active_requests": active_requests}

# ===============================
# 실행 예시
# uvicorn src.serving.serve_advanced:app --host 0.0.0.0 --port 9001
# ===============================
