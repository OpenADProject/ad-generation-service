import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlmodel import Session, text
from src.backend.database import engine


##################################################
# DB 특정 테이블을 리셋하는 스크립트
##################################################
def rebuild_table():

    # Session을 사용해서 데이터베이스에 연결
    with Session(engine) as session:

        # SQL 명령어 실행(만약 usermodel 테이블이 존재하면 테이블 삭제)
        session.exec(text("DROP TABLE IF EXISTS usermodel"))
        session.commit()
        print("Complete")
        

if __name__ == "__main__":
    rebuild_table()