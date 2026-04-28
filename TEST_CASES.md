# Test Cases

46 tests across 5 modules. Run `pytest` and open `allure-report/index.html` for the full interactive report.

---

## Auth — `tests/test_auth.py`

### Register

| Test | Severity | Description |
|------|----------|-------------|
| `test_register_returns_201_with_user_fields` | Critical | Registering with a valid email and password returns 201 with the user's id, email, is_active, and created_at. Verifies hashed_password is never exposed. |
| `test_register_duplicate_email_returns_409` | Normal | Attempting to register with an already-registered email returns 409 Conflict with a detail message indicating the account exists. |
| `test_register_invalid_email_returns_422` | Minor | A malformed email string (missing @ and domain) returns 422 — Pydantic's EmailStr rejects it before the database. |

### Login

| Test | Severity | Description |
|------|----------|-------------|
| `test_login_returns_bearer_token` | Critical | Valid credentials return 200 with a JWT access_token and token_type of 'bearer'. |
| `test_login_wrong_password_returns_401` | Critical | A correct email with the wrong password returns 401. The API gives the same response as for an unknown email to avoid account enumeration. |
| `test_login_unknown_email_returns_401` | Normal | An email that has never been registered returns 401. |
| `test_login_inactive_account_returns_403` | Critical | An account with is_active=False returns 403 'Account is inactive'. The flag is set directly in the DB to simulate administrative deactivation. |

---

## Tasks: Auth Boundaries — `tests/test_tasks_auth.py`

### Unauthenticated Access

| Test | Severity | Description |
|------|----------|-------------|
| `test_no_token_returns_401` | Critical | A request to GET /tasks with no Authorization header returns 401. All task endpoints are protected. |
| `test_malformed_token_returns_401` | Critical | A Bearer token that is not a valid JWT returns 401. The decode step rejects structurally invalid tokens. |
| `test_expired_token_returns_401` | Critical | A structurally valid JWT with an exp timestamp in the past returns 401. Token expiry is enforced. |

### Cross-User Access

| Test | Severity | Description |
|------|----------|-------------|
| `test_get_another_users_task_returns_403` | Critical | User B fetching a task owned by User A returns 403 'Access denied'. Valid authentication is not sufficient to access another user's data. |
| `test_update_another_users_task_returns_403` | Critical | User B updating a task owned by User A returns 403. Ownership is enforced on PUT. |
| `test_delete_another_users_task_returns_403` | Critical | User B deleting a task owned by User A returns 403. Ownership is enforced on DELETE. |
| `test_list_tasks_only_returns_own_tasks` | Critical | GET /tasks returns only the authenticated user's tasks. Every task in the response is verified to have the current user's owner_id. |

---

## Tasks: CRUD — `tests/test_tasks_crud.py`

### Create

| Test | Severity | Description |
|------|----------|-------------|
| `test_create_minimal_task_returns_201_with_defaults` | Critical | Creating a task with only a title returns 201 and applies correct defaults: status='todo', priority='medium', description=null, due_date=null. |
| `test_create_task_with_all_fields` | Normal | Creating a task with all optional fields populated returns 201 and round-trips every value correctly — no field is dropped or coerced. |
| `test_create_task_response_contract` | Normal | The response contains exactly the expected fields: id, title, description, status, priority, due_date, owner_id, created_at, updated_at. Any schema change breaks this test immediately. |

### Read

| Test | Severity | Description |
|------|----------|-------------|
| `test_get_task_by_id_returns_correct_task` | Critical | GET /tasks/{id} returns 200 with the correct task matching what was created. |
| `test_get_nonexistent_task_returns_404` | Normal | Requesting a task ID that does not exist returns 404, not 500 or an empty 200. |

### Update

| Test | Severity | Description |
|------|----------|-------------|
| `test_partial_update_only_changes_specified_fields` | Critical | Sending only a title field in a PUT request updates the title and leaves status and priority unchanged. Confirms partial update behavior. |
| `test_update_task_with_same_values_is_idempotent` | Minor | Updating a task with its existing values returns 200 with an unchanged response. The operation has no unintended side effects. |

### Delete

| Test | Severity | Description |
|------|----------|-------------|
| `test_delete_task_returns_204` | Critical | Deleting an existing task returns 204 No Content. The API uses soft deletion (is_deleted=True), not a physical row removal. |
| `test_deleted_task_returns_404_not_500` | Critical | Fetching a soft-deleted task by ID returns 404. Deleted rows do not cause a server error. |
| `test_deleted_task_absent_from_list` | Critical | After deletion, the task no longer appears in GET /tasks. The list endpoint's is_deleted=False filter works correctly. |

### CRUD Chain

| Test | Severity | Description |
|------|----------|-------------|
| `test_register_login_create_update_delete` | Critical | End-to-end journey: register, log in, create a task, update its status to 'done', delete it, and confirm it is gone from the list. |

---

## Tasks: Filtering — `tests/test_tasks_filter.py`

### Status Filter

| Test | Severity | Description |
|------|----------|-------------|
| `test_no_filter_returns_all_tasks` | Critical | GET /tasks with no query parameters returns all non-deleted tasks for the current user. |
| `test_status_todo_filter` | Critical | GET /tasks?status=todo returns only tasks with status='todo'. |
| `test_status_in_progress_filter` | Normal | GET /tasks?status=in_progress returns only in-progress tasks. |
| `test_status_done_filter` | Normal | GET /tasks?status=done returns only completed tasks. |

### Priority Filter

| Test | Severity | Description |
|------|----------|-------------|
| `test_priority_high_filter` | Normal | GET /tasks?priority=high returns only high-priority tasks. |
| `test_priority_low_filter` | Normal | GET /tasks?priority=low returns only low-priority tasks. |

### Combined Filter

| Test | Severity | Description |
|------|----------|-------------|
| `test_status_and_priority_combined` | Normal | GET /tasks?status=todo&priority=high returns only tasks matching both criteria. Three boundary combinations are created to confirm the intersection works correctly. |
| `test_filter_with_no_matches_returns_empty_list` | Normal | A filter that matches no tasks returns 200 with an empty list, not 404 or 500. |

### Ordering

| Test | Severity | Description |
|------|----------|-------------|
| `test_tasks_returned_newest_first` | Normal | GET /tasks returns tasks ordered by created_at descending. The created_at values in the response are verified to be in non-increasing order. |

### Soft Delete

| Test | Severity | Description |
|------|----------|-------------|
| `test_soft_deleted_task_excluded_from_list` | Critical | After deleting a task, it no longer appears in GET /tasks. A non-deleted task in the same session still does. |
| `test_soft_deleted_task_returns_404_not_500` | Critical | Fetching a soft-deleted task directly by ID returns 404. The row's presence in the DB does not cause a server error. |

---

## Validation — `tests/test_validation.py`

### Task Create Validation

| Test | Severity | Description |
|------|----------|-------------|
| `test_empty_title_returns_422` | Normal | An empty string title returns 422. Pydantic's min_length=1 constraint rejects it before the database. |
| `test_title_exceeding_max_length_returns_422` | Normal | A title of 201 characters returns 422. The max_length=200 constraint is enforced. |
| `test_title_at_max_length_is_valid` | Normal | A title of exactly 200 characters returns 201. The boundary value is accepted and the constraint is inclusive. |
| `test_invalid_status_enum_returns_422` | Normal | A status value not in the TaskStatus enum returns 422. |
| `test_invalid_priority_enum_returns_422` | Normal | A priority value not in the TaskPriority enum returns 422. Valid values are 'low', 'medium', 'high'. |

### Task Update Validation

| Test | Severity | Description |
|------|----------|-------------|
| `test_update_with_empty_title_returns_422` | Normal | Setting title to an empty string via PUT returns 422. The min_length=1 constraint applies to updates as well as creates. |
| `test_update_with_invalid_status_returns_422` | Normal | An invalid status value in a PUT request returns 422. TaskUpdate enforces the same enum validation as TaskCreate. |

### Auth Validation

| Test | Severity | Description |
|------|----------|-------------|
| `test_register_with_invalid_email_returns_422` | Normal | A malformed email in a registration payload returns 422. |
| `test_register_missing_password_returns_422` | Minor | A registration payload with no password field returns 422. Both email and password are required. |
| `test_login_with_json_body_returns_422` | Normal | Sending a JSON body to POST /auth/login returns 422. The endpoint requires application/x-www-form-urlencoded (OAuth2 form data), not JSON. |
