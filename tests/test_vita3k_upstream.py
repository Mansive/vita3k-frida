from pathlib import Path

import pytest

import vita3k_upstream


class FakeResponse:
    def __init__(self, *, json_data=None, chunks=None):
        self._json_data = json_data
        self._chunks = chunks or []

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._json_data

    def iter_content(self, chunk_size: int = 8192):
        del chunk_size
        for chunk in self._chunks:
            yield chunk


def _sample_release_payload() -> dict:
    return {
        "tag_name": "continuous",
        "body": "Corresponding commit: 3b42fa3587c9da043a5113bc89497ac8f9e68fa0\nVita3K Build: 3923",
        "updated_at": "2026-02-16T14:20:21Z",
        "assets": [
            {
                "name": "android-latest.apk",
                "browser_download_url": "https://github.com/Vita3K/Vita3K/releases/download/continuous/android-latest.apk",
                "digest": "sha256:e75098bd8ffcc798224ea10cb594d3684343ac6a6a97e45d919373c05a07b2d6",
            }
        ],
    }


def test_fetch_latest_vita3k_metadata_parses_continuous_release() -> None:
    payload = _sample_release_payload()

    def fake_get(url: str, timeout: int = 300):
        assert url == vita3k_upstream.CONTINUOUS_RELEASE_API_URL
        assert timeout == 300
        return FakeResponse(json_data=payload)

    metadata = vita3k_upstream.fetch_latest_vita3k_metadata(http_get=fake_get)

    assert metadata["package_name"] == "org.vita3k.emulator"
    assert metadata["build_number"] == 3923
    assert metadata["commit_sha"] == "3b42fa3587c9da043a5113bc89497ac8f9e68fa0"
    assert metadata["release_tag"] == "v3923"
    assert metadata["apk_name"] == "android-latest.apk"
    assert (
        metadata["apk_sha256"]
        == "e75098bd8ffcc798224ea10cb594d3684343ac6a6a97e45d919373c05a07b2d6"
    )


def test_build_metadata_raises_when_build_number_missing() -> None:
    payload = _sample_release_payload()
    payload["body"] = "Corresponding commit: 3b42fa3587c9da043a5113bc89497ac8f9e68fa0"

    with pytest.raises(ValueError):
        vita3k_upstream.build_metadata_from_release(payload)


def test_download_latest_apk_writes_binary_chunks(tmp_path: Path) -> None:
    metadata = {
        "package_name": "org.vita3k.emulator",
        "build_number": 3923,
        "apk_url": "https://github.com/Vita3K/Vita3K/releases/download/continuous/android-latest.apk",
    }

    def fake_get(url: str, stream: bool = True, timeout: int = 300):
        assert url.endswith("android-latest.apk")
        assert stream is True
        assert timeout == 300
        return FakeResponse(chunks=[b"abc", b"123"])

    apk_path = vita3k_upstream.download_latest_apk(
        metadata,
        download_dir=tmp_path,
        http_get=fake_get,
    )

    assert apk_path == tmp_path / "org.vita3k.emulator_3923.apk"
    assert apk_path.read_bytes() == b"abc123"
