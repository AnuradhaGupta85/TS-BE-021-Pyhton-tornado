# Authentication and account-management endpoint handlers.
import hashlib
import os
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from dotenv import load_dotenv
from pydantic import ValidationError
from sqlalchemy import select
import tornado.web

from base_handler import BaseHandler
from models import PasswordResetToken, RevokedToken, User
from schemas import (ChangePasswordSchema, ForgotPasswordSchema, LoginSchema,
                     ProfileUpdateSchema, RegisterSchema, ResetPasswordSchema,
                     UserResponse)
from security import (create_access_token, decode_access_token_payload,
                      hash_password, verify_password)

load_dotenv('.env_10c6229a-2c2d-44bf-a722-7f4465657ae8', override=True)


def send_password_reset_email(recipient: str, token: str) -> None:
    """Send reset instructions when SMTP is configured."""
    host, sender = os.getenv('SMTP_HOST'), os.getenv('SMTP_FROM')
    if not host or not sender:
        return
    reset_url = os.getenv('RESET_PASSWORD_URL', '').rstrip('/')
    link = f'{reset_url}?token={token}' if reset_url else token
    message = EmailMessage()
    message['Subject'], message['From'], message['To'] = 'Password reset request', sender, recipient
    message.set_content(f'Use this password reset link or token: {link}')
    with smtplib.SMTP(host, int(os.getenv('SMTP_PORT', '587'))) as client:
        if os.getenv('SMTP_STARTTLS', 'true').lower() == 'true':
            client.starttls()
        if os.getenv('SMTP_USERNAME'):
            client.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD', ''))
        client.send_message(message)


class RegisterHandler(BaseHandler):
    async def post(self) -> None:
        try:
            payload = RegisterSchema.model_validate(self.json_body())
        except ValidationError as exc:
            raise tornado.web.HTTPError(422, reason=self.validation_error_reason(exc)) from exc
        exists = (await self.db.execute(select(User).where(User.email == str(payload.email)))).scalar_one_or_none()
        if exists:
            raise tornado.web.HTTPError(409, reason='Email is already registered')
        user = User(email=str(payload.email), name=payload.name, password_hash=hash_password(payload.password))
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        self.write_json({'user': UserResponse.model_validate(user).model_dump(mode='json'), 'access_token': create_access_token(user.id), 'token_type': 'bearer'}, 201)


class LoginHandler(BaseHandler):
    async def post(self) -> None:
        try:
            payload = LoginSchema.model_validate(self.json_body())
        except ValidationError as exc:
            raise tornado.web.HTTPError(422, reason=self.validation_error_reason(exc)) from exc
        user = (await self.db.execute(select(User).where(User.email == str(payload.email)))).scalar_one_or_none()
        if user is None or not verify_password(payload.password, user.password_hash):
            raise tornado.web.HTTPError(401, reason='Invalid email or password')
        self.write_json({'access_token': create_access_token(user.id), 'token_type': 'bearer'})


class MeHandler(BaseHandler):
    requires_auth = True

    async def get(self) -> None:
        self.write_json(UserResponse.model_validate(self.current_user).model_dump(mode='json'))

    async def put(self) -> None:
        try:
            payload = ProfileUpdateSchema.model_validate(self.json_body())
        except ValidationError as exc:
            raise tornado.web.HTTPError(422, reason=self.validation_error_reason(exc)) from exc
        values = payload.model_dump(exclude_unset=True)
        email = values.get('email')
        if email and str(email) != self.current_user.email:
            existing = (await self.db.execute(select(User.id).where(User.email == str(email), User.id != self.current_user.id))).scalar_one_or_none()
            if existing is not None:
                raise tornado.web.HTTPError(409, reason='Email is already registered')
            self.current_user.email = str(email)
        if 'name' in values:
            self.current_user.name = values['name']
        await self.db.commit()
        await self.db.refresh(self.current_user)
        self.write_json(UserResponse.model_validate(self.current_user).model_dump(mode='json'))

    async def delete(self) -> None:
        await self.db.delete(self.current_user)
        await self.db.commit()
        self.set_status(204)
        self.finish()


class ChangePasswordHandler(BaseHandler):
    requires_auth = True

    async def put(self) -> None:
        try:
            payload = ChangePasswordSchema.model_validate(self.json_body())
        except ValidationError as exc:
            raise tornado.web.HTTPError(422, reason=self.validation_error_reason(exc)) from exc
        if not verify_password(payload.current_password, self.current_user.password_hash):
            raise tornado.web.HTTPError(401, reason='Current password is incorrect')
        self.current_user.password_hash = hash_password(payload.new_password)
        await self.db.commit()
        self.set_status(204)
        self.finish()


class ForgotPasswordHandler(BaseHandler):
    async def post(self) -> None:
        try:
            payload = ForgotPasswordSchema.model_validate(self.json_body())
        except ValidationError as exc:
            raise tornado.web.HTTPError(422, reason=self.validation_error_reason(exc)) from exc
        user = (await self.db.execute(select(User).where(User.email == str(payload.email)))).scalar_one_or_none()
        if user:
            token = secrets.token_urlsafe(32)
            self.db.add(PasswordResetToken(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id, expires_at=datetime.utcnow() + timedelta(hours=1)))
            await self.db.commit()
            try:
                send_password_reset_email(user.email, token)
            except (OSError, smtplib.SMTPException):
                pass
        self.write_json({'message': 'If the email is registered, password reset instructions have been sent.'})


class ResetPasswordHandler(BaseHandler):
    async def post(self) -> None:
        try:
            payload = ResetPasswordSchema.model_validate(self.json_body())
        except ValidationError as exc:
            raise tornado.web.HTTPError(422, reason=self.validation_error_reason(exc)) from exc
        reset = (await self.db.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == hashlib.sha256(payload.token.encode()).hexdigest()))).scalar_one_or_none()
        if reset is None or reset.used_at is not None or reset.expires_at < datetime.utcnow():
            raise tornado.web.HTTPError(400, reason='Reset token is invalid or expired')
        user = (await self.db.execute(select(User).where(User.id == reset.user_id))).scalar_one()
        user.password_hash, reset.used_at = hash_password(payload.new_password), datetime.utcnow()
        await self.db.commit()
        self.write_json({'message': 'Password has been reset successfully.'})


class LogoutHandler(BaseHandler):
    requires_auth = True

    async def post(self) -> None:
        payload = decode_access_token_payload(self.request.headers['Authorization'][7:])
        self.db.add(RevokedToken(jti=payload['jti'], user_id=self.current_user.id, expires_at=datetime.utcfromtimestamp(payload['exp'])))
        await self.db.commit()
        self.set_status(204)
        self.finish()
