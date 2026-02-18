#!/usr/bin/env bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required to parse JSON." >&2
  exit 1
fi

downloads_dir="${1:-downloads}"

metadata_json=$(python src/vita3k_upstream.py --download --json --downloads-dir "${downloads_dir}")
apk_path=$(printf '%s' "$metadata_json" | jq -r '.download_path')

echo "apk_path=${apk_path}" >> "${GITHUB_OUTPUT}"
