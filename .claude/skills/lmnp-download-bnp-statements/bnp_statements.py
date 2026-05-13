#!/usr/bin/env python
"""bnp_statements.py — Bulk-download BNP Paribas PDF statements.

Uses the woob bnp backend to fetch all available statements (~5 years) for
all subscriptions and save them to statements/.

Usage:
  python bnp_statements.py [output_dir]           # download all (default: statements/)
  python bnp_statements.py --year 2024            # filter to one year
  python bnp_statements.py --dry-run              # preview without downloading
"""
import os
import re
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
os.environ.setdefault("WOOB_BACKENDS", str(PROJECT_ROOT / "workspace" / "backends"))


def main():
    output_dir = Path("workspace/statements")
    dry_run = False
    year_filter = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--year":
            i += 1
            if i < len(args):
                year_filter = int(args[i])
        elif not arg.startswith("-"):
            output_dir = Path(arg)
        i += 1

    if dry_run:
        print("[dry-run] no files will be written")

    from woob.core import Woob

    print("Initialising woob bnp backend...")
    w = Woob()
    backend = list(w.load_backends(modules=["bnp"]).values())[0]
    browser = backend.browser

    if not dry_run:
        output_dir.mkdir(exist_ok=True)

    new_count = 0
    skip_count = 0
    errors = []

    for s in list(backend.iter_subscription()):
        account = re.sub(r"[^a-zA-Z0-9]", "", s._number)
        print(f"\nSubscription {account}:")

        for d in backend.iter_documents(s):
            if not isinstance(d.date, date):
                continue
            if year_filter is not None and d.date.year != year_filter:
                continue

            doc_id = d.id.split("_")[1] if "_" in d.id else d.id
            filename = f"{d.date}_{account}_{doc_id}.pdf"
            out_path = output_dir / filename

            if out_path.exists():
                print(f"  skip (exists): {filename}")
                skip_count += 1
                continue

            print(f"  {'[dry-run] would download' if dry_run else 'downloading'}:   {filename}")
            if dry_run:
                new_count += 1
                continue

            try:
                pdf_bytes = browser.open(d.url).content
                out_path.write_bytes(pdf_bytes)
                new_count += 1
            except Exception as e:
                print(f"    ERROR: {e}")
                errors.append((filename, str(e)))

    verb = "would save" if dry_run else "saved"
    print(f"\n{new_count} new file(s) {verb} to {output_dir}/")
    print(f"{skip_count} file(s) already present, skipped.")
    if errors:
        print(f"{len(errors)} error(s):")
        for fname, err in errors:
            print(f"  {fname}: {err}")


if __name__ == "__main__":
    main()
