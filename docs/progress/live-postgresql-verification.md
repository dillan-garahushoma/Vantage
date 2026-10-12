# Live PostgreSQL Verification & Login Throttling Review

**Date:** 2026-10-10  
**Target:** PostgreSQL 15 (`valora_test`) & Alembic Migration Chain (`d4a7e1c9b3f2`)  
**Status:** Verification Complete, All Tests Passing

---

## 1. Summary of Actions Taken

1. **Configured PostgreSQL Test Database (`valora_test`)**:
   - Verified active PostgreSQL container `valora_db` (Postgres 15-alpine).
   - Confirmed disposable test database `valora_test` exists with proper user permissions (`valora_user`).
   - Confirmed database name satisfies the harness safety gate (`'test' in db_name.lower()`).

2. **Alembic Migration Chain Validation**:
   - Upgraded `valora_test` from blank base to Alembic head `d4a7e1c9b3f2` (all 6 revisions applied cleanly: `5c5c0e0ef686` -> `103dd39ca30e` -> `a1d7e4f2b9c8` -> `b2e8f5c3d0a1` -> `c3f9a6d4e1b2` -> `d4a7e1c9b3f2`).
   - Tested rollback and re-upgrade: downgraded `d4a7e1c9b3f2 -> c3f9a6d4e1b2` and re-upgraded back to `d4a7e1c9b3f2`.

3. **Skipped Integration Test Resolution**:
   - Upgraded asynchronous fixtures in `backend/tests/conftest.py` to `@pytest_asyncio.fixture` to resolve pytest-asyncio async-fixture deprecation.
   - Set `TEST_DATABASE_URL="postgresql+asyncpg://valora_user:valora_password@localhost:5432/valora_test"` and ran test suite.
   - Previously skipped integration test (`test_integration_marker_auto_skips`) now runs and passes.

4. **Live-DB Exercise of Login-Attempt & Rate-Limiting Logic**:
   - Added live PostgreSQL integration test `test_live_db_login_attempt_persistence_and_lockout` in `backend/tests/test_login_rate_limit.py`.
   - Exercised:
     - Real database user seeding.
     - Sequential wrong password attempts recorded into table `login_attempts` with `successful = false`.
     - 429 lockout triggered once `LOGIN_MAX_FAILED_ATTEMPTS` is reached.
     - Correct password rejected with 429 `RATE_LIMITED` during active lockout window.
     - Attempt recording for non-existent users (without timing/enumeration leakage).

5. **Test Results**:
   - **With `TEST_DATABASE_URL`**: 58 passed, 0 skipped, 3 deprecation warnings (FastAPI lifespan/httpx).
   - **Without `TEST_DATABASE_URL`**: 56 passed, 2 skipped (auto-skips as required by safety rule), 0 failures.

---

## 2. Security Review: Account-Based Throttling & Denial-of-Service Risk

### Vulnerability Analysis
The current implementation locks out authentication attempts based strictly on the submitted normalized `email` across a sliding window (`LOGIN_MAX_FAILED_ATTEMPTS = 5`, `LOGIN_LOCKOUT_WINDOW_MINUTES = 15`).

**Identified DoS Mechanism**:
- Any unauthenticated actor who knows or guesses a target user's email address can submit 5 bogus login attempts from any arbitrary IP address.
- Because the rate limit check runs before credential validation, this locks out the legitimate account owner for 15 minutes.
- By repeatedly sending 5 failed attempts every 15 minutes, an attacker can **permanently deny legitimate users access to their accounts** without needing their password.

### Recommended Mitigations (Dual-Key / IP-Composite Throttling & Progressive Delays)

1. **IP + Account Composite Rate Limiting (Dual-Key)**:
   - Enforce an IP-based failure threshold (e.g., 20 failures / 15 minutes per client IP) to stop automated credential stuffing across many accounts.
   - For a specific target email, require *both* account failures *and* IP match to trigger immediate lockout, OR only trigger strict account lockouts after significantly higher threshold from distributed IPs.

2. **Progressive Delays / CAPTCHA rather than Complete Hard Lockout**:
   - After 5 failures from an unknown IP for a specific email, require an out-of-band factor (e.g. email verification code / magic link) or a CAPTCHA challenge rather than returning a blocking 429.
   - Alternatively, implement exponential backoff per IP/email pair (e.g. 5s, 15s, 60s) rather than a coarse 15-minute complete block.

3. **Known / Trusted Client IP Exemption**:
   - If an account has previously logged in successfully from an IP, failed attempts from unfamiliar external IPs should not lock out authentication attempts originating from the user's recognized IP.

4. **Reverse-Proxy IP Resolution**:
   - `request.client.host` currently reads the direct socket peer. In production behind load balancers/reverse proxies, ensure trusted proxy CIDRs are configured before inspecting `X-Forwarded-For` to prevent attackers from spoofing their source IP.

---

## 3. Commands Run and Outputs

| Command | Result |
|---|---|
| `docker exec valora_db psql -U valora_user -d valora_test -c "SELECT * FROM alembic_version;"` | Initial empty DB confirmed |
| `alembic -c backend/alembic.ini upgrade head` | Applied all 6 revisions up to `d4a7e1c9b3f2` |
| `alembic -c backend/alembic.ini downgrade -1 && upgrade head` | Reversible migration confirmed |
| `pytest backend/tests/test_harness_safety.py -v` (with `TEST_DATABASE_URL`) | 2 passed (auto-skip turned to pass) |
| `pytest backend/tests/test_login_rate_limit.py -v` (with `TEST_DATABASE_URL`) | 5 passed (including live PostgreSQL test) |
| `pytest backend/tests -q` (with `TEST_DATABASE_URL`) | **58 passed, 0 skipped** in 31.84s |
| `pytest backend/tests -q` (without `TEST_DATABASE_URL`) | **56 passed, 2 skipped** in 12.10s |
| `python -m compileall -q backend/app` | Exit 0 |
| `flake8 backend/app backend/tests --count --select=E9,F63,F7,F82` | 0 errors |
| `git diff --check` | Clean |
