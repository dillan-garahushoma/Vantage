---
name: valora-quality-gates
description: Enforces the mandatory multi-stage quality verification pipeline for all VALORA features. Use to validate feature completeness before considering any task done.
---

# VALORA Quality Gates & Verification Pipeline

In VALORA, "the code compiles" or "the container starts" does **not** mean a feature is complete. Every meaningful feature must pass through an 8-stage verification pipeline:

```text
1. Requirements Alignment
         ↓
2. Architecture & Contract Check
         ↓
3. Clean Implementation
         ↓
4. Automated Tests (Unit & Integration)
         ↓
5. Live Browser Verification (Chrome DevTools / Playwright)
         ↓
6. Security & Authorization Audit
         ↓
7. Performance & Query Check
         ↓
8. Senior Code Review
         ↓
       SHIP
```

## Quality Gate Checklist

### 1. Requirements Alignment
- Feature directly traces to a persona requirement in [VALORA_PRD.md](file:///c:/Users/garah/PycharmProjects/VANTAGE/docs/VALORA_PRD.md).
- Acceptance criteria are clearly defined before code is written.

### 2. Architecture & Contracts
- Respects Clean/Layered separation: Router → Service → Repository → Entity.
- Pydantic DTOs enforce strict input validation, response schemas, and error envelopes.

### 3. Clean Implementation
- Preserves readability, explicit type annotations, and docstrings.
- No dead code, debug statements (`console.log`, `print()`), or temporary bypasses left in place.

### 4. Automated Tests
- Backend: pytest tests covering service logic, edge cases, boundaries, and error handlers.
- Frontend: Vitest/React Testing Library verifying component rendering and user interactions.

### 5. Live Browser Verification
- Verified in a real browser session via Chrome DevTools or Playwright CLI.
- No console errors, unhandled rejections, broken styling, or layout shifts on desktop/mobile viewports.

### 6. Security & Authorization Audit
- Role guards enforce access control on all restricted endpoints (`resident`, `hoa_admin`, `investor`).
- IDOR checks prevent users from accessing estates or units they do not own or manage.
- Password hashing uses bcrypt; JWTs are validated on every secured request.

### 7. Performance & Database Check
- No N+1 queries in SQLAlchemy relationships (use `selectinload` or `joinedload`).
- Appropriate indexes exist on foreign keys, status columns, and timestamp fields.

### 8. Senior Code Review
- Multi-axis review across correctness, security, maintainability, performance, and architecture.
- Any lint warnings or compiler feedback addressed.
