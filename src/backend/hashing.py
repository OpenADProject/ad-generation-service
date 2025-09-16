# from passlib.context import CryptContext

# # 사용할 암호화 알고리즘(bcrypt) 설정
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# class Hasher:
#     # 입력된 비밀번호가 저장된 해시와 일치하는지 확인
#     @staticmethod
#     def verify_password(plain_password, hashed_password):
#         return pwd_context.verify(plain_password, hashed_password)

#     # 일반 비밀번호를 해시값으로 변환
#     @staticmethod
#     def get_password_hash(password):
#         return pwd_context.hash(password)