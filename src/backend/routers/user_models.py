from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlmodel import Session
from typing import List
import shutil
import uuid
import os
from .. import crud, models
from ..database import get_session


##################################################
# 모델 이미지를 관리하는 API
##################################################
# 설정
router = APIRouter(prefix="/user-models", tags=["User Models"])
UPLOAD_DIRECTORY = "./src/backend/user_models"

# C
@router.post("/", response_model=models.UserModelResponse)
def create_user_model(
    alias: str = Form(...), 
    file: UploadFile = File(...), 
    db: Session = Depends(get_session)
):
    # 파일 이름 랜덤 생성
    unique_id = uuid.uuid4()
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{unique_id}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)

    # 서버 폴더에 저장
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # DB에 파일 경로 저장
    db_model = models.UserModelCreate(file_path=file_path, alias=alias)
    created_model = crud.create_user_model(db=db, user_model=db_model)
    
    return created_model

# R
@router.get("/", response_model=List[models.UserModelResponse])
def read_all_user_models(db: Session = Depends(get_session)):
    return crud.get_all_user_models(db=db)

# U
@router.patch("/{model_id}", response_model=models.UserModelResponse)
def update_user_model_alias_by_id(
    model_id: int, 
    user_model_update: models.UserModelUpdate, 
    db: Session = Depends(get_session)
):
    updated_model = crud.update_user_model_alias(
        db, model_id=model_id, user_model_update=user_model_update
    )
    
    if updated_model is None:
        raise HTTPException(status_code=404, detail="해당 ID의 모델을 찾을 수 없습니다.")
    
    if updated_model == "DEFAULT_MODEL_IS_DELETABLE":
        raise HTTPException(status_code=403, detail="기본 모델은 수정할 수 없습니다.")

    return updated_model

# D
@router.delete("/{model_id}", response_model=models.Message)
def delete_single_user_model(model_id: int, db: Session = Depends(get_session)):
    result = crud.delete_user_model(db, model_id=model_id)
    if not result:
        raise HTTPException(status_code=404, detail="해당 ID의 모델을 찾을 수 없습니다.")
    return {"ok": True, "message": "모델이 삭제되었습니다."}