# src/backend/models.py
from sqlmodel import SQLModel, Field, Column, Text
from typing import Optional
from datetime import datetime


"""
데이터베이스 테이블 구조와 API 데이터 형식을 정의하는 모델들을 모아놓은 파일입니다.
SQLModel을 사용하여 Pydantic(API) & SQLAlchemy(DB) 모델을 한 번에 정의합니다.
"""


##################################################
# 사용자 콘텐츠 생성 결과물 관리
##################################################
# 공통 모델
class GenerationBase(SQLModel):
    """
    Generation 모델들의 공통 필드를 정의.
    """
    input_image_path: Optional[str] = Field(default=None)
    input_text: Optional[str] = Field(default=None)
    output_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    output_image_path: Optional[str] = Field(default=None)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")

# DB 정의
class Generation(GenerationBase, table=True):
    """
    generation DB 테이블에 해당하는 모델.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

# 수신
class GenerationCreate(GenerationBase):
    """
    새로운 생성 이력을 API로 생성할 때 사용하는 모델.
    """
    pass

# 송신
class GenerationResponse(GenerationBase):
    """
    생성 이력 정보를 API로 반환할 때 사용하는 모델.
    """
    id: int
    created_at: datetime


##################################################
# 사용자 인물&동물 모델 관리
##################################################
# 공통 모델
class UserModelBase(SQLModel):
    """
    UserModel 모델들의 공통 필드를 정의.
    """
    # 파일 경로 저장할 필드
    file_path: str = Field(sa_column=Column(Text))
    alias: str
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")

# DB 정의
class UserModel(UserModelBase, table=True):
    """
    usermodel DB 테이블에 해당하는 모델.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    is_deletable: bool = Field(default=True) # 삭제 가능 여부(사용자에게 미노출)

# 수신
class UserModelCreate(UserModelBase):
    """
    새로운 사용자 모델을 API로 생성할 때 사용하는 모델.
    """
    pass

# 수정
class UserModelUpdate(SQLModel):
    """
    사용자 모델의 별명을 API로 수정할 때 사용하는 모델.
    """
    alias: str # 별명만 받음

# 송신
class UserModelResponse(UserModelBase):
    """
    사용자 모델 정보를 API로 반환할 때 사용하는 모델.
    """
    id: int


##################################################
# 사용자 계정 관리
##################################################
# 공통 필드
class UserBase(SQLModel):
    """
    User 모델들의 공통 필드를 정의.
    """
    username: str

# DB 정의
class User(UserBase, table=True):
    """
    'user' DB 테이블에 해당하는 모델.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str

# 수신
class UserCreate(UserBase):
    """
    새로운 사용자를 API로 생성할 때 사용하는 모델.
    """
    password: str

# 송신 (비밀번호 제외)
class UserResponse(UserBase):
    """
    사용자 정보를 API로 반환할 때 사용하는 모델. (비밀번호 제외)
    """
    id: int

# 송신 (비밀번호 변경)
class UserPasswordUpdate(SQLModel):
    """
    사용자 비밀번호를 API로 변경할 때 사용하는 모델.
    """
    new_password: str


##################################################
# JWT 토큰 관리
##################################################
class Token(SQLModel):
    """
    로그인 성공 시 API가 반환하는 Access Token의 모델.
    """
    access_token: str
    token_type: str

class TokenData(SQLModel):
    """
    JWT 토큰의 payload(내용물)에 담기는 데이터의 모델.
    """
    username: Optional[str] = None


##################################################
# 공통 응답 메시지
##################################################
class Message(SQLModel):
    """
    삭제 성공 등 간단한 상태 메시지를 API로 반환할 때 사용하는 모델.
    """
    ok: bool
    message: str