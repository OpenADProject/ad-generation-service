from sqlmodel import SQLModel, Field, Column, Text
from typing import Optional
from datetime import datetime

# 생성/조회/응답에 공통으로 사용할 모델
class GenerationBase(SQLModel):
    input_image_path: Optional[str] = Field(default=None)
    input_text: Optional[str] = Field(default=None)
    output_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    output_image_path: Optional[str] = Field(default=None)

# DB 테이블 구조 정의
class Generation(GenerationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

# 생성 이력 수신
class GenerationCreate(GenerationBase):
    pass

# 생성 이력 송신
class GenerationResponse(GenerationBase):
    id: int
    created_at: datetime

# 성공/실패 응답 모델
class Message(SQLModel):
    ok: bool
    message: str





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