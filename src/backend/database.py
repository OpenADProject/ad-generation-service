from sqlmodel import create_engine, SQLModel, Session
import os

# 프로젝트 루트 폴더에 database.db 파일을 생성
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT, 'database.db')}"

# 데이터베이스 엔진 생성
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 서버 시작 시 DB와 테이블을 생성하는 함수
def create_db_and_tables():
    # models.py에서 정의한 모든 SQLModel 테이블을 생성
    SQLModel.metadata.create_all(engine)

# API 요청마다 독립적인 DB 세션을 제공하는 함수
def get_session():
    with Session(engine) as session:
        yield session