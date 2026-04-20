---
description: Reverse-engineered contract for the Orchestra/Egiweb copropriété portal used by Agence Joffard
paths:
  - "orchestra.py"
---

# Orchestra/Egiweb platform — API contract

`orchestra.py` scrapes the Agence Joffard extranet at `https://www.orchestrav2.egiweb.net/`. This file records the reverse-engineered behaviour so future sessions do not need to re-probe the platform.

## Authentication

Two-step. Both requests must use the same `requests.Session` to carry the cookie.

**Step 1 — POST credentials:**
```
POST https://www.orchestrav2.egiweb.net/admin/pwd.php
Form fields: login, password, url_param (empty), comment (honeypot, leave empty), Submit="Connexion"
Response: 75-byte JS redirect body; sets PHPSESSID cookie
```

**Step 2 — Follow JS redirect:**
```
GET https://www.orchestrav2.egiweb.net/admin/login-2.php
Response: authenticated landing page (HTML, ~20 KB)
```

The `login` field uses CSS class `SaisieMajucule` — the portal may uppercase it client-side, but the server accepts mixed case. Send the value as-is.

## Document listing

```
GET https://www.orchestrav2.egiweb.net/Works/Docnew.php
```

Returns HTML with all documents as collapsed table sections. Each document is a JavaScript call:

```html
<a href="#" onClick="javascript:send('HEX_ENCODED_NAME')">Label</a>
```

The hex string is the ASCII filename encoded as hex: `bytes(name, 'ascii').hex()`. Decode with `bytes.fromhex(hex_str).decode('ascii')`.

## Document download

```
POST https://www.orchestrav2.egiweb.net/Works/document.php
Form field: DocName = <hex-encoded filename>  (the raw hex string, not the decoded name)
Response: application/pdf binary
```

Validate `Content-Type: application/pdf` on every response. A login expiry or URL change returns HTML silently with status 200.

## Document name format

```
@PREFIX + BUILDING_CODE + _ + LOT_NUMBER + _ + START_DATE + _ + END_DATE + .PDF
```

For this property:
- Building code: `0217`
- Lot/owner number: `00039`
- Dates: `YYYYMMDD`

Example: `@FGC0217_00039_20250401_20250401.PDF` = appel de fonds Q2 2025 (billed 2025-04-01).

## Known document type prefixes

| Prefix | Type | Notes |
|--------|------|-------|
| `@FGC` | Appel de fonds | Quarterly charge calls; primary download target |
| `@XCC` | Annexe de répartition | Annual charge breakdown |
| `@CCC` | Compte copropriétaire | Owner account statement |
| `@JCC` | Journal de charges | Charge journal |
| `@DCC` | Détail de charges | Charge detail |
| `@D04` | Correspondance / autres | Individual letters and notices |
| `$E`   | Unknown | Seen once; likely a special report |

## Known portal endpoints (not yet automated)

| Path | Purpose |
|------|---------|
| `Works/CC.php?Doc=CC` | Charges account — "Position compte de charges" |
| `Works/CL.php?contenu=C` | Account balances — "Vos soldes de comptes" |
| `Works/CL.php?contenu=D` | Unknown variant of above |
| `Works/PR.php` | Advances and works fund |
| `Works/Budget.php` | Budget |
| `Works/RensAdm.php` | Administrative information |
| `Works/coprovpc.php` | Unknown |
| `Works/coprovpc_h.php` | Unknown |
| `Works/msg.php` | Messaging |
| `Works/demx_depa.php` | Departure request |
| `WorksPrint/CC.php?Doc=CC` | Print view of charges account |

## SSL

The server uses a self-signed certificate chain. Pass `verify=False` to `requests` and suppress `urllib3` warnings with `urllib3.disable_warnings()`.

## Failure modes

- **Login failure**: `pwd.php` still returns 200 with the JS redirect body even on wrong credentials. Detect failure by checking that `Docnew.php` returns a non-empty document list after login.
- **Session expiry**: `document.php` returns HTML (200) instead of PDF. Always check `Content-Type`.
- **Encoding change**: if Egiweb stops using hex and `send()` changes, `bytes.fromhex()` will raise `ValueError`. Catch and report.
- **URL scheme change**: `Docnew.php` may restructure the JS calls. The regex `onClick="javascript:send\('([0-9a-fA-F]+)'\)"` would match zero documents — treat zero results as a probe failure, not an empty list.
