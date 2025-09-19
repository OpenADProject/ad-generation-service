from fastapi import FastAPI
from .database import create_db_and_tables
from .routers import generations, user_models
import uvicorn

# uvicorn src.backend.main:app --reload --port 9000 --host 0.0.0.0

app = FastAPI(
    title="광고 생성 서비스 - 백엔드 API",
    description="광고 콘텐츠 생성 이력 관리를 위한 API입니다."
)

# 서버 시작 시 DB와 테이블을 생성
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# routers 폴더 내 API 메인 앱에 포함
# app.include_router(auth.router) # 계정 기능 추가 시 사용 예정
app.include_router(generations.router)
app.include_router(user_models.router)

# 서버 상태를 확인
@app.get("/")
def read_root():
    return {"status": "Backend server is running"}


# 백엔드 서버 단독 실행
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)