# In-process transaction, filtering, summary, and category endpoint tests.
import json
import time

from dotenv import load_dotenv
from tornado.testing import AsyncHTTPTestCase

from database import engine
from main import make_app
from seed import seed

load_dotenv('.env_10c6229a-2c2d-44bf-a722-7f4465657ae8', override=True)


class TransactionTest(AsyncHTTPTestCase):
    def get_app(self):
        return make_app()

    def setUp(self):
        super().setUp()
        self.io_loop.run_sync(seed)
        email = f'txn-{time.time_ns()}@example.com'
        response = self.fetch('/api/v1/auth/register', method='POST', body=json.dumps({'email': email, 'password': 'SecurePass123!'}), headers={'Content-Type': 'application/json'})
        self.headers = {'Authorization': f"Bearer {json.loads(response.body)['access_token']}", 'Content-Type': 'application/json'}

    def tearDown(self):
        self.io_loop.run_sync(engine.dispose)
        super().tearDown()

    def request(self, path, method='GET', payload=None):
        return self.fetch(path, method=method, body=None if payload is None else json.dumps(payload), headers=self.headers)

    def test_transaction_crud_filter_summary_and_category_rules(self):
        categories = self.request('/api/v1/categories')
        assert categories.code == 200
        category_id = json.loads(categories.body)['items'][0]['id']
        created_category = self.request('/api/v1/categories', 'POST', {'name': 'Test Custom'})
        assert created_category.code == 201
        custom_id = json.loads(created_category.body)['id']
        created = self.request('/api/v1/transactions', 'POST', {'amount': '42.50', 'type': 'Expense', 'category_id': category_id, 'date': '2025-01-15', 'description': 'Coffee supplies'})
        assert created.code == 201
        transaction_id = json.loads(created.body)['id']
        listed = self.request('/api/v1/transactions?search=Coffee&type=Expense&sort_by=amount&order=asc&limit=20&offset=0')
        assert listed.code == 200 and json.loads(listed.body)['total'] >= 1
        retrieved = self.request(f'/api/v1/transactions/{transaction_id}')
        assert retrieved.code == 200
        updated = self.request(f'/api/v1/transactions/{transaction_id}', 'PUT', {'amount': '50.00', 'category_id': custom_id})
        assert updated.code == 200
        blocked_delete = self.request(f'/api/v1/categories/{custom_id}', 'DELETE')
        assert blocked_delete.code == 409
        summary = self.request('/api/v1/summary/monthly?year=2025&month=1')
        assert summary.code == 200 and json.loads(summary.body)['total_expenses'] == '50.00'
        deleted = self.request(f'/api/v1/transactions/{transaction_id}', 'DELETE')
        assert deleted.code == 204
        custom_deleted = self.request(f'/api/v1/categories/{custom_id}', 'DELETE')
        assert custom_deleted.code == 204
