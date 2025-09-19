# ------------------------------------------
# 작성일 : 2025.09.17
# 버전   : 통합 서빙 (텍스트 + 이미지, CLI 경로 적용, JSON 기반 동적 옵션)
# 특징   :
# 1. 비동기 처리 (async/await)
# 2. base64 이미지 처리 + 업로드 가능
# 3. vLLM 직접 호출 옵션
# 4. 로깅 및 예외 처리 강화
# 5. 통합 엔드포인트 제공 + 개별 텍스트/이미지 엔드포인트 추가
# 6. latency 기록
# 7. 동시 요청 추적
# 8. 결과 JSON 자동 저장
# 9. 환경변수(.env) 적용
# 10. 이미지팀 CLI 호출 기반 이미지 생성 (JSON 기반 옵션 반영)
# 11. 외부 텍스트 API POST 호출 분기 지원
# 12. 백엔드 이력 추가
# ------------------------------------------
import asyncio
import time
import logging
import uuid
import base64
import json
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TEXT_MODEL_CLIENT = OpenAI(api_key=OPENAI_API_KEY)
TEXT_EXTERNAL_URL = os.getenv("TEXT_EXTERNAL_URL", "")
VLLM_URL = os.getenv("VLLM_URL", "")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:9000/generations/")

PROJECT_ROOT = Path(__file__).parent.parent.parent

DATA_DIR = PROJECT_ROOT / os.getenv("DATA_DIR", "data")
DATA_DIR.mkdir(exist_ok=True)

IMAGE_SAVE_DIR = PROJECT_ROOT / os.getenv("IMAGE_SAVE_DIR", "generated_images")
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
# 헬퍼: 이미지 처리 (파일 -> base64)
# ===============================
def _get_base64_from_path(file_path: Path):
    if not file_path.exists():
        logger.warning(f"Image file not found: {file_path}")
        return None
    with open(file_path, "rb") as img_f:
        encoded_string = base64.b64encode(img_f.read()).decode()
    return f"data:image/png;base64,{encoded_string}"

# ===============================
# 텍스트 생성 함수
# ===============================
def generate_text_content(prompt: str, use_vllm: bool = False):
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

    if use_vllm and VLLM_URL:
        pass  # vLLM 호출 로직 생략

    response = TEXT_MODEL_CLIENT.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )
    return response.choices[0].message.content.strip()

# ===============================
# 이미지 생성 함수
# ===============================
def generate_image_local_from_json(json_payload: dict):
    prompt = json_payload.get("prompt")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required for image generation.")

    out_dir_name = f"gen_{uuid.uuid4().hex[:8]}"
    out_dir_abs = IMAGE_SAVE_DIR / out_dir_name
    out_dir_abs.mkdir(parents=True, exist_ok=True)
    
    cli_cwd = PROJECT_ROOT

    size = json_payload.get("size", "768x768")
    steps = str(json_payload.get("steps", 6))
    guidance = str(json_payload.get("guidance", 2.0))
    seed = str(json_payload.get("seed", 11))
    use_ip = str(json_payload.get("use_ip", "false")).lower()
    ref_mode = json_payload.get("ref_mode", "ip_txt2img")
    
    if ref_mode in ["ip_txt2img", "img2img"]:
        input_image_path = json_payload.get("input_image")
        if not input_image_path:
            raise HTTPException(status_code=400, detail=f"The selected 'ref_mode' ({ref_mode}) requires an 'input_image' argument.")
        full_image_path = PROJECT_ROOT / input_image_path
        if not full_image_path.exists():
            raise HTTPException(status_code=404, detail=f"Input image file not found: {full_image_path}")
        input_image_arg = str(full_image_path)
    else:
        input_image_arg = None

    cmd = [
        "python", "-m", "src.model.imagemodel.pipeline", 
        "--mode", "recon",
        "--out", str(out_dir_abs),
        "--concept", prompt,
        "--size", size,
        "--steps", steps,
        "--guidance", guidance,
        "--seed", seed,
        "--use_ip", use_ip,
        "--ref_mode", ref_mode
    ]

    if input_image_arg:
        cmd.extend(["--in", input_image_arg])
    
    env = os.environ.copy()
    try:
        result = subprocess.run(cmd, check=True, env=env, cwd=cli_cwd, capture_output=True, text=True)
        logger.info(f"Subprocess stdout: {result.stdout}")
        logger.info(f"Subprocess stderr: {result.stderr}")

        meta_file_path = out_dir_abs / "meta.json"
        if not meta_file_path.exists():
            logger.error(f"Meta file not found at {meta_file_path}")
            return {"images": [], "error": "Meta file not found.", "image_file_path": None}
        
        with open(meta_file_path, "r", encoding="utf-8") as f:
            meta_data = json.load(f)
        
        generated_image_path = out_dir_abs / meta_data["paths"]["final"]
        base64_image = _get_base64_from_path(generated_image_path)
        
        if base64_image:
            return {"images": [base64_image], "meta": meta_data, "image_file_path": str(generated_image_path)}
        else:
            return {"images": [], "error": "Image file not found.", "image_file_path": None}
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Image generation failed: {e.stderr}")
        return {"images": [], "error": f"Image generation failed: {e.stderr}", "image_file_path": None}

# ===============================
# 통합 광고 생성 처리
# ===============================
async def post_with_metrics(client, url, payload, endpoint_name: str):
    global active_requests
    async with lock:
        active_requests += 1
    start = time.perf_counter()

    final_result = {
        "text": {},
        "images": [],
        "latency_ms": {}
    }
    
    generated_image_path = None
    
    try:
        payload = await request.json()
        prompt = payload.get("prompt", "")
        
        if text:
            t0 = time.perf_counter()
            content = generate_text_content(prompt)
            text_latency = (time.perf_counter() - t0) * 1000
            final_result["text"]["output"] = content
            final_result["latency_ms"]["text"] = text_latency
            
        if image:
            t0 = time.perf_counter()
            image_data = generate_image_local_from_json(payload)
            image_latency = (time.perf_counter() - t0) * 1000
            
            final_result["images"] = image_data.get("images", [])
            final_result["latency_ms"]["image"] = image_latency
            generated_image_path = image_data.get("image_file_path")
            
            if "error" in image_data:
                final_result["error"] = image_data["error"]
                
        total_latency = final_result["latency_ms"].get("text", 0) + final_result["latency_ms"].get("image", 0)
        final_result["latency_ms"]["total"] = total_latency

        try:
            if final_result.get("text") or generated_image_path:
                backend_payload = {
                    "input_text": prompt,
                    "output_text": final_result["text"].get("output"),
                    "output_image_path": generated_image_path,
                }
                async with httpx.AsyncClient() as client:
                    response = await client.post(BACKEND_API_URL, json=backend_payload, timeout=10)
                    response.raise_for_status()
                    logger.info("Successfully sent generation log to backend.")
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send to backend (HTTP Error): {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Failed to send to backend (Request Error): {e}")

        save_json(final_result, prefix="ad")
        return JSONResponse(content=final_result)
        
    except Exception as e:
        logger.error(f"process_request failed: {e}")
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(status_code=500, detail=str(e))
    
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

@app.post("/generate/text")
async def generate_text_only(request: Request):
    return await process_request(request, text=True, image=False)

@app.post("/generate/image")
async def generate_image_only(request: Request):
    return await process_request(request, text=False, image=True)

@app.get("/health")
async def health():
    return {"status": "ok", "active_requests": active_requests}

# ===============================
# 실행 예시
# uvicorn src.serving.serve_advanced:app --host 0.0.0.0 --port 9001 --reload
# ===============================
# uvicorn serve:app --host 0.0.0.0 --port 9100 --reload
