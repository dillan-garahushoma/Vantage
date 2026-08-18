# VALORA Live Current Folder Structure

Generated/vendor folders are intentionally omitted for readability:

- `.git/`
- `.idea/`
- `FrontEnd/node_modules/`
- `FrontEnd/dist/`
- `backend/venv/`
- `__pycache__/`

```text
valora-live/
├── !BACKEND DEV UPDATE
├── !FRONT END DEVELOPMENT UPDATE.md
├── CURRENT_FOLDER_STRUCTURE.md
├── NEXT_BUILD_ROADMAP.md
├── docker-compose.yml
├── backend/
│   ├── .dockerignore
│   ├── .env
│   ├── .env.example
│   ├── .gitignore
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── alembic/
│   │   ├── README
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 5c5c0e0ef686_consolidated_architecture.py
│   ├── app/
│   │   ├── .env
│   │   ├── main.py
│   │   ├── analytics/
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   └── router.py
│   │   │   ├── domain/
│   │   │   │   ├── __init__.py
│   │   │   │   └── entities.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   └── ai_analytic.py
│   │   │   ├── repositories/
│   │   │   │   └── __init__.py
│   │   │   ├── schemas/
│   │   │   │   └── __init__.py
│   │   │   └── services/
│   │   │       └── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── router.py
│   │   ├── common/
│   │   │   ├── __init__.py
│   │   │   ├── enums.py
│   │   │   ├── pagination.py
│   │   │   └── validators.py
│   │   ├── community/
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   └── router.py
│   │   │   ├── domain/
│   │   │   │   ├── __init__.py
│   │   │   │   └── entities.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── announcement.py
│   │   │   │   ├── complaint.py
│   │   │   │   └── maintenance_work_order.py
│   │   │   ├── repositories/
│   │   │   │   └── __init__.py
│   │   │   ├── schemas/
│   │   │   │   └── __init__.py
│   │   │   └── services/
│   │   │       └── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── exceptions.py
│   │   │   ├── logging.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── database.py
│   │   │   └── session.py
│   │   ├── identity/
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dependencies.py
│   │   │   │   └── router.py
│   │   │   ├── domain/
│   │   │   │   ├── __init__.py
│   │   │   │   └── entities.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── login_attempt.py
│   │   │   │   ├── session.py
│   │   │   │   └── user.py
│   │   │   ├── repositories/
│   │   │   │   ├── __init__.py
│   │   │   │   └── user_repository.py
│   │   │   ├── schemas/
│   │   │   │   ├── __init__.py
│   │   │   │   └── auth.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── auth_service.py
│   │   ├── property/
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   └── router.py
│   │   │   ├── domain/
│   │   │   │   ├── __init__.py
│   │   │   │   └── entities.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── listing.py
│   │   │   │   ├── property.py
│   │   │   │   └── sale.py
│   │   │   ├── repositories/
│   │   │   │   └── __init__.py
│   │   │   ├── schemas/
│   │   │   │   └── __init__.py
│   │   │   └── services/
│   │   │       └── __init__.py
│   │   └── providers/
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   └── router.py
│   │       ├── domain/
│   │       │   ├── __init__.py
│   │       │   └── entities.py
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── review.py
│   │       │   └── service_provider.py
│   │       ├── repositories/
│   │       │   └── __init__.py
│   │       ├── schemas/
│   │       │   └── __init__.py
│   │       └── services/
│   │           └── __init__.py
│   └── tests/
│       └── __init__.py
└── FrontEnd/
    ├── .env.example
    ├── .gitignore
    ├── FRONTEND_ACCEPTANCE_CHECKLIST.md
    ├── Home Page
    ├── README.md
    ├── check/
    │   └── 1
    ├── index.html
    ├── package-lock.json
    ├── package.json
    ├── scripts/
    │   ├── build.mjs
    │   └── dev-server.mjs
    ├── src/
    │   ├── App.jsx
    │   ├── main.jsx
    │   ├── styles.css
    │   ├── api/
    │   │   ├── authApi.js
    │   │   ├── client.js
    │   │   └── index.js
    │   ├── auth/
    │   │   ├── AuthContext.jsx
    │   │   ├── ProtectedRoute.jsx
    │   │   ├── authErrorMessages.js
    │   │   ├── authService.js
    │   │   ├── index.js
    │   │   └── mockAuthService.js
    │   ├── components/
    │   │   ├── FormField.jsx
    │   │   ├── SubmitButton.jsx
    │   │   └── ValoraLogo.jsx
    │   ├── config/
    │   │   └── environment.js
    │   ├── pages/
    │   │   ├── AppHomePage.jsx
    │   │   ├── LoginPage.jsx
    │   │   └── RegisterPage.jsx
    │   ├── router/
    │   │   └── Router.jsx
    │   └── utils/
    │       └── validation.js
    └── tests/
        ├── phase3-auth.test.mjs
        ├── phase6-api.test.mjs
        └── phase7-hardening.test.mjs
```

## Notes

- **Architecture Consolidation Complete**: The backend has fully transitioned to a Clean Architecture modular monolith.
- `backend/app/api/router.py` remains the single application-level API composition point.
- Models, routers, services, and repositories are explicitly confined to their domain bounds (`identity`, `property`, `community`, `providers`, `analytics`).
- `backend/app/models`, `backend/app/routers`, `backend/app/services`, and `backend/app/shared` have been completely removed.
- Core config and database infrastructure now live permanently in `backend/app/core/` and `backend/app/db/`.
