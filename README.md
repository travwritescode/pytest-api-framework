# pytest-api-framework

Python API test suite for [flowstate-api](https://github.com/travwritescode/flowstate-api) using pytest, httpx, and Allure reporting.

Tests run against the FastAPI app in-process via ASGI transport with an isolated SQLite in-memory database — no running server required.

## Coverage

| Module | What it tests |
|---|---|
| `tests/test_auth.py` | Register, login, duplicate email, wrong password, inactive account |
| `tests/test_tasks_crud.py` | Full CRUD chain, partial update, response contract, soft delete |
| `tests/test_tasks_auth.py` | 401 / 403 boundaries, cross-user isolation |
| `tests/test_tasks_filter.py` | `?status`, `?priority`, combined filters, ordering |
| `tests/test_validation.py` | 422 validation cases across all endpoints |

## Setup

**1. Clone both repos as siblings**

```
projects/
├── flowstate-api/
└── pytest-api-framework/
```

`conftest.py` adds `../flowstate-api` to `sys.path` automatically — no install step needed.

**2. Install dependencies**

```bash
pip install -r requirements.txt
pip install -r ../flowstate-api/requirements.txt
```

**3. Run the tests**

```bash
pytest
```

**4. View the Allure report**

```bash
allure serve allure-results
```
