"""CLI entrypoint for the integration sync/ETL.

Run with:  python -m app.sync

Reads the `integration_*` source tables and normalizes them into the domain
tables (KYC cases + events, payments). Idempotent — safe to re-run.
"""

from app.db import SessionLocal
from app.services import sync_service


def main() -> None:
    db = SessionLocal()
    try:
        result = sync_service.sync_all(db)
        print("Sync complete:")
        for source, counts in result.items():
            print(
                f"  {source}: created={counts['created']} "
                f"updated={counts['updated']} skipped={counts['skipped']}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
