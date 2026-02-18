#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${ANDROID_KEYSTORE_P12_B64:-}" ]]; then
  echo "ANDROID_KEYSTORE_P12_B64 secret is required." >&2
  exit 1
fi

printf '%s' "$ANDROID_KEYSTORE_P12_B64" | base64 --decode > "$RUNNER_TEMP/keystore.p12"
