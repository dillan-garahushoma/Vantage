"""Real Alembic configuration must preserve URL-encoded credentials."""
from alembic.config import Config
from sqlalchemy.engine import make_url

from app.db.migration_config import configure_database_url


def test_url_escaped_password_survives_config_interpolation():
    config = Config()
    url = 'postgresql+asyncpg://example:synthetic%2Bvalue%2Fwith%25encoding@127.0.0.1:54329/valora_test'
    configure_database_url(config, url)
    assert config.get_main_option('sqlalchemy.url') == url
    assert make_url(config.get_main_option('sqlalchemy.url')).password == 'synthetic+value/with%encoding'
