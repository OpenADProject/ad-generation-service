# scripts/rebuild_database.py
import os, sys
# 프로젝트 루트 경로를 sys.path에 추가 (import src... 구문을 위해)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlmodel import Session, text
from src.backend.database import engine, create_db_and_tables
import typer


"""
개발 중 특정 데이터베이스 테이블을 삭제하고 재생성하기 위한 유틸리티 스크립트입니다.
Typer를 사용하여 커맨드 라인 인터페이스(CLI)를 제공합니다.

실행 명령어: python scripts/rebuild_database.py --table [테이블이름]
"""


##################################################
# 설정 및 초기화
##################################################
# Typer 앱 생성
app = typer.Typer()


##################################################
# CLI 명령어 정의
##################################################
@app.command()
def delete_table(table_name: str = typer.Option(..., "--table")):
    """
    특정 테이블을 DB에서 DROP하고, 최신 스키마로 다시 생성함.
    """
    # 입력받은 table_name이 허용된 목록에 있는지 확인
    allowed_tables = ["generation", "usermodel"]
    if table_name not in allowed_tables:
        print(f"오류: '{table_name}'은(는) 허용되지 않은 테이블 이름입니다.")
        raise typer.Exit(code=1) # 오류 코드와 함께 스크립트 종료
    
    # DB 세션을 열고 SQL 쿼리를 직접 실행
    with Session(engine) as session:
        # DROP TABLE IF EXISTS 쿼리로 테이블이 존재하면 삭제
        session.exec(text(f"DROP TABLE IF EXISTS {table_name}"))
        session.commit()
    
    # FastAPI의 create_db_and_tables 함수를 호출하여 모든 테이블을 다시 생성
    # NOTE: 이 함수는 존재하는 테이블은 건너뛰므로, 삭제된 테이블만 새로 만들어짐
    create_db_and_tables()
    print(f"성공: '{table_name}' 테이블을 초기화하고 재생성했습니다.")


##################################################
# 스크립트 실행
##################################################
if __name__ == "__main__":
    # Typer 앱을 실행하여 커맨드 라인 명령어를 처리
    app()