---
name: lmnp-year-backfill
description: Backfill one fiscal year of LMNP transactions into the Table sheet of LMNP.xlsx
---

# Skill: LMNP year-backfill

Populates the Table sheet of `LMNP.xlsx` for a complete fiscal year from BNP Paribas bank statement PDFs. Run this skill once per year, after all 12 monthly PDFs are available, to convert raw bank movements into categorised LMNP accounting entries.

The three authoritative references used throughout this skill:
- `.claude/rules/table-categorisation.md` — Nature values and 2033-B/C filing lines
- `.claude/rules/table-justificatif.md` — justificatif numbering and naming rules
- `CLAUDE.md` — CLI command reference for `table.py`, `bnp_pdf_to_csv.py`, and `orchestra.py`

---

## Prerequisites

- `LMNP.xlsx` is not open in Excel (openpyxl cannot write to a locked file).
- BNP credentials configured and woob patches applied (required for step 1).

---

## Procedure

### Step 1 — Download statements and extract transactions

Invoke the **lmnp-download-bnp-statements** skill. It handles the full pipeline:
dry-run preview → download new PDFs → verify the target year → extract transactions
to `statements.csv`.

After this step, `statements.csv` contains the complete transaction history for all
downloaded PDFs. The output schema is `date,label,amount`.

### Step 2 — Identify LMNP-relevant transactions

Filter `statements.csv` for rows where `date` starts with `<YYYY>`. Classify each row:

**Include (LMNP activity):**

| Bank label pattern | Nature | Notes |
|---|---|---|
| `VIR SEPA RECU /DE <tenant> /MOTIF LOYER MM.YY` | Loyer + Provision | Split 1050 + 120; see step 3 |
| `ECHEANCE PRET 01932 60628946` | Pret | Monthly mortgage instalment |
| `PRLV SEPA TWINSEO ECH/... MDT/HAR1012515...` | Assurance (X) | Contract HAR1012515 |
| `PRLV SEPA TWINSEO ECH/... MDT/HAR1018934...` | Assurance (A) | Contract HAR1018934 |
| `PRLV SEPA SDC LES BALCONS D-OPALE` | Charges | Quarterly copropriété charges |
| PNO (Boursobank — not in statements.csv) | PNO | Add manually; see step 5b |

**Exclude (personal, not LMNP):**
- `FRAIS TENUE DE COMPTE` / `Esprit libre visa` — bank fees, not deductible
- `VIR SEPA RECU /DE ETUDES ET PRODUCTIONS SCHLUMBERGER` — salary
- `VIR SCT INST EMIS /MOTIF VIE|ECONOMI|FRAIS` — personal savings transfers
- `VIR SCT INST RECU /DE ALEXIS HE` — personal reimbursements
- `CHEQUE` — verify individually; most are personal

### Step 3 — Split Loyer payments

Each tenant VIR of 1170.00 becomes two rows:

```
YYYY-MM-DD,Virement,Joint,Loyer,Loyer MM.YYYY,,1050,<stmt_ref>
YYYY-MM-DD,Virement,Joint,Provision,Loyer MM.YYYY,,120,<stmt_ref>
```

### Step 4 — Locate January rent

Rent is due on the 5th of each month. The tenant is expected to pay on or before the 5th, so January rent may arrive in late December of the prior year or in the first few days of January — not a fixed date.

Search both windows:

```bash
# Late December of the prior year
grep "<YYYY-1>-12" statements.csv | grep -i loyer

# Early January
grep "<YYYY>-01" statements.csv | grep -i loyer
```

**If found in December:** include the row with its actual date (e.g. `<YYYY-1>-12-31`). It belongs on the December bank statement of the prior year (same justificatif number as that December's other rows). When clearing placeholders in step 8, widen the range to include it:
```bash
table.py delete-range --from <YYYY-1>-12-25 --to <YYYY>-12-31
```

**If found in January:** treat it like any other monthly rent row — it goes on the January bank statement.

### Step 5 — Download charges invoices from Orchestra

Run `orchestra.py` to fetch all available appels de fonds from the Agence Joffard extranet:

```bash
.venv/Scripts/python.exe orchestra.py --list        # preview what is available
.venv/Scripts/python.exe orchestra.py charges/      # download to charges/
```

The script skips files already present in `charges/`, so re-runs are safe. For the target year you should see quarterly entries (Q1 = 01/01, Q2 = 01/04, Q3 = 01/07, Q4 = 01/10). Q4 of the target year is typically billed in early January of the following year and may not yet be available.

Once downloaded, assign justificatif numbers to the Q1/Q2/Q3 invoices (step 6) and copy them to `Justificatifs/`.

### Step 5b — Handle PNO (non-joint accounts)

The annual PNO insurance premium is paid from Boursobank, not the joint BNP account, so it does not appear in `statements.csv`. Add it manually:

```
YYYY-04-DD,Prélèvement,Bourso,PNO,,<amount>,,<justificatif>
```

Locate the payment date and amount from the Boursobank statement. Assign a justificatif number from the sequence (see step 6).

### Step 6 — Assign justificatif numbers and archive source PDFs

```bash
.venv/Scripts/python.exe table.py justificatif-max
```

Justificatif numbers are assigned incrementally as documents are added — there is no predefined block layout. Each new document gets the next unused integer above the current maximum, regardless of document type. Assign numbers as you go through the entries, in whatever order makes sense for the work session.

For every new justificatif number assigned, **copy the source PDF to `Justificatifs/`** using the naming convention from `.claude/rules/table-justificatif.md`:

```
Justificatifs/NNNN_YYMMDD_description.pdf
```

For monthly bank statements, the source is the PDF in `statements/` and the description is the account and month, e.g.:

```
Justificatifs/0144_250127_BNP_joint_2025-01.pdf   ← statements/2025-01-27_4225_*.pdf
Justificatifs/0145_250227_BNP_joint_2025-02.pdf   ← statements/2025-02-27_4225_*.pdf
...
```

For other documents (PNO invoice, charges appel de fonds, receipts), copy from wherever the document was received.

Bank statement justificatif entry format in the CSV:
- Assurance rows: `"<stmt_num>,<contract_num>"` (e.g. `"144,45"`)
- Pret, Loyer, Provision, Charges rows: `"<stmt_num>"` (e.g. `"144"`)

Known contract numbers (as of 2025):
- HAR1012515 (Assurance X) → contract 45
- HAR1018934 (Assurance A) → contract 43

Consult `.claude/rules/table-justificatif.md` for full numbering rules and the complete filing procedure.

### Step 7 — Write the classification CSV

Create a file (e.g. `<YYYY>_entries.csv`) with header:

```
date,moyen,compte,nature,commentaire,debit,credit,justificatif
```

Sort rows by `date` ascending. Include the December 31 prior-year row first if it exists.

Example rows:

```csv
date,moyen,compte,nature,commentaire,debit,credit,justificatif
2024-12-31,Virement,Joint,Loyer,Loyer janvier 2025,,1050,52
2024-12-31,Virement,Joint,Provision,Loyer janvier 2025,,120,52
2025-01-06,Prélèvement,Joint,Assurance,Assurance (X) Twinseo contrat HAR1012515,13.46,,"144,45"
2025-01-06,Prélèvement,Joint,Assurance,Assurance (A) Twinseo contrat HAR1018934,14.10,,"144,43"
2025-01-10,Prélèvement,Joint,Pret,Echeance emprunt,1056.64,,144
```

Consult `.claude/rules/table-categorisation.md` for the complete Nature vocabulary and filing treatment (600€ threshold, VEFA TMA rules, Caution handling).

### Step 8 — Clear placeholder rows

```bash
# Preview what will be deleted
.venv/Scripts/python.exe table.py delete-range --from <YYYY-1>-12-29 --to <YYYY>-12-31 --dry-run

# Delete
.venv/Scripts/python.exe table.py delete-range --from <YYYY-1>-12-29 --to <YYYY>-12-31
```

The dry-run lists each row with its date and Nature. Verify the count and dates look right before proceeding.

### Step 9 — Insert entries

```bash
# Preview insertions
.venv/Scripts/python.exe table.py append-csv <YYYY>_entries.csv --dry-run

# Insert
.venv/Scripts/python.exe table.py append-csv <YYYY>_entries.csv
```

`append-csv` inserts rows in date order at the correct position in the table — it is not a simple append. The dry-run shows insertion point and each row to be added.

### Step 10 — Verify

```bash
.venv/Scripts/python.exe table.py summary --year <YYYY>
.venv/Scripts/python.exe table.py justificatif-max
```

Expected structure for a standard rental year (tenant paying 1050 + 120/month, full 12 months):
- **Loyer** Crédit: 12 × 1050 = 12,600.00
- **Provision** Crédit: 12 × 120 = 1,440.00
- **Pret** Débit: 12 × 1056.64 = 12,679.68
- **Assurance** Débit: 24 rows (2 contracts × 12 months)
- **Charges** Débit: 3 rows (Q1/Q2/Q3 SDC appels de fonds; Q4 billed the following year)
- **PNO** Débit: 1 row (annual premium)

If counts or totals are off, use `table.py list --year <YYYY>` to inspect individual rows.

### Step 11 — Verify justificatif state

Run `table.py justificatif-max` to confirm the sequence is consistent with what was filed. No file needs to be updated — the command is authoritative.

### Step 12 — Sync to Google Drive

Open `LMNP.xlsx` in Excel and sync `LMNP.xlsx` and `Justificatifs/` to Google Drive. (PDFs were already archived to `Justificatifs/` in step 6.)

---

## Project-specific known values

| Item | Value |
|---|---|
| Tenant monthly payment | 1170 (= Loyer 1050 + Provision 120) |
| Mortgage instalment | ECHEANCE PRET 01932 60628946, 1056.64/month |
| Twinseo HAR1012515 (X) | 13.46/month (stable 2025) |
| Twinseo HAR1018934 (A) | 14.10/month Jan–May 2025; 13.47/month Jun–Dec 2025 |
| HAR1012515 contract justificatif | 45 |
| HAR1018934 contract justificatif | 43 |
| 2021–2024 bank statement range | 5–52 (with 42–47 used for insurance contracts) |
| 2025 bank statement range | 144–155 (Jan–Dec 2025) |
| 2025 charges T2/T3/T4 | 156–158 (T1 filed as 159; no joint-account debit for T1 in 2024 or 2025) |
| Q1 charges pattern | T1 appel de fonds (billed 01/01) is never debited from the joint BNP account — pay source unknown. File the PDF from Orchestra but expect no matching bank row. |
