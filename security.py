# JWT token and password security helpers.
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv('.env_10c6229a-2c2d-44bf-a722-7f4465657ae8', override=True)

SECRET_KEY = os.getenv('SECRET_KEY', 'development-only-change-this-secret')
ALGORITHM = 'HS256'
TOKEN_EXPIRE_MINUTES = int(os.getenv('TOKEN_EXPIRE_MINUTES', '30'))
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode({'sub': str(user_id), 'exp': expires_at}, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    subject = payload.get('sub')
    if not subject:
        raise jwt.InvalidTokenError('Token has no subject')
    return int(subject)
