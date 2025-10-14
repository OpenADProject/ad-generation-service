# api_server.py

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, constr, field_validator
import uvicorn, traceback, base64, binascii
import config
from logger import setup_logger
from pipeline import ImageGenerationPipeline
from typing import Literal

# Pydantic 모델
class Params(BaseModel):
    brand_name: str | None = None
    background: str | None = None
    target: str | None = None
    size: constr(pattern=r"^\d+x\d+$") = Field("1024x1024", description='"가로x세로" 형식')
    model_alias: str | None = None
    file_saved: bool = False
    seed: int | None = None

class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., description="프롬프트 문장")
    params: Params
    product_image: str | None = Field(None, description="Base64 인코딩된 제품 이미지")
    model_image: str | None = Field(None, description="Base64 인코딩된 모델 이미지")
    @field_validator("product_image", "model_image")
    @classmethod
    def validate_base64(cls, v: str | None):
        if v is None: return None
        
        try:
            if ',' in v:
                v = v.split(',', 1)[1]
            
            missing_padding = len(v) % 4
            if missing_padding:
                v += '=' * (4 - missing_padding)
            
            base64.b64decode(v, validate=True)
            return v
        except (binascii.Error, IndexError, TypeError) as e:
            raise ValueError(f"Invalid base64 string: {e}")

# FastAPI 앱 및 로거 생성
app = FastAPI(title="Image Generation API", version="1.0.0")
logger = setup_logger()
pipeline_instance = None

@app.on_event("startup")
def load_pipeline():
    global pipeline_instance
    logger.info("서버 시작: 이미지 생성 파이프라인 로딩...")
    pipeline_instance = ImageGenerationPipeline(config=config, logger=logger)
    logger.info("파이프라인 로딩 완료.")

@app.get("/")
def health_check():
    return {"status": "ok" if pipeline_instance else "loading"}

@app.post("/generate_image")
async def generate_image(request: ImageGenerationRequest):
    if not pipeline_instance:
        raise HTTPException(status_code=503, detail="서버가 준비 중입니다.")
    try:
        input_data = request.model_dump()
        result = await run_in_threadpool(pipeline_instance.run, input_data)
        return result
    except Exception as e:
        logger.error(f"Error during image generation: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="이미지 생성 중 내부 서버 오류 발생")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)