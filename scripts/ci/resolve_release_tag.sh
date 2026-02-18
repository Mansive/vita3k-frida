#!/usr/bin/env bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required to parse JSON." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to call GitHub API." >&2
  exit 1
fi

if [[ -z "${BASE_TAG:-}" ]]; then
  echo "BASE_TAG is required." >&2
  exit 1
fi

if [[ -z "${GITHUB_REPOSITORY:-}" ]]; then
  echo "GITHUB_REPOSITORY is required." >&2
  exit 1
fi

rebuild="${REBUILD:-false}"

api_url="https://api.github.com/repos/${GITHUB_REPOSITORY}/releases?per_page=100"
headers=("Accept: application/vnd.github+json" "X-GitHub-Api-Version: 2022-11-28")

if [[ -n "${GH_TOKEN:-}" ]]; then
  headers+=("Authorization: Bearer ${GH_TOKEN}")
fi

curl_args=("-fsSL")
for header in "${headers[@]}"; do
  curl_args+=("-H" "$header")
done

tags_json=$(curl "${curl_args[@]}" "$api_url" || true)

if [[ -z "$tags_json" ]]; then
  tags_json="[]"
fi

base_exists=$(printf '%s' "$tags_json" | jq -r --arg base "$BASE_TAG" '[.[].tag_name == $base] | any')

if [[ "$base_exists" == "false" ]]; then
  {
    echo "build=true"
    echo "release_tag=${BASE_TAG}"
  } >> "${GITHUB_OUTPUT}"
  exit 0
fi

if [[ "$rebuild" != "true" ]]; then
  {
    echo "build=false"
    echo "release_tag=${BASE_TAG}"
  } >> "${GITHUB_OUTPUT}"
  exit 0
fi

suffix_pattern="^${BASE_TAG}-r[0-9]+$"
max_suffix=$(printf '%s' "$tags_json" | jq -r --arg pattern "$suffix_pattern" '
  [ .[].tag_name | select(test($pattern))
    | capture("-r(?<n>[0-9]+)$").n | tonumber ]
  | max // 0
')

next_suffix=$((max_suffix + 1))
resolved_tag="${BASE_TAG}-r${next_suffix}"

{
  echo "build=true"
  echo "release_tag=${resolved_tag}"
} >> "${GITHUB_OUTPUT}"
