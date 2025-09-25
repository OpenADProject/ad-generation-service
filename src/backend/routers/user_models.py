# src/backend/routers/user_models.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlmodel import Session
from typing import List
import base64
from .. import crud, models
from ..database import get_session
from .auth import get_current_user


##################################################
# 설정
##################################################
# 라우터
router = APIRouter(prefix="/user-models", tags=["User Models"])


##################################################
# 모델 이미지를 관리하는 API
##################################################
# C
# current_user: models.User = Depends(get_current_user) # 🟡 수정 중
@router.post("/", response_model=models.UserModelResponse)
async def create_user_model(
    alias: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    # 이미지를 바이트로 읽어옴
    image_bytes = await file.read()
    # Base64 텍스트로 인코딩
    base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
    # Data URL 형식으로 변환
    data_url = f"data:{file.content_type};base64,{base64_encoded}"
    # 데이터와 별명 저장
    db_model = models.UserModelCreate(file_path=data_url, alias=alias)

    return crud.create_user_model(db=db, user_model=db_model, user_id=current_user.id)
    # return crud.create_user_model(db=db, user_model=db_model, user_id=current_user.id) 🟡 수정 중

# R
# current_user: models.User = Depends(get_current_user) # 🟡 수정 중
@router.get("/", response_model=List[models.UserModelResponse])
def read_all_user_models(
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_all_user_models(db=db, user_id=current_user.id) # (db=db, user_id=current_user.id) 🟡 수정 중

# U 🟡 수정 중
@router.patch("/{model_id}", response_model=models.UserModelResponse)
def update_user_model_alias_by_id(
    model_id: int, 
    user_model_update: models.UserModelUpdate, 
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    updated_model = crud.update_user_model_alias(
        db, model_id=model_id, user_model_update=user_model_update
    )
    
    if updated_model is None:
        raise HTTPException(status_code=404, detail="해당 ID의 모델을 찾을 수 없습니다.")
    
    if updated_model == "DEFAULT_MODEL_IS_NOT_DELETABLE":
        raise HTTPException(status_code=403, detail="기본 모델은 수정할 수 없습니다.")

    return updated_model

# D 🟡 수정 중
@router.delete("/{model_id}", response_model=models.Message)
def delete_single_user_model(
    model_id: int, 
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    result = crud.delete_user_model(db, model_id=model_id)
    if not result:
        raise HTTPException(status_code=404, detail="해당 ID의 모델을 찾을 수 없습니다.")
    return {"ok": True, "message": "모델이 삭제되었습니다."}

