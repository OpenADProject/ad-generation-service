# # src/backend/routers/auth.py

# from fastapi import APIRouter, Depends, HTTPException
# from sqlmodel import Session
# import crud
# import models
# from database import get_session

# # API 라우터 생성
# router = APIRouter(
#     prefix="/auth", # 이 파일의 모든 API 경로는 '/auth'로 시작
#     tags=["Auth"]   # FastAPI 문서에서 'Auth' 그룹으로 묶어서 보여줌
# )

# @router.post("/signup", response_model=models.UserResponse)
# def signup_user(user: models.UserCreate, db: Session = Depends(get_session)):
#     # crud에 있는 함수를 호출해서 DB에서 사용자 조회
#     db_user = crud.get_user_by_username(db, username=user.username)
#     if db_user:
#         raise HTTPException(status_code=400, detail="이미 사용 중인 아이디입니다.")
    
#     # crud에 있는 함수를 호출해서 DB에 사용자 생성
#     return crud.create_user(db=db, user=user)

# # (나중에 추가) 로그인 API
# # @router.post("/login")
# # def login_user(...):
# #     ...