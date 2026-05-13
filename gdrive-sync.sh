#!/usr/bin/env bash
# Sync the local workspace/ folder with lmnp-gdrive:workspace/
#
# Usage:
#   bash gdrive-sync.sh up    — upload local workspace/ to Google Drive
#   bash gdrive-sync.sh down  — download Google Drive workspace/ to local
set -euo pipefail

REMOTE="lmnp-gdrive-user:Workspace"
LOCAL="workspace"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve rclone binary
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
if ! "${RCLONE}" listremotes 2>/dev/null | grep -qx "lmnp-gdrive-user:"; then
    echo "Remote lmnp-gdrive-user not configured. Ensure .claude/gdrive-user-token.json exists and run the session-start hook." >&2
    exit 1
fi

cd "${SCRIPT_DIR}"

case "${1:-}" in
    up)
        if [[ ! -d "${LOCAL}" ]]; then
            echo "Local ${LOCAL}/ not found." >&2
            exit 1
        fi
        echo "Uploading ${LOCAL}/ → ${REMOTE}/"
        "${RCLONE}" copy "${LOCAL}/" "${REMOTE}/" --progress
        echo "Done."
        ;;
    down)
        mkdir -p "${LOCAL}"
        echo "Downloading ${REMOTE}/ → ${LOCAL}/"
        "${RCLONE}" copy "${REMOTE}/" "${LOCAL}/" --progress
        echo "Done."
        ;;
    *)
        echo "Usage: bash gdrive-sync.sh <up|down>"
        echo "  up   — upload local ${LOCAL}/ to Google Drive"
        echo "  down — download Google Drive workspace/ to local ${LOCAL}/"
        exit 1
        ;;
esac
