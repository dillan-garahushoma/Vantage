"""Command-line utilities for VALORA."""

import argparse
import json
from pathlib import Path

from app.main import app


def export_openapi() -> Path:
    output_path = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("export-openapi", help="write the deterministic OpenAPI contract")
    args = parser.parse_args()

    if args.command == "export-openapi":
        print(export_openapi())


if __name__ == "__main__":
    main()
