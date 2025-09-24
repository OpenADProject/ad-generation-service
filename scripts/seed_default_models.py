import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import base64
from sqlmodel import Session, select
from src.backend.database import engine
from src.backend.models import UserModel


##################################################
# DB user_models 테이블에 이미지를 추가하는 스크립트
##################################################
# 디폴트 모델 이미지 경로
ROOT = "./src/backend/user_models/"

# 기본 모델 파일 목록
DEFAULT_MODELS = [
    {"filename": "cat.png", "alias": "고양이"},
    {"filename": "dog.png", "alias": "강아지"},
    {"filename": "male_20.png", "alias": "20대 남성"},
    {"filename": "female_20.png", "alias": "20대 여성"},
    {"filename": "male_50.png", "alias": "50대 남성"},
    {"filename": "female_50.png", "alias": "50대 여성"},
]

# Base 64 인코딩 로직
def encode_image_to_base64(file_path: str) -> str:
    """이미지 파일을 읽어서 Base64 데이터 URL로 변환하는 함수"""
    try:
        with open(file_path, "rb") as image_file: # 'rb'는 바이너리 읽기 모드
            image_bytes = image_file.read()
        
        # 파일 확장자로 MIME 타입 결정 (예: 'image/png')
        mimetype = f"image/{file_path.split('.')[-1]}"
        
        # Base64로 인코딩하고 utf-8 문자열로 변환
        base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
        
        # Data URL 형식으로 변환
        return f"data:{mimetype};base64,{base64_encoded}"

    except FileNotFoundError:
        print(f"{file_path} 파일 없음")
        return None

# 디폴트 이미지 로드 및 변환 함수
def seed_data():
    print("Start Seeding")
    with Session(engine) as session:
        for model_info in DEFAULT_MODELS:
            # 별명(alias) 중복 확인
            statement = select(UserModel).where(UserModel.alias == model_info["alias"])
            existing_model = session.exec(statement).first()
            
            if not existing_model:
                file_path = os.path.join(ROOT, model_info["filename"])
                
                # Base64 데이터 URL로 인코딩
                image_data_url = encode_image_to_base64(file_path)
                
                if image_data_url:
                    print(f"'{model_info['alias']}' 추가 완료")
                    new_model = UserModel(
                        file_path=image_data_url,
                        alias=model_info["alias"],
                        is_deletable=False
                    )
                    session.add(new_model)
    
        session.commit()
    print("End Seeding")

if __name__ == "__main__":
    seed_data()