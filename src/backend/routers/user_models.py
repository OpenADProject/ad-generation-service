# src/backend/routers/user_models.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlmodel import Session
from typing import List
import base64
from .. import crud, models
from ..database import get_session
from .auth import get_current_user


"""
사용자가 업로드한 커스텀 모델(UserModel)을 관리하는 API 라우터 파일입니다.
사용자 모델의 CRUD 엔드포인트를 정의합니다.
"""


##################################################
# 설정
##################################################
# 라우터
router = APIRouter(prefix="/user-models", tags=["User Models"])


##################################################
# 모델 이미지를 관리하는 API
##################################################
# C
@router.post("/", response_model=models.UserModelResponse)
async def create_user_model(
    alias: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    """
    새로운 사용자 모델을 생성하고 DB에 저장함.
    이미지 파일은 Base64 데이터 URL 형식으로 인코딩하여 저장함.
    """
    # 이미지를 바이트로 읽어옴
    image_bytes = await file.read()
    # Base64 텍스트로 인코딩
    base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
    # Data URL 형식으로 변환
    data_url = f"data:{file.content_type};base64,{base64_encoded}"
    # 데이터와 별명 저장
    db_model = models.UserModelCreate(file_path=data_url, alias=alias)

    return crud.create_user_model(db=db, user_model=db_model, user_id=current_user.id)

# R
@router.get("/", response_model=List[models.UserModelResponse])
def read_all_user_models(
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    """
    현재 로그인된 사용자의 모델과 공용 모델(admin 소유) 목록을 조회함.
    """
    return crud.get_all_user_models(db=db, user_id=current_user.id)

# U
@router.patch("/{model_id}", response_model=models.UserModelResponse)
def update_user_model_alias_by_id(
    model_id: int, 
    user_model_update: models.UserModelUpdate, 
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    """
    ID를 기준으로 특정 사용자 모델의 별명을 수정함. (소유권 확인)
    """
    updated_model = crud.update_user_model_alias(
        db, model_id=model_id, user_id=current_user.id, user_model_update=user_model_update
    )
    
    if updated_model is None:
        raise HTTPException(status_code=404, detail="해당 모델을 찾을 수 없거나 수정 권한이 없습니다.")
    
    if updated_model == "DEFAULT_MODEL_IS_NOT_DELETABLE":
        raise HTTPException(status_code=403, detail="기본 모델은 수정할 수 없습니다.")

    return updated_model

# D
@router.delete("/{model_id}", response_model=models.Message)
def delete_single_user_model(
    model_id: int, 
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    """
    ID를 기준으로 특정 사용자 모델을 삭제함. (소유권 확인)
    """
    result = crud.delete_user_model(db, model_id=model_id, user_id=current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="해당 모델을 찾을 수 없거나 삭제 권한이 없습니다.")
    return {"ok": True, "message": "모델이 삭제되었습니다."}