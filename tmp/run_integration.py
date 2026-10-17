"""Run the DB-backed integration tests against a fresh `valora_test` database.

Never prints a credential. Reuses the configured DATABASE_URL's host/port/user and
only swaps the database name, which always contains "test" (the conftest guard).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

BACKEND = Path(__file__).resolve().parent.parent / "backend"
PSQL = r"C:\Users\garah\pgsql\pgsql\bin\psql.exe"
TEST_DB = "valora_test"


def main() -> int:
    sys.path.insert(0, str(BACKEND))
    from app.core.config import get_settings

    url = str(get_settings().DATABASE_URL)
    parts = urlsplit(url)
    user = parts.username or "postgres"
    test_url = urlunsplit(
        (parts.scheme, parts.netloc, f"/{TEST_DB}", parts.query, parts.fragment)
    )

    # Create the test database if it is missing, owned by the app's own role.
    exists = subprocess.run(
        [
            PSQL,
            "-h",
            "127.0.0.1",
            "-p",
            "5432",
            "-U",
            "postgres",
            "-w",
            "-tAc",
            f"SELECT 1 FROM pg_database WHERE datname='{TEST_DB}'",
        ],
        capture_output=True,
        text=True,
    )
    if exists.returncode != 0:
        print("could not query for the test database:", exists.stderr.strip())
        return 2
    if exists.stdout.strip() != "1":
        created = subprocess.run(
            [
                PSQL,
                "-h",
                "127.0.0.1",
                "-p",
                "5432",
                "-U",
                "postgres",
                "-w",
                "-c",
                f'CREATE DATABASE "{TEST_DB}" OWNER "{user}"',
            ],
            capture_output=True,
            text=True,
        )
        print("create database:", created.stdout.strip() or created.stderr.strip())
        if created.returncode != 0:
            return 2
    else:
        print(f"database {TEST_DB} already exists")

    env = dict(os.environ)
    env["TEST_DATABASE_URL"] = test_url
    env["PYTHONPATH"] = str(BACKEND)
    args = sys.argv[1:] or ["tests/test_residency_requests.py", "-q"]
    print(f"running pytest against {TEST_DB}: {' '.join(args)}")
    return subprocess.run(
        [str(BACKEND / "venv" / "Scripts" / "python.exe"), "-m", "pytest", *args],
        cwd=BACKEND,
        env=env,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
