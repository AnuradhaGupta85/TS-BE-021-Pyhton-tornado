# Personal Expense Tracker — Tornado

A JWT-protected REST API for tracking personal income and expenses. Users manage their own transactions and custom categories while using shared predefined categories.

## Setup

1. Create and activate a Python 3.13 virtual environment.
2. Copy `.env.example` values into `.env_10c6229a-2c2d-44bf-a722-7f4465657ae8` if needed.
3. Install dependencies: `pip install -r requirements.txt`.
4. Initialize tables and predefined categories: `python3 seed.py`.
5. Run: `PORT=21435 bash start.sh`.

The verified fallback MySQL database is `gen_226c439ab41f`. The API uses port `21435` locally.

## Environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | MySQL aiomysql connection URL |
| `SECRET_KEY` | JWT signing secret |
| `TOKEN_EXPIRE_MINUTES` | JWT lifetime; default 30 |
| `PORT` | Local server port; default 21435 |

## Endpoints

| Method | Path | Auth | Description |
|---|---|---:|---|
| GET | `/health` | No | Service health check |
| POST | `/api/v1/auth/register` | No | Register user and return JWT |
| POST | `/api/v1/auth/login` | No | Log in and return JWT |
| GET | `/api/v1/auth/me` | Yes | Current user profile |
| GET/POST | `/api/v1/categories` | Yes | List available categories / create custom category |
| DELETE | `/api/v1/categories/{id}` | Yes | Delete an unused owned custom category |
| GET/POST | `/api/v1/transactions` | Yes | List/filter/sort transactions / create transaction |
| GET/PUT/DELETE | `/api/v1/transactions/{id}` | Yes | Retrieve, update, or delete owned transaction |
| GET | `/api/v1/summary/monthly?year=YYYY&month=MM` | Yes | Income, expenses, balance, expense category totals |

Transaction listing supports `search`, `category_id`, `type`, `start_date`, `end_date`, `sort_by` (`date`, `amount`, `category`), `order`, `limit`, and `offset`.

## Tests

Run `pytest -v --tb=short`. Tests use Tornado's in-process `AsyncHTTPTestCase` and initialize the schema automatically.

## Docker

Run `docker compose up --build`. The container serves internally on port 8000 and maps host port 21435. The compose MySQL image is pinned to `mysql:8.4.3`.

## Project tree

```text
├── handlers/                 # Auth, category, transaction, summary handlers
├── tests/                    # In-process API tests
├── database.py               # Async SQLAlchemy engine/session
├── models.py                 # User, Category, Transaction ORM models
├── schemas.py                # Pydantic validation schemas
├── security.py / auth.py     # Password/JWT and request auth helpers
├── main.py                   # Application and routes
├── seed.py                   # Schema and predefined category initialization
├── start.sh / start.bat      # Local launch scripts
└── docker-compose.yml        # App and MySQL services
```
