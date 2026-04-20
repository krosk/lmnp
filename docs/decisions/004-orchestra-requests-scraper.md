# ADR-004 — Orchestra document retrieval: requests scraper over Playwright or woob

## Status
Accepted (2026-04)

## Context

The Agence Joffard copropriété portal runs Orchestra v2 by Egiweb (`orchestrav2.egiweb.net`). It is a PHP/session-based web application that provides quarterly appels de fonds and other accounting documents. No public API exists. Three automation approaches were considered.

## Options considered

**Option A — `requests` scraper** (chosen)
A plain Python `requests` session handles the two-step login and POSTs hex-encoded document names to `document.php`. No additional dependencies. The entire platform interaction is ~50 lines of Python.

**Option B — Playwright**
Full browser automation. More robust against JavaScript-heavy rendering, but Orchestra v2 is server-side PHP — no client-side rendering requiring a real browser. Adds a large binary dependency and significant session overhead for a site that responds fine to plain HTTP.

**Option C — woob module**
Would integrate cleanly with the existing BNP workflow. However, Egiweb Orchestra is a proprietary platform with no woob backend, and writing one is disproportionate for a portal that only needs to download ~3 PDFs per year.

## Decision

Option A. The site is classic PHP with a PHPSESSID cookie and no CAPTCHA. The full login + download roundtrip was validated interactively before writing the script. Re-runs skip already-downloaded files, so the annual cost is one login + three GETs.

## Consequences

- `orchestra.py` owns all Orchestra interaction. It must be maintained if Egiweb changes their login flow or document URL scheme.
- The hex-encoding of document names is the main fragility: if Egiweb changes `send()` to use a different encoding or endpoint, the scraper breaks silently (returns non-PDF content). `orchestra.py` validates `Content-Type: application/pdf` on every download.
- Playwright remains the fallback if a CAPTCHA or JavaScript challenge is added.
