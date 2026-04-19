# ADR-001: woob over Playwright for BNP automation

**Date:** 2026-04-19  
**Status:** Accepted

## Context

BNP Paribas has no public API for personal account access. Two approaches were available for programmatic retrieval of account data and statements:

- **woob** — a Python screen-scraping framework with a pre-existing `bnp` module that handles login, account listing, transaction history, and document retrieval via BNP's internal JSON APIs.
- **Playwright** — a browser automation library that drives a real Chromium instance against the BNP web interface.

## Decision

Use woob.

## Rationale

The woob `bnp` module already reverse-engineered BNP's internal JSON APIs (`releveOp`, `listerDocuments`, `rechercheCriteresDemat`, etc.). These APIs return structured data directly — no HTML parsing, no layout fragility. Playwright would require driving the visual UI, handling dynamic rendering, and parsing or downloading files through a browser download pipeline.

woob also has no browser dependency, runs headlessly with no display, and produces machine-readable output natively. For a scripted, unattended use case this is strictly better than a browser driver.

## Trade-offs accepted

woob's module scrapes session state and form fields that BNP can change without notice. Three breaking changes were encountered on first run (login keyboard, document listing, document history endpoint) and had to be patched locally. Playwright would be more resilient to these surface-level changes because it interacts with the rendered page rather than raw API calls — but it would be slower, heavier, and would still break on authentication flow changes.

## When to reconsider

Switch to Playwright if:
- BNP introduces bot detection (CAPTCHA, device fingerprinting) that blocks woob's requests but not a real browser
- The number of required patches accumulates to the point where maintaining them costs more than writing a Playwright script
- The use case expands to require UI interaction (e.g., initiating transfers) that the woob module does not support
