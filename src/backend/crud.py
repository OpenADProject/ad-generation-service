import os
from sqlmodel import Session, select
from . import models


##################################################
# 사용자 콘텐츠 생성 결과물 관리
##################################################
# C
def create_generation(db: Session, generation: models.GenerationCreate):
    """
    API로부터 받은 GenerationCreate 데이터를 DB에 저장할 Generation 객체로 변환하고,
    DB에 추가(add), 저장(commit), 새로고침(refresh)합니다.
    """
    db_generation = models.Generation.from_orm(generation)
    db.add(db_generation)
    db.commit()
    db.refresh(db_generation)
    return db_generation

# R
def get_generation_by_id(db: Session, generation_id: int):
    """ID를 기준으로 특정 생성 이력 하나를 조회합니다."""
    return db.get(models.Generation, generation_id)

def get_generations(db: Session, skip: int = 0, limit: int = 100):
    """
    모든 생성 이력을 조회하되, pagination(페이지네이션)을 적용합니다.
    skip: 몇 개의 데이터를 건너뛸지
    limit: 몇 개의 데이터를 가져올지
    """
    statement = select(models.Generation).order_by(models.Generation.id.desc()).offset(skip).limit(limit)
    results = db.exec(statement).all()
    return results

# D
def delete_generation(db: Session, generation_id: int):
    """ID를 기준으로 특정 생성 이력을 찾아서 삭제합니다."""
    # 해당 id의 데이터가 있는지 조회
    generation_to_delete = get_generation_by_id(db, generation_id=generation_id)
    
    # 데이터가 없으면 None을 반환(404 에러)
    if not generation_to_delete:
        return None
    
    # 데이터가 있으면 삭제
    db.delete(generation_to_delete)
    db.commit()
    
    return True


##################################################
# 사용자 인물&동물 모델 관리
##################################################
# C
def create_user_model(db: Session, user_model: models.UserModelCreate):
    """새로운 사용자 모델(파일 경로)을 DB에 저장합니다."""
    db_model = models.UserModel.from_orm(user_model)
    db.add(db_model)
    print(f"✅ [CRUD] 2. DB에 모델 추가 완료. 커밋 직전...")
    db.commit()
    print(f"✅ [CRUD] 3. DB 커밋 성공!")
    db.refresh(db_model)
    return db_model

# R
def get_all_user_models(db: Session):
    """사용자가 업로드한 모든 모델 목록을 조회합니다."""
    return db.exec(select(models.UserModel)).all()

def get_user_model_by_id(db: Session, model_id: int):
    """ID를 기준으로 특정 사용자 모델 하나를 조회합니다."""
    return db.get(models.UserModel, model_id)

# U
def update_user_model_alias(db: Session, model_id: int, user_model_update: models.UserModelUpdate):
    """ID를 기준으로 특정 사용자 모델의 별명을 수정합니다."""
    db_model = get_user_model_by_id(db, model_id=model_id)
    
    if not db_model:
        return None을
    
    if not db_model.is_deletable:
        return "DEFAULT_MODEL_IS_NOT_DELETABLE"
    
    db_model.alias = user_model_update.alias
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    
    return db_model

# D
def delete_user_model(db: Session, model_id: int):
    """ID를 기준으로 특정 사용자 모델을 DB와 서버 폴더에서 모두 삭제합니다."""
    model_to_delete = get_user_model_by_id(db, model_id=model_id)
    
    if not model_to_delete:
        return None
    
    file_path = model_to_delete.file_path
    
    db.delete(model_to_delete)
    db.commit()
    
    if os.path.exists(file_path):
        os.remove(file_path)
        
    return True





# ##################################################
# # 회원가입 기능 추가 시
# # 사용자 이름으로 DB에서 사용자 정보 조회
# def get_user_by_username(db: Session, username: str):
#     statement = select(models.User).where(models.User.username == username)
#     user = db.exec(statement).first()
#     return user

# # 새로운 사용자 정보를 DB에 생성
# def create_user(db: Session, user: models.UserCreate):
#     # 입력받은 비밀번호를 해시값으로 변환
#     hashed_password = hashing.Hasher.get_password_hash(user.password)
    
#     # DB에 저장할 User 객체 생성
#     db_user = models.User(username=user.username, hashed_password=hashed_password)
    
#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user) # DB에 저장된 최신 정보로 객체를 새로고침
#     return db_user