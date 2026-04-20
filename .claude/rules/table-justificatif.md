---
description: Conventions for the Justificatif column in the Table sheet of LMNP.xlsx
paths:
  - "LMNP.xlsx"
---

# Table — Justificatif numbering convention

The Justificatif column in the Table sheet ties every transaction to its physical proof. Numbers are assigned sequentially across all document types — bank statements and individual receipts share the same sequence.

## Numbering rules

- Numbers are assigned incrementally — no predefined blocks per document type.
- The current maximum is always the output of `table.py justificatif-max`. Do not hardcode it here.
- A single transaction may reference multiple documents: use a comma-separated list (e.g. `37,143`).
- A single document may justify multiple transactions on the same bank statement: repeat the same number across those rows.
- Never reuse a number. Never leave a number as `x` or blank once the document is located.

## Adding a new document — steps

1. Run `table.py justificatif-max` to get the next available number.
2. Copy the PDF to `Justificatifs/` using the naming convention `NNNN_YYMMDD_description.pdf` (4-digit zero-padded number, date as YYMMDD, short description with underscores). Example: `0156_250407_opale_charges_25T1.pdf`.
3. In the Table row, set the Justificatif cell to that number, or append it comma-separated if a bank statement reference already exists (e.g. `147,156`).
4. Sync `Justificatifs/` and `LMNP.xlsx` to Google Drive.

## File naming convention

`Justificatifs/NNNN_YYMMDD_description.pdf`

- `NNNN`: 4-digit zero-padded justificatif number
- `YYMMDD`: document date
- `description`: short label, underscores for spaces

Examples from the folder: `0141_240811_facture-TELEDEC-261172.pdf`, `0142_240219_Bosch_3030217359.PDF`

## Example — Travaux G fix (2026-04)

The row `2024-03-18 | Travaux G | Solde des options | 1770€` had justificatif `37,x`:
- `37` = March 2024 bank statement (shows the bank debit)
- `x` = missing underlying document

The developer devis (D201-DEVIS TMAV2, Atland Résidentiel, 07/09/2021, 1,770€ TTC) was located, copied to `Justificatifs/0143_210907_Atland_D201_DEVIS_TMAV2.pdf`, and assigned number **143**. The Table cell was updated to `37,143`.
