# Fix — `seed_demo.py` did not flag the demo estate

Session: 2026-10-10. Branch `valora-work`. One-line fix, one new test file. No commit created.

## The change

`seed_demo()` created "Highveld Ridge Estate" without setting `is_demo`, so the seeded demo estate
took the column default (`false`) and was indistinguishable from a real customer's estate — even
though BATCH AI-2 had added the flag exactly to make that distinction. Now:

```python
estate = Estate(
    name=DEMO_ESTATE_NAME,
    ...
    # Seeded demonstration data: never a real customer's estate.
    is_demo=True,
)
```

**Files touched:** `backend/app/seed_demo.py` (the one-line addition plus a comment) and the new
`backend/tests/test_seed_demo_flag.py`. Nothing else was edited.

## Failing test first

`backend/tests/test_seed_demo_flag.py` runs the **real** seeder against a minimal in-memory session
(`execute`/`add`/`add_all`/`flush`/`commit` only), so no database is touched and nothing is
committed, then asserts on the `Estate` object the seeder actually created.

Before the fix:

```
tests\test_seed_demo_flag.py:65: AssertionError
>       assert estates[0].is_demo is True
E       assert None is True
1 failed, 1 passed
exit=1
```

The assertion caught the real defect: the model's `server_default=false()` never populates the
Python attribute, so the created estate had `is_demo` unset at construction time. After the fix the
same file is **2 passed**.

The second test pins the other half of the seeder's contract — given an existing demo estate it
reports `created: False` and adds nothing, which is why setting the flag on an *existing* demo row
is still an open question below.

## Verification — exact commands and results

Run from `backend/` with `venv\Scripts\python.exe`:

| Command | Result |
| --- | --- |
| `-m pytest tests/test_seed_demo_flag.py -q` (before the fix) | **1 failed, 1 passed** — `assert None is True`, exit 1 |
| `-m pytest tests/test_seed_demo_flag.py -q` (after the fix) | 2 passed |
| `-m pytest tests -q` (with `pipefail`) | **246 passed, 2 skipped** (244 + 2 before this fix) |
| `-m compileall -q app` | exit 0 |
| `-m flake8 app tests --count --select=E9,F63,F7,F82 --show-source --statistics` | 0 |
| `git diff --check` | exit 0 |

## Not run / not verified

- **No database was touched.** The seeder was exercised against a fake session, so the real insert
  path, the FK/unique constraints it relies on and the `is_demo` value as *stored* are verified only
  in code and in memory. `TEST_DATABASE_URL` is not set in this session, so the two DB-backed
  integration tests skipped and are not counted as passes.
- `python -m app.cli seed-demo` was **not run** — it needs a live database, which this fix does not
  have. The write path it takes is therefore "written, not run" end to end.

## Open questions

1. **An already-seeded demo estate stays unflagged.** The seeder is deliberately idempotent: if the
   estate exists it changes nothing, so a developer or pilot database seeded before this fix still
   has `is_demo = false`. If that matters, it needs a one-off `UPDATE estates SET is_demo = true
   WHERE name = 'Highveld Ridge Estate'` — a data change, not a code change, and therefore not
   something to slip into this fix.
2. **Nothing reads the flag yet.** `is_demo` is exposed on the estate read DTO
   (`GET /api/v1/auth/estates`, added in AI-2) and it is now set correctly by the seeder, but no
   behaviour branches on it. BATCH AI-3 raised the same point: no rule has needed it so far, so it
   remains a label for the client.
