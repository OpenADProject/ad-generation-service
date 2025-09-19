import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlmodel import Session, select
from src.backend.database import engine
from src.backend.models import UserModel


##################################################
# DB user_models 테이블에 이미지를 추가하는 스크립트
##################################################
# 기본 모델 이미지 경로
ROOT = "./src/backend/user_models/"
FORMAT = ".png"
DEFAULT_MODELS = [
    {"file_path": os.path.join(ROOT, f"cat{FORMAT}"), "alias": "고양이"},
    {"file_path": os.path.join(ROOT, f"dog{FORMAT}"), "alias": "강아지"},
    {"file_path": os.path.join(ROOT, f"male_20{FORMAT}"), "alias": "20대 남성"},
    {"file_path": os.path.join(ROOT, f"female_20{FORMAT}"), "alias": "20대 여성"},
    {"file_path": os.path.join(ROOT, f"male_50{FORMAT}"), "alias": "50대 남성"},
    {"file_path": os.path.join(ROOT, f"female_50{FORMAT}"), "alias": "50대 여성"},
]

def seed_data():
    print("Start Seeding")
    with Session(engine) as session:
        for model_data in DEFAULT_MODELS:
            # DB에 이미 해당 파일 경로의 모델이 있는지 확인
            statement = select(UserModel).where(UserModel.file_path == model_data["file_path"])
            existing_model = session.exec(statement).first()
            
            # 없으면 새로 추가
            if not existing_model:
                print(f">>> Complete: '{model_data['alias']}'")
                new_model = UserModel(
                    file_path=model_data["file_path"],
                    alias=model_data["alias"],
                    is_deletable=False  # 삭제 불가 처리
                )
                session.add(new_model)
        
        session.commit()
    print("End Seeding")

if __name__ == "__main__":
    seed_data()