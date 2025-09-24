# src/backend/auth_utils.py
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt


##################################################
# 설정
##################################################
# bcrypt 방식으로 암호화 진행
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 생성에 사용할 시크릿 키
SECRET_KEY = "open-ad-project-secret-key"

# 토큰 서명 알고리즘
ALGORITHM = "HS256"

# 토큰 유효시간
ACCESS_TOKEN_EXPIRE_MINUTES = 60


##################################################
# 비밀번호 관리
##################################################
# 암호화 및 검증
class Hasher:
    # 사용자 입력 비밀번호와 DB 비밀번호 해시값이 일치하는지 확인
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        # 일치하면 True, 아니면 False를 반환
        return pwd_context.verify(plain_password, hashed_password)

    # 회원가입 시 사용자가 입력한 비밀번호를 해싱
    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

# JWT 생성 함수
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    # 토큰에 담을 정보 복사
    to_encode = data.copy()

    # 토큰 만료시간 설정
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 복사한 정보에 만료 시간 추가
    to_encode.update({"exp": expire})

    # JWT 토큰 생성
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt