"""Reset one account's password and print the new one **once**.

This is the interim answer to a real gap: VALORA sends no email (there is no mail
transport in the codebase), so there is no self-service "forgot password" flow and
a resident who forgets theirs cannot recover it. Until that exists, an operator
generates a new password here and hands it over out of band.

It is deliberately conservative, in the same shape as
``scripts/assign_platform_admin.py``:

* **dry-run by default** - nothing is written unless ``--apply`` is passed;
* the **target database host and name are printed first**, read straight from
  ``DATABASE_URL`` (never from ``.env``), so the printed target is provably the
  database this run will touch;
* writing into a database whose name looks like a demo/seed database is
  **refused** unless ``--allow-demo-database`` is passed;
* ``--expect-database NAME`` refuses the run when the target is not the database
  the operator meant;
* the generated password comes from ``secrets``, is printed **once** to stdout,
  is never logged, and only its bcrypt hash is stored. It is never written to a
  file by this script.

Usage::

    export DATABASE_URL="postgresql+asyncpg://user:pw@host:5432/valora"
    python scripts/reset_password.py --email resident@example.com          # dry run
    python scripts/reset_password.py --email resident@example.com --apply  # writes

What it does not do: unlock a login-locked account (the lockout is a rolling
15-minute window keyed on recent failures and expires by itself), verify an email
address, or notify the account holder.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import secrets
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import urlsplit

# Allow "python scripts/reset_password.py" from the backend directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.security import hash_password  # noqa: E402
from app.identity.models.user import User  # noqa: E402

logger = logging.getLogger("reset_password")

DEMO_MARKERS: tuple[str, ...] = ("demo", "seed", "sample", "scratch")

# Word-list-free but readable: 4 groups of 5 base32-ish characters from a
# 32-symbol alphabet (~25 bits per group, ~100 bits total). Long enough to survive
# password spraying, short enough to read over a phone.
PASSWORD_ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789"
PASSWORD_GROUPS = 4
PASSWORD_GROUP_LENGTH = 5


class OperatorError(Exception):
    """Something the operator must fix before anything is written."""


def generate_password(
    *,
    groups: int = PASSWORD_GROUPS,
    group_length: int = PASSWORD_GROUP_LENGTH,
    alphabet: str = PASSWORD_ALPHABET,
) -> str:
    """A random password from ``secrets``, in readable groups."""
    return "-".join(
        "".join(secrets.choice(alphabet) for _ in range(group_length))
        for _ in range(groups)
    )


def database_name(url: str) -> str:
    """The database name inside a SQLAlchemy URL, without query parameters."""
    return urlsplit(url).path.lstrip("/").split("?")[0]


def redact_database_url(url: str) -> str:
    """``host:port/name`` only - never a user name or a password."""
    parts = urlsplit(url)
    host = parts.hostname or "<unknown host>"
    port = f":{parts.port}" if parts.port else ""
    return f"{host}{port}/{database_name(url) or '<unknown database>'}"


def looks_like_a_demo_database(url: str) -> bool:
    name = database_name(url).lower()
    return any(marker in name for marker in DEMO_MARKERS)


def target_database_url() -> str:
    """Read the target from the environment, never from ``.env``."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise OperatorError(
            "DATABASE_URL is not set. Export it for this shell "
            "(this script does not read .env, on purpose) and re-run."
        )
    return url


def print_target(url: str) -> None:
    print(f"Target database: {redact_database_url(url)}")
    print("(credentials come from DATABASE_URL and are not shown)")


def default_session_factory():
    """A session factory bound to the URL this run has already printed."""

    @asynccontextmanager
    async def _factory():
        engine = create_async_engine(target_database_url(), echo=False)
        try:
            maker = async_sessionmaker(
                bind=engine, class_=AsyncSession, expire_on_commit=False
            )
            async with maker() as session:
                yield session
        finally:
            await engine.dispose()

    return _factory


async def find_user(session: AsyncSession, *, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


def _guard_target(url: str, args: argparse.Namespace) -> None:
    if args.expect_database and database_name(url) != args.expect_database:
        raise OperatorError(
            f"--expect-database {args.expect_database} does not match the target "
            f"'{database_name(url)}'. Nothing was written."
        )
    if args.apply and looks_like_a_demo_database(url) and not args.allow_demo_database:
        raise OperatorError(
            f"The target database '{database_name(url)}' looks like a demo database. "
            "Pass --allow-demo-database only if you are certain. Nothing was written."
        )


async def run(args: argparse.Namespace, session_factory: Callable) -> int:
    email = args.email.strip().lower()
    async with session_factory() as session:
        user = await find_user(session, email=email)
        if user is None:
            print(f"ERROR: no account exists with email {email}. Nothing was written.")
            return 1

        print(f"Account: {email} (user_id={user.user_id}, role={user.role})")

        if not args.apply:
            print("Proposed action: replace this account's password with a new random one.")
            print("")
            print("[dry-run] no changes were written. Re-run with --apply to write.")
            return 0

        password = generate_password()
        user.password_hash = hash_password(password)
        await session.commit()

        print("")
        print("Applied: the password was replaced.")
        print("")
        print("  email    : " + email)
        print("  password : " + password)
        print("")
        print("Shown once and not stored: hand it to the account holder now and ask")
        print("them to change it. Re-run this script if it is lost.")
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reset one account's password. Dry-run unless --apply is given."
    )
    parser.add_argument("--email", required=True, help="email of an existing account")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the change (without it, this is a dry run)",
    )
    parser.add_argument(
        "--expect-database",
        default=None,
        help="refuse to run unless the target database has this exact name",
    )
    parser.add_argument(
        "--allow-demo-database",
        action="store_true",
        help="permit writing into a database whose name looks like a demo database",
    )
    return parser


async def main(
    argv: Sequence[str] | None = None, *, session_factory: Callable | None = None
) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        url = target_database_url()
        print_target(url)
        _guard_target(url, args)
        factory = session_factory or default_session_factory()
        return await run(args, factory)
    except OperatorError as exc:
        print(f"ERROR: {exc}")
        return 1


def cli() -> int:
    return asyncio.run(main())


if __name__ == "__main__":
    raise SystemExit(cli())
