---
description: Table sheet schema and Nature categorisation rules — how each transaction type maps to 2033-B/2033-C filing lines
paths:
  - "LMNP.xlsx"
---

# Table — schema and transaction categorisation

The Table sheet is the LMNP transaction journal. Every cash movement related to the activity is entered here with a Nature that determines its filing treatment. Correct categorisation at entry time prevents misclassification on the tax forms.

## Column schema

| Column | Name | Values |
|---|---|---|
| A | Date | datetime — date of the bank transaction |
| B | Moyen | `Prélèvement`, `Virement` |
| C | Compte | `Joint` (only account in use) |
| D | Nature | see categorisation table below |
| E | Commentaire | free text description |
| F | Débit | positive amount, or empty |
| G | Crédit | positive amount, or empty |
| H | Justificatif | see `.claude/rules/table-justificatif.md` |

Rows are ordered by date ascending. Insert new rows in date order.

## Nature values and filing treatment

| Nature | What it covers | Filing line | Notes |
|---|---|---|---|
| `Loyer` | Pure rent received | 2033-B **218** | Exclude provisions de charges |
| `Provision` | Tenant charges provision received | 2033-B **230** | 120€/month; separate from Loyer |
| `Caution` | Security deposit received | Balance sheet only | Not income; refundable — never on 2033-B |
| `Charges` | Copropriété charges called | 2033-B **242** | Actual appels de fonds, not provisions |
| `PNO` | Assurance propriétaire non-occupant | 2033-B **242** | Annual premium |
| `Assurance` | Mortgage insurance (Twinseo / BNP) | 2033-B **294** | Via Mortgage sheet computation, not direct |
| `Pret` | Mortgage instalment (capital + interest) | 2033-B **294** (interest only) | Only the deductible portion is filed; computed in Mortgage sheet |
| `Meuble` | Furniture — items with a till receipt | 2033-B **242** | Each item must be < 500€ HT (600€ TTC); otherwise capitalise |
| `Meuble nf` | Furniture — items without a full invoice | 2033-B **242** | Same 600€ TTC threshold applies per item |
| `Electromenager` | Appliances | 2033-B **242** | Same 600€ TTC threshold per item |
| `Travaux` | Repairs / maintenance works | 2033-B **242** | Entretien/réparation only; see threshold rule below |
| `Gestion` | Property management fees | 2033-B **242** | e.g. Teledec accounting fees |
| `Travaux G` | Major works / VEFA TMA payments | **2033-C** (capitalised) | Do not put on 2033-B; see capitalisation rule below |

## The 600€ TTC threshold

For furniture, appliances, and small tools: items with a **unit value below 500€ HT (600€ TTC)** may be expensed directly on line 242. Items at or above 600€ TTC per unit must be capitalised on 2033-C.

This threshold applies **per item**, not per receipt. A single receipt covering multiple items each under 600€ TTC is fully deductible on 242 even if the total exceeds 600€.

For **travaux d'entretien/réparation** (maintenance and repair): deductible on 242 regardless of amount — no threshold.
For **travaux d'amélioration** (improvements that add value or extend lifespan): capitalise on 2033-C regardless of amount.

## VEFA TMA payments — always capitalise

Travaux Modificatifs Acquéreurs (developer-issued modifications ordered during the VEFA build) are **part of the acquisition cost**, not travaux in the accounting sense. Capitalise the full TTC amount on 2033-C, split 10% terrain / 90% construction, regardless of amount.

Do not apply the 600€ threshold to TMA payments. Do not put them on 2033-B line 242.

Example: `Travaux G | Solde des options | 1,770€` (Atland devis D201, 2024-03-18) → 177€ terrain + 1,593€ construction on 2033-C.

## Caution — never income

The security deposit (`Caution`) appears as a credit in the Table but is a liability, not rental income. It must not appear on 2033-B line 218 or 230. It is recorded in the Table for cash-flow tracking only.
