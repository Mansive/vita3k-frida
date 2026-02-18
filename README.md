# Vita3K Frida APK Repacker

This repository provides Android releases of [Vita3K](https://github.com/Vita3K/Vita3K) repacked with [frida-gadget](https://github.com/frida/frida).

## Important updater note

Vita3K's built-in updater currently doesn't work. It's suggested to update through the app through Obtanium instead. To disable the in-app update check:

- `Configuration` -> `Settings` -> `Emulator` -> uncheck `Check For Updates`

Vita3K's built-in updater downloads the official `continuous/android-latest.apk`, which cannot install over a differently signed APK.

## Local scripts

- `src/vita3k_upstream.py`
  - `--check --json`: print latest continuous metadata without downloading.
  - `--download --json`: download latest Android APK into `downloads/`.
- `src/repack.py`
  - Rebuilds APK with Frida Gadget and outputs an unsigned APK.
  - Default Frida config listens on `127.0.0.1:27042`.
  - Override with `--listen-address` if needed.
  - Strips non-`arm64-v8a` ABI directories by default.
  - Use `--keep-all-abis` to keep `x86_64`, `armeabi-v7a`, etc.

### Repack CLI flags

- `--apk`: input APK path (required)
- `--out`: output unsigned APK path (required)
- `--apktool-jar`: apktool jar path (required)
- `--frida-version`: Frida Gadget version (default `17.6.2`)
- `--listen-address`: Frida listen address (default `127.0.0.1`)
- `--listen-port`: Frida listen port (default `27042`)
- `--cache-dir`: Frida gadget cache directory (default `.cache/frida`)
- `--work-dir`: optional working directory for apktool output
- `--target-lib`: force a specific `arm64-v8a` library to inject (`libVita3K.so` recommended)
- `--keep-all-abis`: keep all ABI folders (disable arm64-only trimming)
- `--android-version-code`: set `AndroidManifest.xml` `android:versionCode`

## Frida Gadget source

`src/repack.py` fetches:

- Release: `https://github.com/frida/frida/releases`
- Asset: `frida-gadget-{version}-android-arm64.so.xz`

## Release tag strategy

- Base tag: `v0.0.{upstream_build_number}`
- Rebuild tags: `v0.0.{upstream_build_number}-r1`, `-r2`, ...

## GitHub Actions secrets

Create and set these repository secrets:

- `ANDROID_KEYSTORE_P12_B64`
- `ANDROID_KEYSTORE_PASS`

The key alias is fixed to `vita3k-puni`.

### One-time key generation (.p12)

```bash
keytool -genkeypair \
  -storetype PKCS12 \
  -keystore vita3k-frida.p12 \
  -alias vita3k-puni \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -storepass "<PASSWORD>" \
  -keypass "<PASSWORD>" \
  -dname "CN=vita3k-frida, OU=CI, O=vita3k-frida, L=NA, ST=NA, C=US"
```

Base64-encode the generated file and store it in `ANDROID_KEYSTORE_P12_B64`.

## Tests

```bash
python -m pytest -q
```

## act

The workflow supports local `act` runs. When `ACT=true`, signing and GitHub release creation are skipped, but the unsigned APK artifact is still uploaded.

For local `act` rebuild-tag testing, create:

```json
{
  "inputs": {
    "rebuild": "true"
  }
}
```

Then run:

```bash
act -W ".github/workflows/vita3k-frida.yml" workflow_dispatch -e ".act-rebuild.json" --artifact-server-path ".act-artifacts"
```
