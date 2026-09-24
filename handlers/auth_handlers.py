# Authentication endpoint handlers.
from dotenv import load_dotenv
from pydantic import ValidationError
from sqlalchemy import select
import tornado.web

from base_handler import BaseHandler
from models import User
from schemas import LoginSchema, RegisterSchema, UserResponse
from security import create_access_token, hash_password, verify_password

load_dotenv('.env_10c6229a-2c2d-44bf-a722-7f4465657ae8', override=True)


class RegisterHandler(BaseHandler):
    async def post(self) -> None:
        try:
            payload = RegisterSchema.model_validate(self.json_body())
        except ValidationError as exc:
            raise tornado.web.HTTPError(422, reason=str(exc)) from exc
        exists = (await self.db.execute(select(User).where(User.email == str(payload.email)))).scalar_one_or_none()
        if exists:
            raise tornado.web.HTTPError(409, reason='Email is already registered')
        user = User(email=str(payload.email), password_hash=hash_password(payload.password))
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        self.write_json({'user': UserResponse.model_validate(user).model_dump(mode='json'), 'access_token': create_access_token(user.id), 'token_type': 'bearer'}, 201)


class LoginHandler(BaseHandler):
    async def post(self) -> None:
        try:
            payload = LoginSchema.model_validate(self.json_body())
        except ValidationError as exc:
            raise tornado.web.HTTPError(422, reason=str(exc)) from exc
        user = (await self.db.execute(select(User).where(User.email == str(payload.email)))).scalar_one_or_none()
        if user is None or not verify_password(payload.password, user.password_hash):
            raise tornado.web.HTTPError(401, reason='Invalid email or password')
        self.write_json({'access_token': create_access_token(user.id), 'token_type': 'bearer'})


class MeHandler(BaseHandler):
    requires_auth = True

    async def get(self) -> None:
        self.write_json(UserResponse.model_validate(self.current_user).model_dump(mode='json'))
