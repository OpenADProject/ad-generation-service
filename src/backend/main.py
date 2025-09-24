# src/backend/main.py
from fastapi import FastAPI
from .database import create_db_and_tables
from .routers import generations, user_models, auth
import uvicorn

# 실행 명령어: uvicorn src.backend.main:app --reload --port 9000 --host 0.0.0.0

# 앱 설정
app = FastAPI(title="Backend Server")

# 서버 시작 시 DB와 테이블을 생성
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# routers 폴더 내 API 메인 앱에 포함
app.include_router(auth.router)
app.include_router(generations.router)
app.include_router(user_models.router)

# 서버 상태 확인
@app.get("/")
def read_root():
    return {"status": "Backend server is running"}