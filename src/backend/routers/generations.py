# src/backend/routers/generations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from .. import crud, models
from ..database import get_session
from .auth import get_current_user


"""
사용자가 생성한 콘텐츠(Generation)의 이력을 관리하는 API 라우터 파일입니다.
생성 이력의 생성(Create), 조회(Read), 삭제(Delete)를 위한 엔드포인트를 정의합니다.
"""


##################################################
# 설정
##################################################
# 라우터
router = APIRouter(prefix="/generations", tags=["Generations"])


##################################################
# 사용자 생성 결과물을 관리하는 API
##################################################
# C
@router.post("/", response_model=models.GenerationResponse)
def create_new_generation(
    generation: models.GenerationCreate, 
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    """
    새로운 생성 이력을 생성하고 DB에 저장함.
    """
    return crud.create_generation(db=db, generation=generation, user_id=current_user.id)

# R
@router.get("/", response_model=List[models.GenerationResponse])
def read_all_generations(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)    
):
    """
    현재 로그인된 사용자의 모든 생성 이력 목록을 조회함.
    """
    generations = crud.get_generations_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return generations

# D
@router.delete("/{generation_id}", response_model=models.Message)
def delete_single_generation(
    generation_id: int, 
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    """
    ID를 기준으로 특정 생성 이력을 삭제함. (소유권 확인)
    """
    result = crud.delete_generation(db, generation_id=generation_id, user_id=current_user.id)
    if result is None:
        raise HTTPException(
            status_code=404, 
            detail="해당 생성 이력을 찾을 수 없거나 삭제 권한이 없습니다."
        )
    
    return {"ok": True, "message": "생성 이력이 삭제되었습니다."}