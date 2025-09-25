# src/backend/crud.py
import os
from sqlmodel import Session, select
from . import models, auth_utils


##################################################
# 사용자 콘텐츠 생성 결과물 관리
##################################################
# C
# def create_generation(db: Session, generation: models.GenerationCreate, user_id: int): # 🟡 수정 중
def create_generation(
    db: Session, 
    generation: models.GenerationCreate, 
    user_id: int
):
    """
    API로부터 받은 GenerationCreate 데이터를 DB에 저장할 Generation 객체로 변환하고,
    DB에 추가(add), 저장(commit), 새로고침(refresh)합니다.
    """
    db_generation = models.Generation.from_orm(generation)
    db_generation.owner_id = user_id # 🟡 수정 중
    db.add(db_generation)
    db.commit()
    db.refresh(db_generation)
    return db_generation

# R
def get_generation_by_id(
    db: Session, 
    generation_id: int, 
    user_id: int
):
    """ID를 기준으로 특정 생성 이력 하나를 조회합니다."""
    return db.get(models.Generation, generation_id)

# def get_generations_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100): # 🟡 수정 중
def get_generations(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100
):
    """
    모든 생성 이력을 조회하되, pagination(페이지네이션)을 적용합니다.
    skip: 몇 개의 데이터를 건너뛸지
    limit: 몇 개의 데이터를 가져올지
    """
    statement = select(models.Generation).order_by(models.Generation.id.desc()).offset(skip).limit(limit)
    results = db.exec(statement).all()
    return results

# D
def delete_generation(
    db: Session, 
    generation_id: int, 
    user_id: int
):
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
# def create_user_model(db: Session, user_model: models.UserModelCreate, user_id: int): # 🟡 수정 중
def create_user_model(
    db: Session, 
    user_model: models.UserModelCreate, 
    user_id: int
):
    """새로운 사용자 모델 이미지를 DB에 저장합니다."""
    db_model = models.UserModel.from_orm(user_model)
    db_model.owner_id = user_id # 🟡 수정 중
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model

# R
# def get_all_user_models(db: Session, user_id: int): # 🟡 수정 중
def get_all_user_models(
    db: Session, 
    user_id: int
):
    """사용자가 업로드한 모든 모델 목록을 조회합니다."""
    return db.exec(select(models.UserModel)).all()

def get_user_model_by_id(
    db: Session, 
    model_id: int, 
    user_id: int
):
    """ID를 기준으로 특정 사용자 모델 하나를 조회합니다."""
    return db.get(models.UserModel, model_id)

# U
def update_user_model_alias(
    db: Session, 
    model_id: int, 
    user_model_update: models.UserModelUpdate, 
    user_id: int
):
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
def delete_user_model(
    db: Session, 
    model_id: int, 
    user_id: int
):
    """ID를 기준으로 특정 사용자 모델을 DB와 서버 폴더에서 모두 삭제합니다."""
    model_to_delete = get_user_model_by_id(db, model_id=model_id)
    
    if not model_to_delete:
        return None
    
    db.delete(model_to_delete)
    db.commit()
        
    return True


##################################################
# 사용자 계정 관리
##################################################
# C
def create_user(
    db: Session, 
    user: models.UserCreate
):
    """새로운 사용자를 생성합니다."""
    hashed_password = auth_utils.Hasher.get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# R
def get_user_by_id(
    db: Session, 
    user_id: int
):
    """ID로 특정 사용자를 조회합니다."""
    return db.get(models.User, user_id)

def get_user_by_username(
    db: Session, 
    username: str
):
    """사용자 이름으로 특정 사용자를 조회합니다."""
    statement = select(models.User).where(models.User.username == username)
    return db.exec(statement).first()

def get_all_users(
    db: Session
):
    """모든 사용자 목록을 조회합니다."""
    return db.exec(select(models.User)).all()

# U
def update_user_password(
    db: Session, 
    user_id: int, 
    new_password: str
):
    """ID로 사용자를 찾아 새 비밀번호로 변경합니다."""
    db_user = db.get(models.User, user_id)
    if db_user:
        db_user.hashed_password = auth_utils.Hasher.get_password_hash(new_password)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    return db_user

# D
def delete_user(
    db: Session, 
    user_id: int
):
    """ID로 특정 사용자를 삭제합니다."""
    user_to_delete = db.get(models.User, user_id)
    if not user_to_delete:
        return None
    db.delete(user_to_delete)
    db.commit()
    return True