"""CLI interface to inspect and manage the local SQLite DB used by the app.

Features:
- `list`         : show first N CD rows
- `count`        : show total number of CDs
- `show <id>`    : show full record for a given CD id
- `export <file>`: export all rows to CSV
- `clear`        : delete all rows (requires confirmation or --yes)
- `reset --xlsx path` : clear then import from Excel using `scripts.import_excel.import_direct`

Run as module from repo root (recommended):
  python -m scripts.db_inspect <command> [args]

This script uses the app's SQLAlchemy models and DB connection.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
from typing import Optional


def get_session():
    from app.db.database import SessionLocal

    return SessionLocal()


def cmd_count():
    from app.db import models

    session = get_session()
    try:
        n = session.query(models.CD).count()
        print(f"Total CDs: {n}")
    finally:
        session.close()


def cmd_list(limit: int = 20):
    from app.db import models

    session = get_session()
    try:
        rows = session.query(models.CD).order_by(models.CD.id.asc()).limit(limit).all()
        if not rows:
            print("No rows found.")
            return
        for r in rows:
            print(f"{r.id}\t{r.artist or ''} — {r.title or ''} ({r.year or ''})")
    finally:
        session.close()


def cmd_show(cd_id: int):
    from app.db import models
    from dataclasses import asdict

    session = get_session()
    try:
        r = session.query(models.CD).filter(models.CD.id == cd_id).first()
        if not r:
            print(f"No CD with id={cd_id}")
            return
        # convert SQLAlchemy object to dict
        d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
        for k, v in d.items():
            print(f"{k}: {v}")
    finally:
        session.close()


def cmd_export(path: Path):
    from app.db import models

    session = get_session()
    try:
        rows = session.query(models.CD).order_by(models.CD.id.asc()).all()
        if not rows:
            print("No rows to export.")
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # header
            header = [c.name for c in rows[0].__table__.columns]
            writer.writerow(header)
            for r in rows:
                writer.writerow([getattr(r, c) for c in header])

        print(f"Exported {len(rows)} rows to {path}")
    finally:
        session.close()


def cmd_clear(yes: bool = False):
    from app.db import models

    if not yes:
        confirm = input("Are you sure you want to DELETE ALL rows from the cds table? Type 'yes' to confirm: ")
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            return

    session = get_session()
    try:
        deleted = session.query(models.CD).delete()
        session.commit()
        print(f"Deleted {deleted} rows from cds table.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def cmd_reset(xlsx: Optional[Path]):
    # clear then re-import via import_excel.import_direct
    if xlsx is None or not xlsx.exists():
        print("Please provide a valid Excel file path with --xlsx PATH for reset.")
        return

    # clear (ask for confirmation)
    cmd_clear(yes=False)

    # import
    # import here to avoid heavy deps unless needed
    try:
        from scripts.import_excel import import_direct
    except Exception:
        # import as module if package import path differs
        try:
            import importlib

            mod = importlib.import_module("scripts.import_excel")
            import_direct = getattr(mod, "import_direct")
        except Exception:
            print("Could not import import_direct from scripts.import_excel. Make sure module is available.")
            return

    print(f"Importing from {xlsx}...")
    import_direct(xlsx)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Inspect/manage the app SQLite DB (cds table)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("count", help="Show total number of CDs")

    l = sub.add_parser("list", help="List first N CDs")
    l.add_argument("--limit", type=int, default=20)

    s = sub.add_parser("show", help="Show full record for a CD id")
    s.add_argument("id", type=int)

    e = sub.add_parser("export", help="Export all rows to CSV")
    e.add_argument("path", type=Path)

    c = sub.add_parser("clear", help="Delete all rows from cds table")
    c.add_argument("--yes", action="store_true", help="Confirm without prompt")

    r = sub.add_parser("reset", help="Clear DB and import from Excel")
    r.add_argument("--xlsx", type=Path, required=True, help="Excel file to import after clearing")

    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.cmd == "count":
        return cmd_count()
    if args.cmd == "list":
        return cmd_list(limit=args.limit)
    if args.cmd == "show":
        return cmd_show(args.id)
    if args.cmd == "export":
        return cmd_export(args.path)
    if args.cmd == "clear":
        return cmd_clear(yes=args.yes)
    if args.cmd == "reset":
        return cmd_reset(args.xlsx)


if __name__ == "__main__":
    raise SystemExit(main())
