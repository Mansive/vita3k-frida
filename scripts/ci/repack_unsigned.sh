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

if [[ -z "${APK_PATH:-}" ]]; then
  echo "APK_PATH is required." >&2
  exit 1
fi

if [[ -z "${APKTOOL_JAR:-}" ]]; then
  echo "APKTOOL_JAR is required." >&2
  exit 1
fi

unsigned_apk="${RUNNER_TEMP}/${PACKAGE_NAME}_${BUILD_NUMBER}_frida-unsigned.apk"

python src/repack.py \
  --apk "$APK_PATH" \
  --out "$unsigned_apk" \
  --apktool-jar "$APKTOOL_JAR" \
  --target-lib "libVita3K.so" \
  --android-version-code "$BUILD_NUMBER"

echo "unsigned_apk=$unsigned_apk" >> "${GITHUB_OUTPUT}"
