import argparse
import json
import lzma
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable, Mapping

import lief
import requests


DEFAULT_FRIDA_VERSION = "17.6.2"
DEFAULT_FRIDA_LISTEN_ADDRESS = "127.0.0.1"
DEFAULT_FRIDA_LISTEN_PORT = 27042
DEFAULT_ABI = "arm64-v8a"
DEFAULT_CACHE_DIR = Path(".cache") / "frida"
DEFAULT_TIMEOUT_SECONDS = 300

FRIDA_RELEASES_BASE_URL = "https://github.com/frida/frida/releases/download"
ANDROID_NS = "http://schemas.android.com/apk/res/android"
PREFERRED_TARGET_LIB_NAMES = (
    "libVita3K.so",
    "libvita3k.so",
    "libmain.so",
    "libnative-lib.so",
)

INTERNAL_GADGET_NAME = "libfrida-gadget.so"
INTERNAL_CONFIG_NAME = "libfrida-gadget.config.so"


HttpGet = Callable[..., Any]
LiefParser = Callable[[str], Any]
DEFAULT_LIEF_PARSER = getattr(lief, "parse")


def frida_gadget_filename(version: str) -> str:
    return f"frida-gadget-{version}-android-arm64.so"


def build_frida_gadget_url(version: str) -> str:
    xz_name = f"{frida_gadget_filename(version)}.xz"
    return f"{FRIDA_RELEASES_BASE_URL}/{version}/{xz_name}"


def decompress_xz_bytes(data: bytes) -> bytes:
    return lzma.decompress(data, format=lzma.FORMAT_XZ)


def _download_file(
    url: str,
    destination: Path,
    *,
    http_get: HttpGet = requests.get,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    response = http_get(url, timeout=timeout, stream=True)
    response.raise_for_status()

    with destination.open("wb") as output_file:
        if hasattr(response, "iter_content"):
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output_file.write(chunk)
        else:
            output_file.write(response.content)


def _extract_xz_file(source_xz: Path, destination_so: Path) -> None:
    destination_so.parent.mkdir(parents=True, exist_ok=True)
    with (
        lzma.open(source_xz, mode="rb") as source_file,
        destination_so.open("wb") as output_file,
    ):
        shutil.copyfileobj(source_file, output_file)


def ensure_frida_gadget_so(
    version: str,
    cache_dir: Path,
    *,
    http_get: HttpGet = requests.get,
) -> Path:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    so_name = frida_gadget_filename(version)
    so_path = cache_dir / so_name
    xz_path = cache_dir / f"{so_name}.xz"

    if so_path.exists():
        return so_path

    if not xz_path.exists():
        _download_file(
            build_frida_gadget_url(version),
            xz_path,
            http_get=http_get,
        )

    _extract_xz_file(xz_path, so_path)
    return so_path


def build_frida_config(
    *,
    listen_address: str = DEFAULT_FRIDA_LISTEN_ADDRESS,
    listen_port: int = DEFAULT_FRIDA_LISTEN_PORT,
) -> dict[str, Any]:
    return {
        "interaction": {
            "type": "listen",
            "address": listen_address,
            "port": listen_port,
            "on_load": "resume",
        }
    }


def patch_manifest(
    xml_text: str,
    *,
    android_version_code: int | None = None,
) -> str:
    ET.register_namespace("android", ANDROID_NS)
    root = ET.fromstring(xml_text)

    application = root.find("application")
    if application is None:
        raise ValueError("AndroidManifest.xml is missing the <application> tag")

    extract_native_libs_attr = f"{{{ANDROID_NS}}}extractNativeLibs"
    application.set(extract_native_libs_attr, "true")

    if android_version_code is not None:
        version_code_attr = f"{{{ANDROID_NS}}}versionCode"
        root.set(version_code_attr, str(android_version_code))

    return ET.tostring(root, encoding="unicode")


def patch_manifest_file(
    manifest_path: Path,
    *,
    android_version_code: int | None = None,
) -> None:
    manifest_text = manifest_path.read_text(encoding="utf-8")
    patched_text = patch_manifest(
        manifest_text,
        android_version_code=android_version_code,
    )
    manifest_path.write_text(patched_text, encoding="utf-8")


def select_target_library(arm64_dir: Path, target_lib: str | None = None) -> Path:
    if target_lib:
        candidate = arm64_dir / target_lib
        if not candidate.exists():
            raise FileNotFoundError(
                f"Target library '{target_lib}' was not found in {arm64_dir}"
            )
        return candidate

    for name in PREFERRED_TARGET_LIB_NAMES:
        candidate = arm64_dir / name
        if candidate.exists():
            return candidate

    so_files = [
        file_path for file_path in arm64_dir.glob("*.so") if file_path.is_file()
    ]
    if not so_files:
        raise FileNotFoundError(f"No shared libraries were found in {arm64_dir}")

    return max(so_files, key=lambda path: path.stat().st_size)


def inject_needed_library(
    target_lib_path: Path,
    *,
    dependency_name: str = INTERNAL_GADGET_NAME,
    parser: LiefParser = DEFAULT_LIEF_PARSER,
) -> bool:
    binary = parser(str(target_lib_path))
    if binary is None:
        raise RuntimeError(f"Failed to parse ELF file: {target_lib_path}")

    existing_libraries = {str(library_name) for library_name in binary.libraries}
    if dependency_name in existing_libraries:
        return False

    binary.add_library(dependency_name)
    binary.write(str(target_lib_path))
    return True


def inject_gadget_into_unpacked_dir(
    *,
    unpacked_dir: Path,
    gadget_so_path: Path,
    config: Mapping[str, Any],
    abi: str = DEFAULT_ABI,
    target_lib: str | None = None,
    parser: LiefParser = DEFAULT_LIEF_PARSER,
) -> Path:
    arm64_dir = unpacked_dir / "lib" / abi
    if not arm64_dir.exists():
        raise FileNotFoundError(f"ABI directory not found: {arm64_dir}")

    target_lib_path = select_target_library(arm64_dir, target_lib=target_lib)
    inject_needed_library(target_lib_path, parser=parser)

    destination_gadget_path = arm64_dir / INTERNAL_GADGET_NAME
    shutil.copy2(gadget_so_path, destination_gadget_path)

    config_path = arm64_dir / INTERNAL_CONFIG_NAME
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    return target_lib_path


def strip_non_target_abis(unpacked_dir: Path, *, keep_abis: set[str]) -> list[str]:
    lib_root = unpacked_dir / "lib"
    if not lib_root.exists():
        raise FileNotFoundError(f"No lib directory found at {lib_root}")

    removed: list[str] = []
    keep_found = False

    for abi_dir in lib_root.iterdir():
        if not abi_dir.is_dir():
            continue

        if abi_dir.name in keep_abis:
            keep_found = True
            continue

        shutil.rmtree(abi_dir)
        removed.append(abi_dir.name)

    if not keep_found:
        raise FileNotFoundError(
            f"Required ABI directories not found: {sorted(keep_abis)}"
        )

    return removed


def run_command(command: list[str | Path], *, cwd: Path | None = None) -> None:
    command_parts = [str(part) for part in command]
    subprocess.run(command_parts, check=True, cwd=str(cwd) if cwd else None)


def decode_apk(apktool_jar: Path, apk_path: Path, output_dir: Path) -> None:
    run_command(
        [
            "java",
            "-jar",
            apktool_jar,
            "d",
            apk_path,
            "-o",
            output_dir,
            "-f",
            "-m",
        ]
    )


def build_apk(apktool_jar: Path, unpacked_dir: Path, output_apk_path: Path) -> None:
    output_apk_path.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        ["java", "-jar", apktool_jar, "b", unpacked_dir, "-o", output_apk_path, "-f"]
    )


def _run_repack(
    *,
    apk_path: Path,
    output_apk_path: Path,
    apktool_jar: Path,
    frida_version: str,
    cache_dir: Path,
    listen_address: str,
    listen_port: int,
    work_dir: Path,
    target_lib: str | None,
    keep_all_abis: bool,
    android_version_code: int | None,
) -> Path:
    unpacked_dir = work_dir / "unpacked"
    if unpacked_dir.exists():
        shutil.rmtree(unpacked_dir)

    decode_apk(apktool_jar, apk_path, unpacked_dir)

    if not keep_all_abis:
        strip_non_target_abis(unpacked_dir, keep_abis={DEFAULT_ABI})

    gadget_so_path = ensure_frida_gadget_so(frida_version, cache_dir)
    frida_config = build_frida_config(
        listen_address=listen_address,
        listen_port=listen_port,
    )

    inject_gadget_into_unpacked_dir(
        unpacked_dir=unpacked_dir,
        gadget_so_path=gadget_so_path,
        config=frida_config,
        target_lib=target_lib,
    )

    manifest_path = unpacked_dir / "AndroidManifest.xml"
    patch_manifest_file(
        manifest_path,
        android_version_code=android_version_code,
    )

    build_apk(apktool_jar, unpacked_dir, output_apk_path)
    return output_apk_path


def repack_apk(
    *,
    apk_path: Path,
    output_apk_path: Path,
    apktool_jar: Path,
    frida_version: str = DEFAULT_FRIDA_VERSION,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    listen_address: str = DEFAULT_FRIDA_LISTEN_ADDRESS,
    listen_port: int = DEFAULT_FRIDA_LISTEN_PORT,
    work_dir: Path | None = None,
    target_lib: str | None = None,
    keep_all_abis: bool = False,
    android_version_code: int | None = None,
) -> Path:
    apk_path = Path(apk_path)
    output_apk_path = Path(output_apk_path)
    apktool_jar = Path(apktool_jar)

    if not apk_path.exists():
        raise FileNotFoundError(f"APK file does not exist: {apk_path}")

    if not apktool_jar.exists():
        raise FileNotFoundError(f"apktool jar does not exist: {apktool_jar}")

    if work_dir is not None:
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        return _run_repack(
            apk_path=apk_path,
            output_apk_path=output_apk_path,
            apktool_jar=apktool_jar,
            frida_version=frida_version,
            cache_dir=Path(cache_dir),
            listen_address=listen_address,
            listen_port=listen_port,
            work_dir=work_dir,
            target_lib=target_lib,
            keep_all_abis=keep_all_abis,
            android_version_code=android_version_code,
        )

    with tempfile.TemporaryDirectory(prefix="vita3k-repack-") as temp_dir:
        return _run_repack(
            apk_path=apk_path,
            output_apk_path=output_apk_path,
            apktool_jar=apktool_jar,
            frida_version=frida_version,
            cache_dir=Path(cache_dir),
            listen_address=listen_address,
            listen_port=listen_port,
            work_dir=Path(temp_dir),
            target_lib=target_lib,
            keep_all_abis=keep_all_abis,
            android_version_code=android_version_code,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repack an APK with Frida Gadget (unsigned output)"
    )
    parser.add_argument("--apk", required=True, help="Path to the input APK")
    parser.add_argument(
        "--out", required=True, help="Path to the unsigned repacked APK"
    )
    parser.add_argument("--apktool-jar", required=True, help="Path to apktool jar")
    parser.add_argument("--frida-version", default=DEFAULT_FRIDA_VERSION)
    parser.add_argument("--listen-address", default=DEFAULT_FRIDA_LISTEN_ADDRESS)
    parser.add_argument("--listen-port", type=int, default=DEFAULT_FRIDA_LISTEN_PORT)
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument(
        "--work-dir",
        help="Optional working directory. Defaults to a temporary directory.",
    )
    parser.add_argument(
        "--target-lib", help="Specific library filename in arm64-v8a to inject"
    )
    parser.add_argument(
        "--keep-all-abis",
        action="store_true",
        help="Keep all native ABI directories instead of stripping to arm64-v8a",
    )
    parser.add_argument(
        "--android-version-code",
        type=int,
        help="Override AndroidManifest android:versionCode for update monotonicity",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    repack_apk(
        apk_path=Path(args.apk),
        output_apk_path=Path(args.out),
        apktool_jar=Path(args.apktool_jar),
        frida_version=args.frida_version,
        cache_dir=Path(args.cache_dir),
        listen_address=args.listen_address,
        listen_port=args.listen_port,
        work_dir=Path(args.work_dir) if args.work_dir else None,
        target_lib=args.target_lib,
        keep_all_abis=args.keep_all_abis,
        android_version_code=args.android_version_code,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
