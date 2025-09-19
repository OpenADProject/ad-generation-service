from sqlmodel import SQLModel, Field, Column, Text
from typing import Optional
from datetime import datetime


##################################################
# 사용자 콘텐츠 생성 결과물 관리
##################################################
# 공통 모델
class GenerationBase(SQLModel):
    input_image_path: Optional[str] = Field(default=None)
    input_text: Optional[str] = Field(default=None)
    output_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    output_image_path: Optional[str] = Field(default=None)

# DB 정의
class Generation(GenerationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

# 수신
class GenerationCreate(GenerationBase):
    pass

# 송신
class GenerationResponse(GenerationBase):
    id: int
    created_at: datetime

# 응답
class Message(SQLModel):
    ok: bool
    message: str


##################################################
# 사용자 인물&동물 모델 관리
##################################################
# 공통 모델
class UserModelBase(SQLModel):
    # 파일 경로 저장할 필드
    file_path: str
    alias: str

# DB 정의
class UserModel(UserModelBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    is_deletable: bool = Field(default=True) # 삭제 가능 여부(사용자에게 미노출)

# 수신
class UserModelCreate(UserModelBase):
    pass

# 수정
class UserModelUpdate(SQLModel):
    alias: str # 별명만 받음

# 송신
class UserModelResponse(UserModelBase):
    id: int




# ##################################################
# # 회원가입 기능 추가 시
# # 여러 모델에서 공통으로 사용할 필드
# class UserBase(SQLModel):
#     username: str

# # DB 테이블을 나타내는 모델 (table=True)
# class User(UserBase, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     hashed_password: str

# # 회원가입 API 요청 시 받을 데이터 형식
# class UserCreate(UserBase):
#     password: str

# # API가 사용자 정보를 응답할 때 보낼 데이터 형식 (비밀번호 제외)
# class UserResponse(UserBase):
#     id: int