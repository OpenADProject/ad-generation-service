import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlmodel import Session, text
from src.backend.database import engine, create_db_and_tables
import typer


##################################################
# DB 특정 테이블을 초기화하는 스크립트
# python scripts/rebuild_database.py --table {table_name}
##################################################
# Typer 앱 생성
app = typer.Typer()

# 메인 함수를 Typer의 명령어로 등록
@app.command()
def delete_table(table_name: str = typer.Option(..., "--table")):
    """
    특정 테이블을 DB에서 DROP(서버 시작 시 최신 스키마 자동 생성)
    """
    
    # 입력받은 table_name이 유효한지 확인
    allowed_tables = ["generation", "usermodel"]
    if table_name not in allowed_tables:
        print(f"테이블 미존재")
        raise typer.Exit(code=1) # 스크립트 종료
    
    # 입력받은 table_name으로 SQL 쿼리 실행
    with Session(engine) as session:
        session.exec(text(f"DROP TABLE IF EXISTS {table_name}"))
        session.commit()
    
    # 테이블 재생성
    create_db_and_tables()
    print(f"'{table_name}' 테이블 삭제 완료")

# 실행
if __name__ == "__main__":
    # 프로젝트 루트 경로를 sys.path에 추가 (import src... 구문을 위해)
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    app()