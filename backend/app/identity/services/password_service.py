"""
Password service — password hashing and verification.
Thin wrapper around core.security for consistency in the services layer.
"""
from app.core.security import hash_password, verify_password

__all__ = ["hash_password", "verify_password"]
