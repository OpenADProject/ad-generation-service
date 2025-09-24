# src/backend/database.py
from sqlmodel import create_engine, SQLModel, Session
import os


##################################################
# 설정
##################################################
# database.db 파일 생성
DATABASE_URL = "sqlite:////home/db/database.db"

# 데이터베이스 엔진 생성
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


##################################################
# 데이터베이스 관련
##################################################
# 서버 시작 시 DB와 테이블을 생성하는 함수
def create_db_and_tables():
    # models.py에서 정의한 모든 SQLModel 테이블을 생성
    SQLModel.metadata.create_all(engine)

# API 요청마다 독립적인 DB 세션을 제공하는 함수
def get_session():
    with Session(engine) as session:
        yield session

# DB 경로 테스트
print(f"DATABASE URL: {DATABASE_URL}")