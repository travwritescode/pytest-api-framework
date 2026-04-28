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
