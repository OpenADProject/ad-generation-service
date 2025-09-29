# ==================================
# api_server.py
# ----------------------------------
# 아주 단순한 FastAPI 서버 예제
# 이미지 생성 API 하나만 있음
# ==================================

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, constr, field_validator
import uvicorn
import traceback
import base64
import binascii

# 내가 만든 main.py 안에 있는 실행 함수
from main import run_pipeline  
# 로깅, 성능 모니터링 (logger.py 참고)
from logger import setup_logger, PerformanceMonitor
# 특정 값만 허용할 때 Literal 사용
from typing import Literal


# ------------------------------
# 옵션 파라미터 모음
# ------------------------------
class Params(BaseModel):
    brand_name: str | None = None        # 브랜드 이름
    background: str | None = None        # 배경 힌트 (예: 카페, 거실)
    target: str | None = None            # 타겟 (안 써도 됨)
    size: constr(pattern=r"^\d+x\d+$") = Field(
        ..., 
        description='"가로x세로" 형식. 예: "1024x1024"', 
        example="1024x1024"
    )
    model_alias: str | None = None       # 모델 이름 (선택)
    file_saved: bool = False             # 저장할지 여부
    recipe: Literal[
        "warm_handmade", "fresh_food", "minimal_premium"
    ] | None = None                      # 레시피 프리셋
    style_hints: list[str] | None = None # 추가 스타일 키워드


# ------------------------------
# 요청 스키마 정의
# ------------------------------
class ImageGenerationRequest(BaseModel):
    product_image: str = Field(..., description="Base64 인코딩된 제품 이미지")
    model_image: str | None = Field(None, description="Base64 인코딩된 모델 이미지 (선택)")
    prompt: str = Field(..., description="프롬프트 문장")
    params: Params

    # Base64 문자열 검증
    @field_validator("product_image", "model_image")
    @classmethod
    def validate_and_normalize_base64(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        # data: 로 시작하면 앞부분 떼기
        if s.startswith("data:"): 
            s = s.split(",", 1)[-1].strip()
        # base64: 접두어 제거
        if s.startswith("base64:"):
            s = s[len("base64:"):].strip()
        # 공백 제거
        s = "".join(s.split())  
        # 파일 경로 막기 (보안)
        if s.startswith("/") or s.startswith("path:"):
            raise ValueError("Only base64 is accepted. 파일 경로는 안됨")
        # base64 문자열인지 확인
        try:
            base64.b64decode(s, validate=True)
        except binascii.Error:
            raise ValueError("Invalid base64 string (개행, 접두어 제거 필요)")
        return s


# ------------------------------
# FastAPI 앱 생성
# ------------------------------
app = FastAPI(
    title="Image Generation API",
    description="SDXL 기반 이미지 생성 API",
    version="1.0.0"
)


# 상태 체크용 (GET /)
@app.get("/")
def health_check():
    return {"status": "ok", "message": "API is running!"}


# 로거 준비
logger = setup_logger()


# ------------------------------
# 이미지 생성 API (POST)
# ------------------------------
@app.post("/generate_image")
async def generate_image(request: ImageGenerationRequest):
    performance_monitor = PerformanceMonitor(logger)
    try:
        performance_monitor.start()   # 시간/메모리 측정 시작
        # 요청 객체를 dict로 변환
        input_data = request.model_dump()
        # 실제 파이프라인 실행
        result = run_pipeline(input_data)
        logger.info("Pipeline 실행 완료")
        return result
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Unhandled exception: {e}")
        # 에러 응답
        raise HTTPException(
            status_code=500, 
            detail={"error": str(e), "traceback": traceback.format_exc()}
        )
    finally:
        performance_monitor.end()     # 측정 종료


# ------------------------------
# 로컬에서 직접 실행할 때
# ------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)