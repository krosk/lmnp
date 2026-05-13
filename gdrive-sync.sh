#!/usr/bin/env bash
# Upload local bookkeeping artefacts to lmnp-gdrive:lmnp/
set -euo pipefail

REMOTE="lmnp-gdrive:lmnp"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure rclone is available
RCLONE=rclone
if ! command -v rclone &>/dev/null; then
    if [[ -x "${HOME}/.local/bin/rclone" ]]; then
        RCLONE="${HOME}/.local/bin/rclone"
    else
        echo "rclone not found. Run the session-start hook first." >&2
        exit 1
    fi
fi

# Ensure the remote is configured
if ! "${RCLONE}" listremotes 2>/dev/null | grep -qx "lmnp-gdrive:"; then
    echo "Remote lmnp-gdrive not configured. Provide gdrive-sa.json and let the hook run." >&2
    exit 1
fi

cd "${SCRIPT_DIR}"

synced=0

if [[ -f "LMNP.xlsx" ]]; then
    echo "Uploading LMNP.xlsx → ${REMOTE}/"
    "${RCLONE}" copy LMNP.xlsx "${REMOTE}/" --progress
    synced=$((synced + 1))
else
    echo "LMNP.xlsx not found locally, skipping."
fi

if [[ -d "Justificatifs" ]]; then
    echo "Syncing Justificatifs/ → ${REMOTE}/Justificatifs/"
    "${RCLONE}" copy Justificatifs/ "${REMOTE}/Justificatifs/" --progress
    synced=$((synced + 1))
else
    echo "Justificatifs/ not found locally, skipping."
fi

if [[ ${synced} -eq 0 ]]; then
    echo "Nothing to sync."
else
    echo "Done."
fi
