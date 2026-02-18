#!/usr/bin/env bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required to parse JSON." >&2
  exit 1
fi

metadata_json=$(python src/vita3k_upstream.py --check --json)

build_number=$(printf '%s' "$metadata_json" | jq -r '.build_number')
commit_sha=$(printf '%s' "$metadata_json" | jq -r '.commit_sha')
apk_name=$(printf '%s' "$metadata_json" | jq -r '.apk_name')
apk_url=$(printf '%s' "$metadata_json" | jq -r '.apk_url')
apk_sha256=$(printf '%s' "$metadata_json" | jq -r '.apk_sha256')
release_tag="v${build_number}"

{
  echo "build_number=${build_number}"
  echo "commit_sha=${commit_sha}"
  echo "apk_name=${apk_name}"
  echo "apk_url=${apk_url}"
  echo "apk_sha256=${apk_sha256}"
  echo "release_tag=${release_tag}"
} >> "${GITHUB_OUTPUT}"
