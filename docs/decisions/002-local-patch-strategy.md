# ADR-002: Local patch strategy — copy files over fork or upstream contribution

**Date:** 2026-04-19  
**Status:** Accepted

## Context

The upstream woob `bnp` module (version 3.7, released 2024-10-29) is broken against the current BNP web interface in three ways:

1. Login keyboard changed from image-based to JS-generated button grid
2. Document listing API requires a `code` parameter that upstream does not pass
3. Document history is capped at 6 months; a separate endpoint (`rechercheCriteresDemat`) provides 5 years

These required changes to three files: `pages.py`, `browser.py`, `document_pages.py`.

Three strategies were available:

1. **Contribute upstream** — submit PRs to `gitlab.com/woob/woob`
2. **Fork woob** — maintain a private fork with the fixes applied
3. **Patch in place** — copy the fixed files into this repo under `patches/` and apply them to the live module location via `apply_patches.py`

## Decision

Patch in place (option 3).

## Rationale

Contributing upstream is the right long-term answer but has friction: the woob project requires understanding their testing infrastructure, the maintainer response time is unknown, and the patches needed immediately. Upstream contribution remains possible later without changing this local strategy.

Forking woob would mean maintaining a full Python package fork — tracking upstream releases, managing a separate install source, and updating `requirements.txt` to point at the fork. That overhead is disproportionate for three file-level fixes.

Patching in place keeps the fixes version-controlled in this repo, co-located with the scripts that use them, and reapplicable with a single command (`apply_patches.py`). The cost is that `woob config update` silently overwrites the patches — mitigated by the explicit warning in CLAUDE.md and the fast reapplication path.

## Constraints that follow

- `patches/bnp/pp/` is the source of truth for all three patched files. Never edit the live module files directly — always edit `patches/` and re-run `apply_patches.py`.
- `apply_patches.py` must be run after every `woob config update`.
- When woob releases a new version that fixes any of these issues upstream, the corresponding patch file should be removed from `patches/` and `apply_patches.py` updated.

## When to reconsider

Switch to a fork if the number of patched files grows beyond ~5, or if the patches require changes to woob core rather than just the `bnp` module.

Consider contributing upstream once the fixes are stable and verified — the `rechercheCriteresDemat` change in particular is useful to all woob BNP users.
