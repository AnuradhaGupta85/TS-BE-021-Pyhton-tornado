# In-process authentication endpoint tests.
import json
import time

from dotenv import load_dotenv
from tornado.testing import AsyncHTTPTestCase

from database import engine
from main import make_app
from seed import seed

load_dotenv('.env_10c6229a-2c2d-44bf-a722-7f4465657ae8', override=True)


class AuthTest(AsyncHTTPTestCase):
    def get_app(self):
        return make_app()

    def setUp(self):
        super().setUp()
        self.io_loop.run_sync(seed)
        self.email = f'auth-{time.time_ns()}@example.com'
        self.password = 'SecurePass123!'

    def tearDown(self):
        self.io_loop.run_sync(engine.dispose)
        super().tearDown()

    def request(self, path, method='GET', payload=None, headers=None):
        headers = headers or {}
        body = None if payload is None else json.dumps(payload)
        if body is not None:
            headers['Content-Type'] = 'application/json'
        return self.fetch(path, method=method, body=body, headers=headers)

    def test_register_login_me_and_invalid_token(self):
        register = self.request('/api/v1/auth/register', 'POST', {'email': self.email, 'password': self.password})
        assert register.code == 201
        token = json.loads(register.body)['access_token']
        login = self.request('/api/v1/auth/login', 'POST', {'email': self.email, 'password': self.password})
        assert login.code == 200
        me = self.request('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
        assert me.code == 200
        rejected = self.request('/api/v1/auth/me', headers={'Authorization': 'Bearer invalid'})
        assert rejected.code == 401
