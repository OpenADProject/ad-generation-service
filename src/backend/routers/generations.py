# src/backend/routers/generation.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from .. import crud, models
from ..database import get_session
from .auth import get_current_user


##################################################
# 설정
##################################################
# 라우터
router = APIRouter(prefix="/generations", tags=["Generations"])


##################################################
# 사용자 생성 결과물을 관리하는 API
##################################################
# C
# def create_new_generation(generation: models.GenerationCreate, db: Session = Depends(get_session), current_user: models.User = Depends(get_current_user)):  # 🟡 수정 중
@router.post("/", response_model=models.GenerationResponse)
def create_new_generation(
    generation: models.GenerationCreate, 
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    return crud.create_generation(db=db, generation=generation, user_id=current_user.id)
    # return crud.create_generation(db=db, generation=generation, user_id=current_user.id) 

# R
# , current_user: models.User = Depends(get_current_user)):  # 🟡 수정 중
@router.get("/", response_model=List[models.GenerationResponse])
def read_all_generations(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)    
):
    generations = crud.get_generations(db, user_id=current_user.id, skip=skip, limit=limit)
    # generations = crud.get_generations_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return generations

# D 🟡 수정 중
@router.delete("/{generation_id}", response_model=models.Message)
def delete_single_generation(
    generation_id: int, 
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    result = crud.delete_generation(db, generation_id=generation_id)
    if result is None:
        raise HTTPException(
            status_code=404, 
            detail=f"ID {generation_id}에 해당하는 생성 이력을 찾을 수 없습니다."
        )
    
    return {"ok": True, "message": f"ID {generation_id}번 생성 이력이 삭제되었습니다."}

