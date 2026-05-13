#!/usr/bin/env bash
# Ensures the lmnp-gdrive-user rclone remote is configured using the stored OAuth token.
set -euo pipefail

REMOTE_NAME="lmnp-gdrive-user"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOKEN_FILE="${SCRIPT_DIR}/../gdrive-user-token.json"

if [[ ! -f "${TOKEN_FILE}" ]]; then
    echo "[session-start] ${TOKEN_FILE} not found — skipping rclone gdrive setup" >&2
    exit 0
fi

# Install rclone if missing
if ! command -v rclone &>/dev/null; then
    echo "[session-start] rclone not found, installing…"
    if command -v apt-get &>/dev/null; then
        apt-get install -y rclone >/dev/null 2>&1
        echo "[session-start] rclone installed via apt"
    else
        tmp=$(mktemp -d)
        curl -fsSL "https://downloads.rclone.org/rclone-current-linux-amd64.zip" -o "${tmp}/rclone.zip"
        unzip -q "${tmp}/rclone.zip" -d "${tmp}"
        mkdir -p "${HOME}/.local/bin"
        cp "${tmp}"/rclone-*-linux-amd64/rclone "${HOME}/.local/bin/rclone"
        chmod +x "${HOME}/.local/bin/rclone"
        rm -rf "${tmp}"
        export PATH="${HOME}/.local/bin:${PATH}"
        echo "[session-start] rclone installed to ~/.local/bin/rclone"
    fi
fi

TOKEN="$(cat "${TOKEN_FILE}")"

# Create or update the remote with the current token
if ! rclone listremotes 2>/dev/null | grep -qx "${REMOTE_NAME}:"; then
    rclone config create "${REMOTE_NAME}" drive \
        scope drive \
        token "${TOKEN}" \
        root_folder_id 1mqKDoqwFC2k-RrgCQMy3f4WaDFwDPsE3 \
        --non-interactive >/dev/null
    echo "[session-start] rclone remote '${REMOTE_NAME}' created"
else
    rclone config update "${REMOTE_NAME}" \
        token "${TOKEN}" \
        root_folder_id 1mqKDoqwFC2k-RrgCQMy3f4WaDFwDPsE3 \
        --non-interactive >/dev/null 2>&1 || true
    echo "[session-start] rclone remote '${REMOTE_NAME}' updated"
fi
