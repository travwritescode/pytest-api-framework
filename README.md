# pytest-api-framework

Python API test suite for [flowstate-api](https://github.com/travwritescode/flowstate-api) using pytest, httpx, and Allure reporting.

Tests run against the FastAPI app in-process via ASGI transport with an isolated SQLite in-memory database — no running server required.

## Coverage

46 tests across 5 modules. See [TEST_CASES.md](TEST_CASES.md) for the full list with descriptions.

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

## DB isolation

Each test gets its own throwaway SQLite database. There is no shared state between tests and no cleanup scripts to maintain.

| Decision | Reason |
|---|---|
| `sqlite:///:memory:` | Zero-cost, no disk I/O, automatically gone when the connection closes |
| `StaticPool` | Forces SQLAlchemy to reuse one connection for the engine's lifetime — without this, the httpx ASGI transport and the test session can land on different connections, making the in-memory DB appear empty to one of them |
| `PRAGMA foreign_keys=ON` | SQLite disables FK constraints by default; this makes FK violations visible during tests |
| `Base.metadata.drop_all` on teardown | Wipes the schema after every test so no rows can bleed across |

The full fixture dependency chain is:

```
db_session
  └── client                   overrides get_db with the test session
        ├── registered_user    POST /auth/register — unique email per test
        │     └── auth_headers POST /auth/login — returns Bearer token
        │           └── seeded_task  POST /tasks via factories.create_task
        └── second_user        second isolated user for cross-user tests
              └── other_auth_headers
```

## Allure Report

Each test is annotated with `@allure.feature`, `@allure.story`, `@allure.severity`, and `@allure.description`. Running the suite produces raw results in `allure-results/`.

**Generate and open the HTML report**

Requires the [Allure CLI](https://allurereport.org/docs/install/) (needs Java):

```bash
# Install CLI (one-time)
npm install -g allure-commandline

# Generate report from latest results
allure generate allure-results -o allure-report --clean

# Open in browser
allure open allure-report
```

For a GitHub-readable summary without running the CLI, see [TEST_CASES.md](TEST_CASES.md).
