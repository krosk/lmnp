# lmnp — BNP Paribas statement retrieval

This project is **step one of a French LMNP (Loueur Meublé Non Professionnel) tax-filing workflow.** It automates retrieval of BNP Paribas bank account data (balances, transaction history, documents) and extraction of transaction history from PDF statements. The extracted movements feed downstream accounting document generation (recettes, charges, amortissements, liasse fiscale).

BNP has no public API for personal use; [woob](https://woob.tech) screen-scrapes the retail web interface on your behalf. Everything runs locally — no third-party servers are involved.

---

## Environment

- **Runtime:** Python 3.14 via `.venv/` (created with `uv`)
- **Activate:** `.venv/Scripts/activate` (Windows) or `.venv/Scripts/python.exe` directly
- **woob backend name:** `bnp` (configured via `woob config add bnp`)
- **Credentials file:** `%USERPROFILE%/.config/woob/backends` — plaintext, local use only

## Scripts

- **`transactions.py`** — fetch all transactions for the joint account and write `transactions.csv` (date, label, amount). Run: `.venv/Scripts/python.exe transactions.py [output.csv]`
- **`apply_patches.py`** — reapply the local woob module patches after a fresh install or `woob config update`. Run: `.venv/Scripts/python.exe apply_patches.py`
- **`pdf_to_csv.py`** — extract transactions from joint account PDFs in `statements/` using the Claude API and append them to a master `statements.csv` (same schema: date, label, amount). Run: `.venv/Scripts/python.exe pdf_to_csv.py [output.csv]`
- **`orchestra.py`** — Download documents (appels de fonds, etc.) from the Agence Joffard Orchestra/Egiweb extranet. Requires `ORCHESTRA_LOGIN` and `ORCHESTRA_PASSWORD` in `.claude/.env`. Run: `.venv/Scripts/python.exe orchestra.py [output_dir]` (default: `charges/`). Use `--list` to preview without downloading; `--type all` to include all document types. Re-runs skip already-downloaded files. Portal: `https://www.orchestrav2.egiweb.net/`
- **`table.py`** — CLI for reading and editing the Table sheet of `LMNP.xlsx`. Run: `.venv/Scripts/python.exe table.py <command> [options]`

  Commands:
  - `list [--year YYYY] [--nature N] [--from DATE] [--to DATE] [--format table|tsv]` — list entries
  - `delete-range --from DATE --to DATE [--dry-run]` — delete rows in a date range
  - `append-csv FILE [--dry-run]` — insert rows from a CSV in date order (see CSV schema below)
  - `summary [--year YYYY]` — totals by Nature
  - `edit ROW --field VALUE [...]` — update one or more fields of a row by its row number (as shown in `list`); supports `--moyen`, `--compte`, `--nature`, `--commentaire`, `--debit`, `--credit`, `--justificatif`; `--dry-run` supported
  - `justificatif-max` — show current max justificatif number and next available

  CSV schema for `append-csv`: `date,moyen,compte,nature,commentaire,debit,credit,justificatif`
  — `date` is ISO `YYYY-MM-DD`; `debit`/`credit` are positive floats or empty; `justificatif` must be quoted if it contains a comma (e.g. `"144,45"`).

  Typical year-backfill workflow:
  1. `pdf_to_csv.py` to extract statements → `statements.csv`
  2. Classify LMNP-relevant transactions → write a CSV with the 8-column schema
  3. `table.py delete-range --from YYYY-01-01 --to YYYY-12-31 --dry-run` to preview what gets cleared
  4. `table.py delete-range --from YYYY-01-01 --to YYYY-12-31` to clear placeholder rows
  5. `table.py append-csv entries.csv --dry-run` then `append-csv entries.csv` to insert

  Only processes files matching `*_4225_*.pdf` (joint account statements). Mortgage documentation (`*_8946_*.pdf`) is silently ignored — it contains no transaction table.

  Requires the Anthropic SDK auth env vars to be set (same ones that power Claude Code in this environment). Set `ANTHROPIC_MODEL` to override the default model (`claude-sonnet-4-6--111582`).

  Results are cached per PDF in `.pdf_cache/` — re-runs only process new files and append to the existing CSV. PDFs are sent as base64 document blocks (no Files API), which works with Vertex AI and LiteLLM proxy endpoints.

  Two known behaviours to be aware of:
  - Labels from PDFs are fuller than woob's truncated versions.
  - `INST EMIS` / `INST RECU` instant transfers are dated in the month they occur but appear on the *following* month's PDF.

## Key commands

```bash
.venv/Scripts/python.exe -m woob bank list                              # list accounts + balances
.venv/Scripts/python.exe -m woob bank history <account_id>              # transaction history (interactive)
.venv/Scripts/python.exe -m woob bill documents <account_id>            # list statements for one account
.venv/Scripts/python.exe -m woob bill download <doc_id> <filename.pdf>  # download one statement
.venv/Scripts/python.exe -m woob bill download all                      # download all statements
```

**Note:** `woob bill list` is not a valid command — use `documents` or `bills`.

## Reinstall / reset

```bash
uv venv .venv
uv pip install -r requirements.txt
.venv/Scripts/python.exe -m woob config add bnp    # enter credentials once
.venv/Scripts/python.exe apply_patches.py          # reapply the 3 module fixes
```

## Bookkeeping artefacts

These files are not in the automated pipeline but are the primary accounting record for the LMNP activity. They live locally and are synced manually to Google Drive.

- **`LMNP.xlsx`** — the master bookkeeping workbook. Sheets:
  - `Table` — transaction journal (Date, Moyen, Compte, Nature, Commentaire, Débit, Crédit, Justificatif). One row per cash movement. See `.claude/rules/table-categorisation.md` for Nature values and filing treatment, and `.claude/rules/table-justificatif.md` for the Justificatif numbering convention.
  - `Mortgage` — amortisation table; computes deductible interest and insurance per month (feeds 2033-B line 294).
  - `Immobilisation` — component breakdown and annual amortissement (feeds 2033-C).
  - `Informations` — SIREN/SIRET, tax regime, Teledec links.
  - `2021-2022`, `2023`, `2024`, `2025` — one sheet per fiscal year; assembles 2033-A, 2033-B, 2033-C, and 2031 figures for entry into Teledec.
  - `Guide` — reference links and filing reminders (human-only).

- **`Justificatifs/`** — numbered PDFs backing every Table entry (bank statements, invoices, receipts, contracts). Named `NNNN_YYMMDD_description.pdf`. Current maximum: **143**. Not tracked by git (`*.pdf` in `.gitignore`) — sync to Google Drive alongside `LMNP.xlsx`.

## Architecture decisions

See `docs/decisions/` for rationale behind key choices:
- [ADR-001](docs/decisions/001-woob-over-playwright.md) — woob over Playwright
- [ADR-002](docs/decisions/002-local-patch-strategy.md) — local patch strategy (copy files vs fork)
- [ADR-003](docs/decisions/003-plaintext-credentials.md) — plaintext credentials for local use

## Local module patch — CRITICAL

The woob `bnp` module has a **local patch** applied. The upstream module (as of 2025-12-18) is broken against the current BNP login page.

**Source of truth for the patches:** `patches/bnp/pp/` — three files: `pages.py`, `browser.py`, `document_pages.py`. `apply_patches.py` copies all three to the live woob module location (resolved at runtime via `Woob().repositories.modules_dir`). Edit files in `patches/` when fixes are needed, then re-run `apply_patches.py`.

**pages.py — LoginPage.login (login keyboard):**
BNP replaced their image-based virtual keyboard with a JS-generated button grid. The page now embeds `var gridNumbers="XXXXXXXXXX"` (10 digits, randomised on every page load) in a `<script>` tag. The form ID also changed from `logincanalnet` to `identForm`.
- Old: fetched a keyboard image URL from a `<style>` tag, used pixel hashing to find digit positions
- New: extracts `gridNumbers` via regex from the script tag; maps each password digit to its 1-indexed position in that string; zero-pads to 2 chars; concatenates → `gridPosition`

**browser.py — iter_accounts (life insurance probe):**
The life insurance account probe (`natio_vie_pro` → `clients.assurance-vie.fr`) is skipped entirely. It caused 4-minute timeouts on every command. No life insurance accounts exist on this profile.

**browser.py + document_pages.py — iter_documents (document listing, ~5 years):**
`iter_documents` now uses `/demat-wspl/rest/rechercheCriteresDemat` (POST with `dateDebut`/`dateFin`) instead of `listerDocuments`. This endpoint returns `mapDocuments` (vs `mapReleves`) and is not capped to 6 months. It is called once per calendar year for the past 5 years. `document_pages.py` adds `iter_documents_date_range` which parses `data/rechercheCriteresDemat/mapDocuments/*/listeDocument`. The old `listerDocuments`+`code` approach is no longer used.

**Do NOT run `woob config update` without immediately running `apply_patches.py` afterwards.** The update overwrites all three patched files.

## When the module breaks again

BNP changes their login page periodically. If `woob bank list` fails with a parse error on the login page:

1. Write a debug script that instantiates the browser, navigates to the login page, and dumps the HTML (see session history for the pattern used to produce `login_page.html`)
2. Look for where `gridNumbers` or the keyboard URL is now embedded
3. Update `LoginPage.login` in `pages.py` accordingly

If `woob bill documents` returns only a RIB and no statements, the document API changed again. Debug by calling `rechercheCriteresDemat` directly with a `dateDebut`/`dateFin` payload and inspecting the response — specifically whether `mapDocuments` still exists under `data/rechercheCriteresDemat` and what the `listeDocument` items look like. Update `iter_documents_date_range` in `document_pages.py` if the response path changed.
