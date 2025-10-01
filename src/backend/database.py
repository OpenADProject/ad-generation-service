# src/backend/database.py
from sqlmodel import create_engine, SQLModel, Session
import os


"""
데이터베이스 연결 설정 및 세션 관리를 담당하는 파일입니다.
"""


##################################################
# 설정
##################################################
# database.db 파일 경로 지정
DATABASE_URL = "sqlite:////home/db/database.db"

# 데이터베이스 엔진 생성
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


##################################################
# 데이터베이스 관련 함수
##################################################
def create_db_and_tables():
    """
    서버 시작 시 DB와 모든 테이블을 생성하는 함수.
    NOTE: Alembic으로 DB를 관리하여 실제로 이 함수는 사용하지 않음.
    """
    # models.py에서 정의한 모든 SQLModel 테이블을 생성
    SQLModel.metadata.create_all(engine)

def get_session():
    """
    API의 각 요청마다 독립적인 데이터베이스 세션을 생성하고,
    요청 처리가 끝나면 세션을 자동으로 닫아주는 의존성 함수.
    """
    with Session(engine) as session:
        yield session


##################################################
# DB 경로 확인
##################################################
# 서버 실행 시 터미널에 DB 경로를 출력하여 확인
print(f"DATABASE URL: {DATABASE_URL}")