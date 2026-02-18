#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${ANDROID_BUILD_TOOLS_VERSION:-}" ]]; then
  echo "ANDROID_BUILD_TOOLS_VERSION is required." >&2
  exit 1
fi

android_sdk_root="${RUNNER_TEMP}/android-sdk"
echo "ANDROID_SDK_ROOT=${android_sdk_root}" >> "${GITHUB_ENV}"
echo "ANDROID_HOME=${android_sdk_root}" >> "${GITHUB_ENV}"

mkdir -p "${android_sdk_root}/cmdline-tools"
curl -fsSL "https://dl.google.com/android/repository/commandlinetools-linux-13114758_latest.zip" -o "${RUNNER_TEMP}/cmdline-tools.zip"
unzip -q "${RUNNER_TEMP}/cmdline-tools.zip" -d "${RUNNER_TEMP}/cmdline-tools-unpacked"
mkdir -p "${android_sdk_root}/cmdline-tools/latest"
mv "${RUNNER_TEMP}/cmdline-tools-unpacked/cmdline-tools/"* "${android_sdk_root}/cmdline-tools/latest/"

echo "${android_sdk_root}/cmdline-tools/latest/bin" >> "${GITHUB_PATH}"

set +o pipefail
yes | "${android_sdk_root}/cmdline-tools/latest/bin/sdkmanager" --sdk_root="${android_sdk_root}" --licenses > /dev/null
set -o pipefail

"${android_sdk_root}/cmdline-tools/latest/bin/sdkmanager" --sdk_root="${android_sdk_root}" "build-tools;${ANDROID_BUILD_TOOLS_VERSION}"
echo "${android_sdk_root}/build-tools/${ANDROID_BUILD_TOOLS_VERSION}" >> "${GITHUB_PATH}"
