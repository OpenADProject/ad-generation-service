from sqlmodel import Session, select
from . import models


# C: 새로운 생성 이력을 DB에 저장
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

# R: 생성 이력을 DB에서 조회
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

# D: 특정 생성 이력을 DB에서 삭제
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