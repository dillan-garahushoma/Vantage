# Bug Report: Account Registration Failure

**Date:** 2026-08-19  
**Status:** Resolved  
**Affected flow:** `POST /api/v1/auth/register`  
**Symptoms:** Frontend showed *"Unable to connect to the authentication service. Please try again."* then *"Unable to create your account. Please try again."*

---

## Issue 1 — `bcrypt` / `passlib` incompatibility (HTTP 500)

### Symptom
Every registration attempt returned `500 Internal Server Error`. The API logs showed:

```
[WARNING] passlib.handlers.bcrypt: (trapped) error reading bcrypt version
AttributeError: module 'bcrypt' has no attribute '__about__'
...
ValueError: password cannot be longer than 72 bytes, truncate manually if necessary
```

### Root Cause
`passlib 1.7.4` is incompatible with `bcrypt >= 4.1.x`. When passlib initialises its bcrypt backend it:
1. Reads `bcrypt.__about__.__version__` — removed in bcrypt 4+, causing `AttributeError`.
2. Runs an internal self-test with a 73-byte probe password — bcrypt 4+ enforces the 72-byte limit strictly, causing `ValueError`.

`requirements.txt` had `bcrypt==3.2.2` pinned, but the Docker image was installing a newer version due to a stale cached layer.

### Fix
Pinned `bcrypt==4.0.1` in `backend/requirements.txt` — the only 4.x release that retains enough backward compatibility for `passlib 1.7.4` to initialise correctly.

```diff
- bcrypt==3.2.2
+ bcrypt==4.0.1
```

Containers were fully rebuilt:

```bash
docker compose down
docker compose up -d --build --force-recreate
```

---

## Issue 2 — `user_id` / `id` field mismatch (frontend error after 201)

### Symptom
After Issue 1 was resolved, the API correctly returned `201 Created`, but the frontend still displayed *"Unable to create your account. Please try again."*

### Root Cause
The backend's `UserResponse` Pydantic schema serialised the user primary key as `user_id`:

```python
# backend/app/identity/schemas/auth.py
class UserResponse(BaseModel):
    user_id: int   # serialised as "user_id" in JSON
    ...
```

The frontend's `authService.js` validated the response expecting the field to be named `id`:

```js
// FrontEnd/src/auth/authService.js
if (!result.user?.id || !result.user?.email || !result.user?.role) {
    throw new Error('The authentication response did not include a valid user.');
}
```

Because `result.user.id` was `undefined`, `validateAuthResult()` threw, the `catch` block in `RegisterPage.jsx` caught it, and the fallback error message was displayed — even though the account was created successfully on the backend.

### Fix
Added a `serialization_alias` to `UserResponse` so the field is emitted as `"id"` in JSON responses, matching the frontend contract, without renaming the Python attribute or altering the database model.

```diff
# backend/app/identity/schemas/auth.py
- user_id: int
+ user_id: int = Field(..., serialization_alias="id")

- model_config = {"from_attributes": True}
+ model_config = {"from_attributes": True, "populate_by_name": True}
```

Uvicorn's hot-reload picked up the change immediately — no container restart required.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/requirements.txt` | `bcrypt==3.2.2` → `bcrypt==4.0.1` |
| `backend/app/identity/schemas/auth.py` | Added `serialization_alias="id"` to `user_id`; added `populate_by_name: True` to `model_config` |
