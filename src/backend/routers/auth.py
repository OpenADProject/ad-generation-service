# src/backend/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session
from typing import List
from jose import JWTError, jwt
from .. import crud, models, auth_utils
from ..database import get_session


##################################################
# 설정
##################################################
# 라우터
router = APIRouter(prefix="/auth")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


##################################################
# 사용자 계정 관리
##################################################
# 검증 함수
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_session)):
    """
    JWT 토큰을 검증하고, 유효하면 해당 사용자 정보를 DB에서 찾아 반환하는 함수.
    이 함수를 Depends로 사용하는 API는 모두 로그인이 필요하게 됨.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 시크릿 키를 사용해 토큰을 해독하고 payload(내용물)를 추출
        payload = jwt.decode(token, auth_utils.SECRET_KEY, algorithms=[auth_utils.ALGORITHM])
        username: str = payload.get("sub") # 토큰 내용물에서 사용자 이름(sub)을 꺼냄
        if username is None:
            raise credentials_exception
        token_data = models.TokenData(username=username)
    except JWTError:
        # 토큰 해독 과정에서 에러가 나면(예: 유효기간 만료, 형식 오류) 인증 실패 처리
        raise credentials_exception
    
    # 해독된 사용자 이름으로 DB에서 실제 사용자가 있는지 확인
    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    
    # 사용자가 있으면 사용자 정보를 반환
    return user


# 토큰 발급
@router.post("/login", response_model=models.Token, tags=["Auth (User)"])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_session)):
    """사용자 아이디와 비밀번호로 로그인하고, 성공 시 JWT 토큰을 발급."""
    user = crud.get_user_by_username(db, username=form_data.username)
    # 사용자가 없거나, 비밀번호가 틀리면 401 에러 발생
    if not user or not auth_utils.Hasher.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 로그인 성공 시, 사용자 이름을 내용(sub)으로 하는 access token 생성
    access_token = auth_utils.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# R
@router.get("/users/me", response_model=models.UserResponse, tags=["Auth (User)"])
def read_users_me(current_user: models.User = Depends(get_current_user)):
    """현재 로그인된 사용자의 정보를 반환. 토큰 인증 테스트용."""
    return current_user


##################################################
# 사용자 계정 관리 (관리자)
##################################################
# C
@router.post("/users/", response_model=models.UserResponse, tags=["Auth (Admin)"])
def create_new_user(user: models.UserCreate, db: Session = Depends(get_session), admin_user: models.User = Depends(get_current_user)):
    """새로운 사용자를 생성 (관리자 전용)."""
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

# R
@router.get("/users/", response_model=List[models.UserResponse], tags=["Auth (Admin)"])
def read_all_users(db: Session = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    """모든 사용자 목록을 조회 (관리자 전용)."""
    return crud.get_all_users(db=db)

@router.get("/users/{user_id}", response_model=models.UserResponse, tags=["Auth (Admin)"])
def read_user_by_id(user_id: int, db: Session = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    """ID로 특정 사용자를 조회 (관리자 전용)."""
    db_user = crud.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# U
@router.patch("/users/{user_id}/password", response_model=models.UserResponse, tags=["Auth (Admin)"])
def update_user_password_by_id(user_id: int, user_update: models.UserPasswordUpdate, db: Session = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    """ID로 특정 사용자의 비밀번호를 변경 (관리자 전용)."""
    db_user = crud.update_user_password(db, user_id=user_id, new_password=user_update.new_password)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# D
@router.delete("/users/{user_id}", response_model=models.Message, tags=["Auth (Admin)"])
def remove_user(user_id: int, db: Session = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    """ID로 특정 사용자를 삭제 (관리자 전용)."""
    result = crud.delete_user(db, user_id=user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "message": "User deleted successfully"}