# Request authentication helper for JWT-protected handlers.
import tornado.web
from sqlalchemy import select

from database import get_session
from models import User
from security import decode_access_token


async def get_current_user(handler: tornado.web.RequestHandler) -> User:
    """Load the user identified by a Bearer JWT or raise a uniform 401 error."""
    authorization = handler.request.headers.get('Authorization', '')
    if not authorization.startswith('Bearer '):
        raise tornado.web.HTTPError(401, reason='Missing or invalid Authorization header')
    try:
        user_id = decode_access_token(authorization[7:])
    except Exception as exc:
        raise tornado.web.HTTPError(401, reason='Invalid or expired access token') from exc

    session = getattr(handler, 'db', None)
    if session is not None:
        user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    else:
        async with get_session() as db:
            user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise tornado.web.HTTPError(401, reason='User no longer exists')
    return user
