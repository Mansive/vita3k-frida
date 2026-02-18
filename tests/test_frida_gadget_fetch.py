import lzma

import repack


class FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int = 8192):
        del chunk_size
        yield self._payload


def test_build_frida_gadget_url_uses_versioned_release_path() -> None:
    url = repack.build_frida_gadget_url("17.6.2")
    assert (
        url
        == "https://github.com/frida/frida/releases/download/17.6.2/frida-gadget-17.6.2-android-arm64.so.xz"
    )


def test_decompress_xz_bytes_round_trip() -> None:
    original_payload = b"test gadget payload"
    xz_payload = lzma.compress(original_payload, format=lzma.FORMAT_XZ)

    assert repack.decompress_xz_bytes(xz_payload) == original_payload


def test_ensure_frida_gadget_so_downloads_once_and_reuses_cache(tmp_path) -> None:
    so_payload = b"arm64 gadget binary"
    xz_payload = lzma.compress(so_payload, format=lzma.FORMAT_XZ)

    calls: list[str] = []

    def fake_get(url: str, timeout: int = 300, stream: bool = True):
        del timeout, stream
        calls.append(url)
        return FakeResponse(xz_payload)

    so_path = repack.ensure_frida_gadget_so(
        version="17.6.2",
        cache_dir=tmp_path,
        http_get=fake_get,
    )
    assert so_path.read_bytes() == so_payload
    assert len(calls) == 1

    reused_path = repack.ensure_frida_gadget_so(
        version="17.6.2",
        cache_dir=tmp_path,
        http_get=fake_get,
    )
    assert reused_path == so_path
    assert len(calls) == 1
