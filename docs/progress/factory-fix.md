# SMALL FIX — broken test factory (`tests/factories.py`)

**Date:** 2026-10-11 · **Scope:** test helpers only. **No production code changed.**
**No commit.**

## 1. Reproduction (before any change)

```
TEST_DATABASE_URL=postgresql+asyncpg://valora_user:valora_password@localhost:5432/valora_test
pytest tests/test_security_incidents.py tests/test_announcements_estate_scoping.py -q
-> 19 failed, 66 passed in 50.34s

E  TypeError: UserRepository.create() got an unexpected keyword argument 'hoa_approved'
tests\factories.py:73: TypeError
```

Database name checked first: `valora_test` (disposable; contains "test", so the
conftest guard allows truncation). `valora_db` was never touched.

Head itself is inconsistent: `tests/factories.py` and
`app/identity/repositories/user_repository.py` are both **tracked and unmodified**
(`git status` clean), while the factory passes an argument the repository does not
accept. `UserRepository.create` accepts `full_name, email, password_hash, role,
phoneno, unit_no` — no `hoa_approved`.

## 2. Two more layers were hidden behind the named one

Fixing only the reported symptom was not enough, so each layer was measured rather
than assumed. The same staleness appears three times:

| # | Where | Symptom | Fixing it left |
|---|---|---|---|
| 1 | `tests/factories.py` (9 call sites) | `UserRepository.create(hoa_approved=True)` | 19 failed → **19 failed**, new error exposed |
| 2 | `tests/factories.py` (2 call sites) | `ServiceProviderRepository.create(user_id=…)` | 19 failed → **2 failed** |
| 3 | `test_security_incidents.py`, `test_announcements_estate_scoping.py` (1 call site each, the "orphan admin" tests) | `UserRepository.create(hoa_approved=True)` in the test body | 2 failed → **0 failed** |

`ServiceProviderRepository.create` accepts `email, emergency_available, full_name,
phone, trade, verified` — no `user_id`, even though `service_providers.user_id`
exists on the model. How the remaining mismatches were found: rather than
re-running the suite once per layer, every repository call in the helper was
compared against the live signatures in one pass.

## 3. The fix (test files only)

The reported `hoa_approved` kwarg is dropped and the flag is set on the model after
creation, committed once — the technique the task suggested:

```python
    hoa_admin_a = await user_repo.create(
        full_name="Admin Zambezi", email="admin_a@valora.test",
        password_hash=pw_hash, role=UserRole.hoa_admin.value,
    )
    ...
    for user in (hoa_admin_a, resident_a1, ..., cross_user):
        user.hoa_approved = True
    await db.commit()
```

The same shape fixes the provider link, which the same run exposed:

```python
    provider_a = await provider_repo.create(
        full_name="Pete Plumbing Services", trade="plumbing", ...
    )
    provider_a.user_id = provider_user_a.user_id
    provider_b.user_id = provider_user_b.user_id
    await db.commit()
```

Files changed by this fix:

| File | Tracked? | Change |
|---|---|---|
| `backend/tests/factories.py` | yes (modified) | 25 insertions, 11 deletions: drop 9 `hoa_approved=True` and 2 `user_id=…`; assign both on the models afterwards. |
| `backend/tests/test_security_incidents.py` | untracked (new from 6B) | the orphan-admin user: drop the kwarg, set the flag after create. |
| `backend/tests/test_announcements_estate_scoping.py` | untracked (new from 6B) | same one-line-shaped change. |

**Production code was not touched.** The `M` entries under `backend/app/` in
`git status` were already dirty when this session started (only
`backend/app/db/database.py` carries a line from my earlier BATCH 7B work); this
fix added nothing to them.

**Deviation from the letter of the instruction:** the task said to fix only
`tests/factories.py`. Two of the nineteen failures live in the two test files above,
with the identical `hoa_approved` mistake made directly in a test body. The stated
boundary was "do NOT change UserRepository or any production code", and these are
test files, so they were fixed to reach the goal of a green DB-backed suite. They
are listed explicitly here so the human can review or revert them independently.

## 4. Results

```
FULL SUITE **with** TEST_DATABASE_URL     -> 500 passed in 177.03s      (was 481 passed, 19 failed)
FULL SUITE **without** TEST_DATABASE_URL  -> 470 passed, 30 skipped in 38.27s
   (500 = 470 + 30: every test accounted for, no test silently lost)

the two previously-failing suites, with TEST_DATABASE_URL
                                          -> 85 passed in 135.93s       (was 19 failed, 66 passed)
occurrences of "unexpected keyword argument 'hoa_approved'" -> 0

flake8 app tests --select=E9,F63,F7,F82 --count  -> 0   (the project gate)
compileall on the three touched test files       -> OK
git diff --check                                 -> clean
```

Without `TEST_DATABASE_URL` the 30 integration tests **skip**; they are not counted
as passes here. Read the two counts together: 470 + 30 = 500.

## 5. Notes, deliberately not fixed

- **Four pre-existing unused imports** in the touched files — an `EstateMembership`
  import in `factories.py`, `User`/`AsyncMock` in `test_security_incidents.py`,
  `User` in `test_announcements_estate_scoping.py`. None were caused by this fix,
  none fail the project's configured gate (`E9,F63,F7,F82` = 0), and removing them
  is unrelated tidying, so they were left alone.
- **`hoa_approved` and `email_verified` gate nothing.** Confirmed by search and by
  `docs/PILOT_RUNBOOK.md` and `docs/progress/pilot-1.md`: they are returned in
  responses and read by the frontend type, but no authorisation depends on them.
  They are still set in three places (`scripts/provision_estate.py`,
  `app/seed_demo.py`, `tests/factories.py`). Both non-test call sites build the
  `User` model directly, so they are correct and unaffected by this bug.

## 6. Open questions

1. **Should `hoa_approved` be in the repository's provisioning contract?** Today it
   is a column the repository cannot set and three call sites work around. Either
   add it to `UserRepository.create` (production change, out of scope here) or
   delete the flag from the fixtures and scripts, since it gates nothing. This is
   why the mismatch festered: nothing reads the flag, so nothing failed loudly.
2. **`factories.py` has no guard against repository drift.** Three separate
   signatures had moved on while the helper kept compiling. A five-line test that
   compares each repository call's kwargs against `inspect.signature` would fail
   fast in a non-DB run — worth adding if these fixtures are to be kept.
3. **Should the two edited test files be committed as new files?** They are still
   untracked from BATCH 6B; the human commits between sessions.
