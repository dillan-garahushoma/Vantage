import os


os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/valora_test")
os.environ.setdefault("SECRET_KEY", "test-secret-not-for-production")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:5173"]')
