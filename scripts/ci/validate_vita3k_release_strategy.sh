#!/usr/bin/env bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required to validate Vita3K release strategy." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to validate Vita3K release strategy." >&2
  exit 1
fi

upstream_repository="${UPSTREAM_REPOSITORY:-Vita3K/Vita3K}"
api_base="https://api.github.com/repos/${upstream_repository}"

headers=("Accept: application/vnd.github+json" "X-GitHub-Api-Version: 2022-11-28")

if [[ -n "${GH_TOKEN:-}" ]]; then
  headers+=("Authorization: Bearer ${GH_TOKEN}")
fi

curl_args=("-fsSL")
for header in "${headers[@]}"; do
  curl_args+=("-H" "$header")
done

releases_json=$(curl "${curl_args[@]}" "${api_base}/releases?per_page=2")
release_count=$(printf '%s' "$releases_json" | jq -r 'length')

if [[ "$release_count" -ne 1 ]]; then
  known_tags=$(printf '%s' "$releases_json" | jq -r '[.[].tag_name] | join(", ")')
  echo "Unexpected Vita3K release strategy: expected exactly one GitHub release with tag 'continuous', found ${release_count}. Tags: [${known_tags}]" >&2
  echo "Please update src/vita3k_upstream.py and CI scripts to match the new upstream strategy." >&2
  exit 1
fi

list_tag=$(printf '%s' "$releases_json" | jq -r '.[0].tag_name // ""')
if [[ "$list_tag" != "continuous" ]]; then
  echo "Unexpected Vita3K release tag strategy: expected only 'continuous', found '${list_tag}'." >&2
  echo "Please update src/vita3k_upstream.py and CI scripts to match the new upstream strategy." >&2
  exit 1
fi

continuous_json=$(curl "${curl_args[@]}" "${api_base}/releases/tags/continuous")

list_id=$(printf '%s' "$releases_json" | jq -r '.[0].id // ""')
continuous_id=$(printf '%s' "$continuous_json" | jq -r '.id // ""')
if [[ -n "$list_id" && -n "$continuous_id" && "$list_id" != "$continuous_id" ]]; then
  echo "Unexpected Vita3K release mismatch: /releases and /releases/tags/continuous do not reference the same release." >&2
  echo "Please update src/vita3k_upstream.py and CI scripts to match the new upstream strategy." >&2
  exit 1
fi

has_android_asset=$(printf '%s' "$continuous_json" | jq -r '[.assets[]?.name == "android-latest.apk"] | any')
if [[ "$has_android_asset" != "true" ]]; then
  echo "Unexpected Vita3K assets: 'android-latest.apk' is missing from the continuous release." >&2
  echo "Please update src/vita3k_upstream.py and CI scripts to match the new upstream strategy." >&2
  exit 1
fi

release_body=$(printf '%s' "$continuous_json" | jq -r '.body // ""')

if ! printf '%s' "$release_body" | grep -Eq 'Vita3K Build:[[:space:]]*[0-9]+'; then
  echo "Unexpected Vita3K release body: missing 'Vita3K Build: <number>' metadata." >&2
  echo "Please update src/vita3k_upstream.py and CI scripts to match the new upstream strategy." >&2
  exit 1
fi

if ! printf '%s' "$release_body" | grep -Eq 'Corresponding commit:[[:space:]]*[0-9a-fA-F]{40}'; then
  echo "Unexpected Vita3K release body: missing 'Corresponding commit: <sha>' metadata." >&2
  echo "Please update src/vita3k_upstream.py and CI scripts to match the new upstream strategy." >&2
  exit 1
fi

echo "Validated upstream Vita3K release strategy: single 'continuous' release with android-latest.apk and expected metadata."
