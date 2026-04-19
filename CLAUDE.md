# lmnp — BNP Paribas statement retrieval

This project automates retrieval of BNP Paribas bank account data (balances, transaction history, documents) using [woob](https://woob.tech). It exists because BNP has no public API for personal use; woob screen-scrapes the retail web interface on your behalf. Everything runs locally — no third-party servers are involved.

---

## Environment

- **Runtime:** Python 3.14 via `.venv/` (created with `uv`)
- **Activate:** `.venv/Scripts/activate` (Windows) or `.venv/Scripts/python.exe` directly
- **woob backend name:** `bnp` (configured via `woob config add bnp`)
- **Credentials file:** `%USERPROFILE%/.config/woob/backends` — plaintext, local use only

## Scripts

- **`transactions.py`** — fetch all transactions for the joint account and write `transactions.csv` (date, label, amount). Run: `.venv/Scripts/python.exe transactions.py [output.csv]`
- **`apply_patches.py`** — reapply the local woob module patches after a fresh install or `woob config update`. Run: `.venv/Scripts/python.exe apply_patches.py`

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
