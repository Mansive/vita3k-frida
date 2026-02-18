#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${PACKAGE_NAME:-}" ]]; then
  echo "PACKAGE_NAME is required." >&2
  exit 1
fi

if [[ -z "${BUILD_NUMBER:-}" ]]; then
  echo "BUILD_NUMBER is required." >&2
  exit 1
fi

if [[ -z "${UNSIGNED_APK:-}" ]]; then
  echo "UNSIGNED_APK is required." >&2
  exit 1
fi

if [[ -z "${ANDROID_KEYSTORE_PASS:-}" ]]; then
  echo "ANDROID_KEYSTORE_PASS secret is required." >&2
  exit 1
fi

keystore_path="${RUNNER_TEMP}/keystore.p12"
if [[ ! -f "$keystore_path" ]]; then
  echo "Keystore not found at $keystore_path" >&2
  exit 1
fi

final_apk="dist/${PACKAGE_NAME}_${BUILD_NUMBER}_frida.apk"
mkdir -p dist

zipalign -p -v 4 "$UNSIGNED_APK" "$final_apk"
apksigner sign \
  --ks "$keystore_path" \
  --ks-key-alias "vita3k-puni" \
  --ks-pass "pass:${ANDROID_KEYSTORE_PASS}" \
  --key-pass "pass:${ANDROID_KEYSTORE_PASS}" \
  "$final_apk"

apksigner verify --verbose --print-certs "$final_apk"
zipalign -c -v 4 "$final_apk"

echo "final_apk=$final_apk" >> "${GITHUB_OUTPUT}"
