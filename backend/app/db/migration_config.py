"""Adapt database URLs to Alembic's ConfigParser interpolation rules."""
from alembic.config import Config


def configure_database_url(config: Config, url: str) -> None:
    # ConfigParser reserves percent for interpolation; SQLAlchemy still needs
    # the original percent-encoded URL when the option is retrieved.
    config.set_main_option('sqlalchemy.url', url.replace('%', '%%'))
