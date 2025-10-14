# scripts/seed_default_models.py
import os, sys
# 프로젝트 루트 경로를 sys.path에 추가 (다른 폴더의 .py 파일을 import하기 위해)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import base64
from sqlmodel import Session, select
from src.backend.database import engine
from src.backend.models import UserModel, User


"""
데이터베이스의 'usermodel' 테이블에 모든 사용자가 공통으로 사용할
기본 모델(Default Models) 데이터를 미리 삽입(seed)하는 스크립트입니다.
이 스크립트는 admin 계정(ID=1)의 소유로 기본 모델들을 생성합니다.

실행 명령어: python scripts/seed_default_models.py
"""


##################################################
# 설정 및 상수
##################################################
# 디폴트 모델 이미지 파일이 저장된 루트 경로
ROOT = "./src/backend/user_models/"

# DB에 추가할 기본 모델 정보 목록
DEFAULT_MODELS = [
    {"filename": "cat.png", "alias": "고양이"},
    {"filename": "dog.png", "alias": "강아지"},
    {"filename": "male_20.png", "alias": "20대 남성"},
    {"filename": "female_20.png", "alias": "20대 여성"},
    {"filename": "male_50.png", "alias": "50대 남성"},
    {"filename": "female_50.png", "alias": "50대 여성"},
]


##################################################
# 유틸리티 함수
##################################################
def encode_image_to_base64(file_path: str) -> str:
    """
    이미지 파일을 읽어서 Base64 데이터 URL로 변환함.
    """
    try:
        # 'rb'는 바이너리 읽기 모드
        with open(file_path, "rb") as image_file:
            image_bytes = image_file.read()
        
        # 파일 확장자로 MIME 타입 결정 (예: 'image/png')
        mimetype = f"image/{file_path.split('.')[-1]}"
        
        # Base64로 인코딩하고 utf-8 문자열로 변환
        base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
        
        # Data URL 형식으로 반환
        return f"data:{mimetype};base64,{base64_encoded}"

    except FileNotFoundError:
        print(f"오류: {file_path} 파일을 찾을 수 없음")
        return None


##################################################
# 메인 시딩(Seeding) 로직
##################################################
def seed_data():
    """
    DB에 기본 사용자 모델(Default Models) 데이터를 초기 삽입(seed)함.
    """
    print("Start Seeding")
    with Session(engine) as session:
        # 기본 모델의 소유자가 될 admin 계정(ID=1)이 있는지 확인
        admin_user = session.get(User, 1)
        if not admin_user:
            print("오류: ID가 1인 admin 계정이 없습니다.")
            return

        # 기본 모델 목록을 순회하며 DB에 추가
        for model_info in DEFAULT_MODELS:
            # 같은 별명(alias)을 가진 모델이 이미 DB에 있는지 중복 확인
            statement = select(UserModel).where(UserModel.alias == model_info["alias"])
            existing_model = session.exec(statement).first()
            
            # 중복되지 않은 모델만 추가 진행
            if not existing_model:
                file_path = os.path.join(ROOT, model_info["filename"])
                image_data_url = encode_image_to_base64(file_path)
                
                if image_data_url:
                    print(f"'{model_info['alias']}' 모델 추가 완료")
                    new_model = UserModel(
                        file_path=image_data_url,
                        alias=model_info["alias"],
                        is_deletable=False,
                        owner_id=1  # admin 계정(ID=1)의 소유로 지정
                    )
                    session.add(new_model)
    
        # 모든 변경사항을 DB에 최종 저장
        session.commit()
    print("Complete Seeding")

    
##################################################
# 스크립트 실행
##################################################
if __name__ == "__main__":
    seed_data()