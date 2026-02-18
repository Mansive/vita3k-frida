import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable

import requests


PACKAGE_NAME = "org.vita3k.emulator"
CONTINUOUS_RELEASE_API_URL = (
    "https://api.github.com/repos/Vita3K/Vita3K/releases/tags/continuous"
)
DEFAULT_TIMEOUT_SECONDS = 300

BUILD_NUMBER_REGEX = re.compile(r"Vita3K Build:\s*(\d+)")
COMMIT_SHA_REGEX = re.compile(r"Corresponding commit:\s*([0-9a-fA-F]{40})")
ANDROID_ASSET_NAME = "android-latest.apk"

HttpGet = Callable[..., Any]


def fetch_continuous_release_payload(
    *,
    http_get: HttpGet = requests.get,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    response = http_get(CONTINUOUS_RELEASE_API_URL, timeout=timeout)
    response.raise_for_status()
    return response.json()


def extract_build_number(release_body: str) -> int:
    match = BUILD_NUMBER_REGEX.search(release_body)
    if not match:
        raise ValueError("Unable to parse Vita3K build number from release body")
    return int(match.group(1))


def extract_commit_sha(release_body: str) -> str:
    match = COMMIT_SHA_REGEX.search(release_body)
    if not match:
        raise ValueError(
            "Unable to parse Vita3K corresponding commit SHA from release body"
        )
    return match.group(1).lower()


def extract_android_asset(release_payload: dict[str, Any]) -> dict[str, Any]:
    assets = release_payload.get("assets") or []
    for asset in assets:
        if asset.get("name") == ANDROID_ASSET_NAME:
            return asset

    raise ValueError(
        "Unable to find android-latest.apk in Vita3K continuous release assets"
    )


def build_metadata_from_release(release_payload: dict[str, Any]) -> dict[str, Any]:
    release_body = str(release_payload.get("body") or "")
    android_asset = extract_android_asset(release_payload)

    digest = str(android_asset.get("digest") or "")
    if digest.startswith("sha256:"):
        apk_sha256 = digest.split(":", maxsplit=1)[1]
    else:
        apk_sha256 = digest

    build_number = extract_build_number(release_body)

    return {
        "package_name": PACKAGE_NAME,
        "upstream_tag": "continuous",
        "build_number": build_number,
        "commit_sha": extract_commit_sha(release_body),
        "apk_name": android_asset["name"],
        "apk_url": android_asset["browser_download_url"],
        "apk_sha256": apk_sha256,
        "release_updated_at": release_payload.get("updated_at"),
        "release_tag": f"v{build_number}",
    }


def fetch_latest_vita3k_metadata(
    *,
    http_get: HttpGet = requests.get,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    release_payload = fetch_continuous_release_payload(
        http_get=http_get, timeout=timeout
    )
    return build_metadata_from_release(release_payload)


def create_download_filename(metadata: dict[str, Any]) -> str:
    package_name = metadata["package_name"]
    build_number = metadata["build_number"]
    return f"{package_name}_{build_number}.apk"


def download_latest_apk(
    metadata: dict[str, Any],
    *,
    download_dir: Path = Path("downloads"),
    http_get: HttpGet = requests.get,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Path:
    apk_url = metadata["apk_url"]
    download_name = create_download_filename(metadata)
    apk_path = Path(download_dir) / download_name

    apk_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = apk_path.with_suffix(".apk.part")

    response = http_get(apk_url, stream=True, timeout=timeout)
    response.raise_for_status()

    with temp_path.open("wb") as output_file:
        if hasattr(response, "iter_content"):
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output_file.write(chunk)
        else:
            output_file.write(response.content)

    temp_path.replace(apk_path)
    return apk_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check and download the latest Vita3K Android APK from the continuous release"
    )
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--check", action="store_true", help="Only check for latest version metadata"
    )
    action_group.add_argument(
        "--download", action="store_true", help="Download the latest Android APK"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print machine-readable JSON",
    )
    parser.add_argument(
        "--downloads-dir",
        default="downloads",
        help="Output directory for downloaded APKs",
    )
    return parser.parse_args()


def _print_payload(payload: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload))
        return

    for key, value in payload.items():
        print(f"{key}: {value}")


def main() -> int:
    args = parse_args()

    metadata = fetch_latest_vita3k_metadata()

    if args.check:
        _print_payload(metadata, as_json=args.as_json)
        return 0

    apk_path = download_latest_apk(metadata, download_dir=Path(args.downloads_dir))
    payload = {
        **metadata,
        "download_name": create_download_filename(metadata),
        "download_path": str(apk_path),
    }
    _print_payload(payload, as_json=args.as_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
