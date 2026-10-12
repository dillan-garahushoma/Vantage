import os
from urllib.parse import urlparse
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


# When a throwaway test database is provided, point the whole app at it before
# any app module imports Settings. alembic's env.py builds its engine from
# settings.DATABASE_URL rather than from the URL conftest sets on the Alembic
# Config, so the environment is the single lever that keeps migrations off the
# developer's own database. The name still has to contain "test" (guard below).
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
else:
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/valora_test"
    )
os.environ.setdefault("SECRET_KEY", "test-secret-not-for-production")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:5173"]')


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: DB-backed integration test (auto-skipped when TEST_DATABASE_URL is unset)",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        skip_marker = pytest.mark.skip(reason="TEST_DATABASE_URL is not set")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_marker)
    else:
        parsed = urlparse(test_db_url)
        db_name = parsed.path.lstrip("/").split("?")[0]
        if "test" not in db_name.lower():
            raise RuntimeError(
                f"Refusing to run integration tests against non-test database '{db_name}'. "
                "Database name in TEST_DATABASE_URL must contain 'test' to protect against data truncation."
            )


import pytest_asyncio


@pytest.fixture(autouse=True)
def reset_join_attempt_limiter():
    """Keep the process-wide join limiter out of the way between tests.

    The join rate limiter is deliberately in-process state (ADR-007). Tests
    exhaust it and assert windows on it, so it must start and end each test
    empty - otherwise one test's failed attempts would 429 the next test's user.
    """
    from app.identity.services.join_attempt_limiter import join_attempt_limiter

    join_attempt_limiter.reset_all()
    yield
    join_attempt_limiter.reset_all()


@pytest.fixture(scope="session")
def apply_migrations():
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        return
    import pathlib
    from alembic import command
    from alembic.config import Config

    backend_dir = pathlib.Path(__file__).resolve().parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    sync_url = test_db_url.replace("+asyncpg", "")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_cfg, "head")


@pytest_asyncio.fixture
async def test_db_engine():
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        pytest.skip("TEST_DATABASE_URL is not set")
    engine = create_async_engine(test_db_url, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_sessionmaker(test_db_engine):
    return async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def db_session(test_db_engine, test_db_sessionmaker, apply_migrations):
    from sqlalchemy import text

    async with test_db_engine.begin() as conn:
        result = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename <> 'alembic_version';"
            )
        )
        tables = [row[0] for row in result.fetchall()]
        if tables:
            tables_clause = ", ".join(f'"{t}"' for t in tables)
            await conn.execute(text(f"TRUNCATE TABLE {tables_clause} RESTART IDENTITY CASCADE;"))

    async with test_db_sessionmaker() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(test_db_sessionmaker):
    import httpx
    from app.main import app
    from app.db.session import get_db

    async def _get_test_db():
        async with test_db_sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
