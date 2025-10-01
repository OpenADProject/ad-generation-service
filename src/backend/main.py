# src/backend/main.py
from fastapi import FastAPI
from .database import create_db_and_tables
from .routers import generations, user_models, auth
import uvicorn


"""
FastAPI 애플리케이션의 메인 실행 파일(Entrypoint)입니다.
FastAPI 앱을 초기화하고, CORS 미들웨어를 설정하며,
각 기능별로 분리된 API 라우터들을 앱에 포함시키는 역할을 합니다.

실행 명령어: uvicorn src.backend.main:app --reload --port 9000 --host 0.0.0.0
"""


##################################################
# 앱 설정 및 초기화
##################################################
app = FastAPI(title="Backend Server")


##################################################
# 시작 이벤트 -> Alembic으로 관리하여 주석 처리함
##################################################
# 서버 시작 시 DB와 테이블을 생성
# @app.on_event("startup")
# def on_startup():
#     create_db_and_tables()


##################################################
# 라우터 설정
##################################################
# routers 폴더에 정의된 각 API 라우터를 메인 앱에 포함
app.include_router(auth.router)
app.include_router(generations.router)
app.include_router(user_models.router)


##################################################
# 루트 엔드포인트
##################################################
@app.get("/")
def read_root():
    """
    서버가 정상적으로 실행 중인지 확인하기 위한 Health Check용 API.
    """
    return {"status": "Backend server is running"}