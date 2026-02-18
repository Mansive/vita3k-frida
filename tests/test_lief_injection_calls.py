from pathlib import Path

import repack


class FakeBinary:
    def __init__(self, libraries: list[str] | None = None):
        self.libraries = libraries or []
        self.added: list[str] = []
        self.written: list[str] = []

    def add_library(self, library_name: str) -> None:
        self.libraries.append(library_name)
        self.added.append(library_name)

    def write(self, output_path: str) -> None:
        self.written.append(output_path)


def test_inject_needed_library_adds_dependency_when_missing(tmp_path: Path) -> None:
    target = tmp_path / "libtarget.so"
    target.write_bytes(b"binary")

    binary = FakeBinary(libraries=["libc.so"])

    changed = repack.inject_needed_library(
        target_lib_path=target,
        parser=lambda _: binary,
    )

    assert changed is True
    assert binary.added == [repack.INTERNAL_GADGET_NAME]
    assert binary.written == [str(target)]


def test_inject_needed_library_is_idempotent_when_dependency_exists(
    tmp_path: Path,
) -> None:
    target = tmp_path / "libtarget.so"
    target.write_bytes(b"binary")

    binary = FakeBinary(libraries=[repack.INTERNAL_GADGET_NAME, "libc.so"])

    changed = repack.inject_needed_library(
        target_lib_path=target,
        parser=lambda _: binary,
    )

    assert changed is False
    assert binary.added == []
    assert binary.written == []
