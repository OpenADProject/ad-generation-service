# src/backend/auth_utils.py
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt


"""
사용자 인증과 관련된 보안 유틸리티 함수들을 모아놓은 파일입니다.
비밀번호 해싱(암호화), JWT 토큰 생성 및 검증 로직을 포함하며,
주로 API 라우터에서 사용자 인증을 처리할 때 사용됩니다.
"""


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
class Hasher:
    """
    비밀번호 해싱과 검증을 처리하는 staticmethod를 관리하는 클래스.
    """
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        사용자가 입력한 일반 비밀번호와 DB에 저장된 해시 비밀번호가 일치하는지 확인함.

        Args:
            plain_password (str): 사용자가 로그인 시 입력한 비밀번호 원문.
            hashed_password (str): DB에 저장되어 있는 암호화된 비밀번호.

        Returns:
            bool: 비밀번호가 일치하면 True, 일치하지 않으면 False.
        """
        # 해싱값이 일치하면 True 아니면 False를 반환
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        일반 비밀번호를 bcrypt 해시값으로 변환(암호화)함.

        Args:
            password (str): 암호화할 비밀번호 원문.

        Returns:
            str: 암호화된 비밀번호 해시값.
        """
        # 비밀번호를 암호화(해싱)하고 결과를 반환
        return pwd_context.hash(password)


##################################################
# JWT 토큰 관리
##################################################
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    JWT Access Token을 생성함.

    Args:
        data (dict): 토큰의 payload에 담을 데이터 (예: {"sub": "username"}).
        expires_delta (Optional[timedelta]): 토큰의 만료 시간을 지정. 기본값은 60분.

    Returns:
        str: 생성된 JWT 토큰 문자열.
    """
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