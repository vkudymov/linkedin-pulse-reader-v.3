"""Encrypt existing ``linkedin_accounts`` session fields.

``cookies_json`` and ``session_snapshot`` written before application-level
encryption are plaintext JSON. This script rewrites those values as
``enc:v1:`` Fernet tokens. Rows that are already tokens are skipped.

Generate a key once and store it only in the worker environment
(``LINKEDIN_COOKIES_ENCRYPTION_KEY``). Do not commit the key.

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

From the ``worker/`` directory, with ``SUPABASE_URL``,
``SUPABASE_SERVICE_ROLE_KEY``, and ``LINKEDIN_COOKIES_ENCRYPTION_KEY`` set:

    python scripts/encrypt_linkedin_accounts.py --dry-run
    python scripts/encrypt_linkedin_accounts.py

The script prints counts only. It does not print cookies or snapshots.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def _ensure_storage_import() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "Storage" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _needs_encryption(value: Any) -> bool:
    from storage.session_crypto import is_encrypted

    if value is None:
        return False
    return not is_encrypted(value)


def encrypt_existing_accounts(*, client: Any, dry_run: bool, page_size: int = 200) -> tuple[int, int]:
    from storage.session_crypto import encrypt_json

    updated = 0
    skipped = 0
    offset = 0
    while True:
        resp = (
            client.table("linkedin_accounts")
            .select("id,cookies_json,session_snapshot")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = getattr(resp, "data", None)
        if not isinstance(rows, list) or not rows:
            break
        for row in rows:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            patch: dict[str, Any] = {}
            cookies = row.get("cookies_json")
            snapshot = row.get("session_snapshot")
            if _needs_encryption(cookies):
                patch["cookies_json"] = encrypt_json(cookies)
            if _needs_encryption(snapshot):
                patch["session_snapshot"] = encrypt_json(snapshot)
            if not patch:
                skipped += 1
                continue
            updated += 1
            if dry_run:
                continue
            (
                client.table("linkedin_accounts")
                .update(patch)
                .eq("id", row["id"])
                .execute()
            )
        if len(rows) < page_size:
            break
        offset += page_size
    return updated, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count rows that would be encrypted without writing.",
    )
    args = parser.parse_args(argv)

    _ensure_storage_import()
    from storage.core.client import create_supabase_client
    from storage.session_crypto import SessionCryptoError

    try:
        client = create_supabase_client()
        updated, skipped = encrypt_existing_accounts(client=client, dry_run=args.dry_run)
    except SessionCryptoError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            f"ERROR: failed to encrypt linkedin_accounts session fields ({type(exc).__name__}).",
            file=sys.stderr,
        )
        return 1

    mode = "would_encrypt" if args.dry_run else "encrypted"
    print(f"{mode}={updated} already_encrypted_or_empty={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
