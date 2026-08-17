"""
JWT service — token creation and decoding.
Thin wrapper around core.security that can be injected as a dependency
or called directly by other services.
"""
from app.core.security import create_access_token, decode_access_token

__all__ = ["create_access_token", "decode_access_token"]
