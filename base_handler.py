# Shared Tornado handler behavior including DB lifecycle and JSON errors.
import json
import os

import tornado.ioloop
import tornado.web
from dotenv import load_dotenv

from auth import get_current_user as load_current_user
from database import SessionLocal

load_dotenv('.env_10c6229a-2c2d-44bf-a722-7f4465657ae8', override=True)


class BaseHandler(tornado.web.RequestHandler):
    """Base handler providing per-request sessions, CORS, and JSON errors."""

    requires_auth = False

    def set_default_headers(self) -> None:
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.set_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')

    def options(self, *args: str, **kwargs: str) -> None:
        self.set_status(204)
        self.finish()

    async def prepare(self) -> None:
        self.db = SessionLocal()
        self._current_user = None
        if self.requires_auth:
            self._current_user = await load_current_user(self)

    def get_current_user(self):
        return getattr(self, '_current_user', None)

    def on_finish(self) -> None:
        session = getattr(self, 'db', None)
        if session is not None:
            tornado.ioloop.IOLoop.current().spawn_callback(session.close)

    def write_error(self, status_code: int, **kwargs: object) -> None:
        reason = getattr(kwargs.get('exc_info', (None, None, None))[1], 'reason', None)
        self.set_header('Content-Type', 'application/json')
        self.finish(json.dumps({'detail': reason or self._reason}))

    def write_json(self, body: object, status: int = 200) -> None:
        self.set_status(status)
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(body, default=str))

    @staticmethod
    def validation_error_reason(error: object) -> str:
        """Return a single-line validation message safe for HTTP reason headers."""
        errors = getattr(error, 'errors', lambda: [])()
        if not errors:
            return 'Invalid request data'
        first_error = errors[0]
        location = '.'.join(str(part) for part in first_error.get('loc', ()))
        message = ' '.join(str(first_error.get('msg', 'Invalid value')).splitlines())
        return f'{location}: {message}' if location else message

    def json_body(self) -> dict:
        try:
            data = json.loads(self.request.body or b'{}')
        except json.JSONDecodeError as exc:
            raise tornado.web.HTTPError(400, reason='Invalid JSON') from exc
        if not isinstance(data, dict):
            raise tornado.web.HTTPError(400, reason='JSON body must be an object')
        return data

    def pagination(self) -> tuple[int, int]:
        try:
            limit = int(self.get_query_argument('limit', '20'))
            offset = int(self.get_query_argument('offset', '0'))
        except ValueError as exc:
            raise tornado.web.HTTPError(400, reason='limit and offset must be integers') from exc
        if offset < 0:
            raise tornado.web.HTTPError(400, reason='offset must be non-negative')
        return max(1, min(limit, 100)), offset
