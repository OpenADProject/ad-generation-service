# ------------------------------------------
# 작성일 : 2025.09. 15
# 버 전 : 1차 초기 버전(팀 코드 연결 확인용)
# 특 징 : 1. 텍스트 전용 생성
#            엔드포인트: /generate/text
#            Pydantic 모델: TextGenRequest, TextGenResponse
#            선택 프롬프트(preset) 적용 가능
#            순수 텍스트 생성만 담당
#         2. 이미지 전용 생성
#            엔드포인트: /generate/image
#            Form + File 기반 입력
#            text2image / image2image 모드 지원
#            선택 프롬프트 + 업로드 이미지 적용 가능
#            Pydantic 모델: ImageGenResponse
#         3. 문구 + 이미지 통합 생성
#            엔드포인트: /generate/ad
#            텍스트 먼저 생성 (call_text_api) → 생성된 캡션 기반으로 이미지 생성 (call_image_api)
#            선택 프롬프트 + 업로드 이미지 적용 가능
#           최종 반환: { "text": {...}, "image": { "image_paths": [...] } }
# ------------------------------------------
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
from utils import call_text_api, call_image_api
import base64

app = FastAPI(title="Serving API - Demo", version="1.0.0")

# --- Pydantic schemas
class TextGenRequest(BaseModel):
    prompt: str
    channel: Optional[str] = "instagram"
    tone: Optional[str] = "friendly"
    target: Optional[str] = None
    preset: Optional[str] = None  # 선택 프롬프트

class TextGenResponse(BaseModel):
    headline: str
    caption: str
    hashtags: List[str]

class ImageGenRequest(BaseModel):
    prompt: str
    mode: Optional[str] = "text2image"
    n_images: Optional[int] = 1
    preset: Optional[str] = None  # 선택 프롬프트

class ImageGenResponse(BaseModel):
    image_paths: List[str]

# ----------------------------
# 텍스트 생성
# ----------------------------
@app.post("/generate/text", response_model=TextGenResponse)
def generate_text(req: TextGenRequest):
    try:
        payload = req.dict()
        if req.preset:
            payload["prompt"] += f" | Preset: {req.preset}"
        return call_text_api(payload)
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------
# 이미지 생성 (text2image / image2image + 선택 프롬프트)
# ----------------------------
@app.post("/generate/image", response_model=ImageGenResponse)
async def generate_image(
    prompt: str = Form(...),
    mode: str = Form("text2image"),
    n_images: int = Form(1),
    preset: Optional[str] = Form(None),
    upload_file: Optional[UploadFile] = File(None)
):
    try:
        full_prompt = prompt
        if preset:
            full_prompt += f" | Preset: {preset}"

        # 업로드된 이미지가 있으면 base64로 서버 전달
        if upload_file:
            content = await upload_file.read()
            b64_image = base64.b64encode(content).decode("utf-8")
            full_prompt += f" | Base64Image:{b64_image}"

        payload = {"prompt": full_prompt, "mode": mode, "n_images": n_images}
        images = call_image_api(payload)
        return {"image_paths": images}
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------
# 문구 + 이미지 통합 생성
# ----------------------------
@app.post("/generate/ad")
async def generate_ad(
    prompt: str = Form(...),
    channel: str = Form("instagram"),
    tone: str = Form("friendly"),
    target: Optional[str] = Form(None),
    preset: Optional[str] = Form(None),
    upload_file: Optional[UploadFile] = File(None)
):
    try:
        # 1. 텍스트 생성
        text_payload = {"prompt": prompt, "channel": channel, "tone": tone, "target": target, "preset": preset}
        text_data = call_text_api(text_payload)

        # 2. 이미지 생성
        img_prompt = text_data.get("caption", "")
        if preset:
            img_prompt += f" | Preset: {preset}"
        if upload_file:
            content = await upload_file.read()
            b64_image = base64.b64encode(content).decode("utf-8")
            img_prompt += f" | Base64Image:{b64_image}"

        image_payload = {"prompt": img_prompt, "mode": "text2image", "n_images": 1}
        images = call_image_api(image_payload)

        return {"text": text_data, "image": {"image_paths": images}}
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
