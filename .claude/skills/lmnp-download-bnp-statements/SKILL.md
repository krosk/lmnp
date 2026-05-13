---
name: lmnp-download-bnp-statements
description: Download BNP Paribas PDF statements and extract transactions to statements.csv
---

# Skill: lmnp-download-bnp-statements

Downloads all available BNP Paribas PDF statements (~5 years) to `workspace/statements/`, then
extracts transactions from joint account PDFs and appends them to `workspace/statements.csv`.
Both steps are incremental — files and cache entries already present are skipped.

Run this before `lmnp-year-backfill` to ensure the target year's data is in `statements.csv`.

---

## Scripts

Both scripts live in `.claude/skills/lmnp-download-bnp-statements/`.

## Usage

```bash
# Preview what would be downloaded (no files written)
.venv/bin/python .claude/skills/lmnp-download-bnp-statements/bnp_statements.py --dry-run

# Download all available statements
.venv/bin/python .claude/skills/lmnp-download-bnp-statements/bnp_statements.py

# Download only a specific year
.venv/bin/python .claude/skills/lmnp-download-bnp-statements/bnp_statements.py --year 2025

# Download to a custom directory
.venv/bin/python .claude/skills/lmnp-download-bnp-statements/bnp_statements.py path/to/dir
```

---

## Procedure

### Step 1 — Dry-run preview

```bash
.venv/bin/python .claude/skills/lmnp-download-bnp-statements/bnp_statements.py --dry-run
```

Prints every file that would be downloaded and every file already present. Verify the
expected year and account numbers appear (joint account: `4225`; mortgage: `8946`).

### Step 2 — Download

```bash
.venv/bin/python .claude/skills/lmnp-download-bnp-statements/bnp_statements.py
```

The script prints `skip (exists)` for files already in `workspace/statements/` and
`downloading` for new ones. Re-runs are safe.

### Step 3 — Verify target year

```bash
ls workspace/statements/*_4225_*.pdf | grep "<YYYY>"
```

Expect 12 files for a complete year (one per month, dated at month-end). If fewer
than 12 are present, the remaining statements may not yet be published by BNP —
re-run later or check the online portal.

### Step 4 — Extract transactions to CSV

```bash
.venv/bin/python .claude/skills/lmnp-download-bnp-statements/bnp_pdf_to_csv.py
```

Processes only `*_4225_*.pdf` files with no `.pdf_cache/` entry yet. Appends the
extracted rows (date, label, amount) to `workspace/statements.csv`, creating the file with a
header if it does not exist. Re-runs are safe — already-cached PDFs are skipped.

After this step, `workspace/statements.csv` contains the full transaction history available
from the downloaded PDFs, ready for manual LMNP classification.

---

## Output convention

Files are named `YYYY-MM-DD_ACCOUNT_DOCID.pdf`, e.g.:

```
workspace/statements/2025-01-27_4225_ZZ1FWITQFZL3RJ4KE.pdf
```

This satisfies the `*_4225_*.pdf` pattern used by `bnp_pdf_to_csv.py` to filter joint
account statements. Mortgage documents (`*_8946_*.pdf`) are also downloaded but
ignored by `bnp_pdf_to_csv.py`.

---

## Prerequisites

- woob bnp backend configured (`woob config add bnp`)
- Local patches applied (`apply_patches.py`) — required after any `woob config update`
- `.venv` active (create with `uv venv .venv && uv pip install -r requirements.txt`)
