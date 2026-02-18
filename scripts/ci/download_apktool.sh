#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${APKTOOL_VERSION:-}" ]]; then
  echo "APKTOOL_VERSION is required." >&2
  exit 1
fi

apktool_jar="${RUNNER_TEMP}/apktool_${APKTOOL_VERSION}.jar"
curl -fsSL "https://github.com/iBotPeaches/Apktool/releases/download/v${APKTOOL_VERSION}/apktool_${APKTOOL_VERSION}.jar" -o "$apktool_jar"

echo "apktool_jar=$apktool_jar" >> "${GITHUB_OUTPUT}"
