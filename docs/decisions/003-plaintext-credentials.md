# ADR-003: Plaintext credentials for local use

**Date:** 2026-04-19  
**Status:** Accepted

## Context

woob stores backend credentials (BNP login and password) in `%USERPROFILE%/.config/woob/backends`, an INI file. By default the file is plaintext. woob supports an alternative called `pass-backends`: credential values can be shell commands enclosed in backticks, executed at runtime to retrieve secrets from an encrypted store (e.g. `pass`, `gopass`).

## Decision

Accept plaintext storage. Do not configure `pass-backends`.

## Rationale

This installation runs on a single-user Windows machine used exclusively by the account holder. The threat model for plaintext credentials on a personal, non-shared machine is: physical access or remote compromise — both of which give an attacker access to the BNP session directly anyway.

`pass-backends` on Windows requires `gopass` (the native Windows port), a GPG keypair, and a password store to be set up and maintained. The incremental security benefit on this machine does not justify that operational overhead.

The file is created with restrictive permissions by woob on Unix; on Windows, permissions are not set by woob (`sys.platform == "win32"` branch skips `chmod`). The file resides in the user profile directory, which is user-owned by default.

## Constraints that follow

- This decision is conditional on the machine remaining single-user and not internet-facing via remote shell (SSH, RDP with multiple users, etc.).
- Do not commit the `backends` file to version control under any circumstances.
- If the machine's threat model changes (shared access, cloud VM, CI environment), configure `pass-backends` with `gopass` before continuing to use this project.

## When to reconsider

Reconfigure with `pass-backends` if:
- The machine gains additional user accounts or remote shell access
- The project is adapted to run in a CI/CD pipeline or cloud environment
- BNP credentials are rotated infrequently and the risk of a lingering plaintext copy is unacceptable
