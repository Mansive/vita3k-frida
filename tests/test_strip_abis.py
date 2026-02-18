from pathlib import Path

import pytest

import repack


def test_strip_non_target_abis_removes_other_folders(tmp_path: Path) -> None:
    unpacked_dir = tmp_path / "unpacked"
    lib_root = unpacked_dir / "lib"
    (lib_root / "arm64-v8a").mkdir(parents=True)
    (lib_root / "armeabi-v7a").mkdir()
    (lib_root / "x86_64").mkdir()

    removed = repack.strip_non_target_abis(unpacked_dir, keep_abis={"arm64-v8a"})

    assert sorted(removed) == ["armeabi-v7a", "x86_64"]
    assert (lib_root / "arm64-v8a").exists()
    assert not (lib_root / "armeabi-v7a").exists()
    assert not (lib_root / "x86_64").exists()


def test_strip_non_target_abis_raises_when_target_missing(tmp_path: Path) -> None:
    unpacked_dir = tmp_path / "unpacked"
    lib_root = unpacked_dir / "lib"
    (lib_root / "armeabi-v7a").mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        repack.strip_non_target_abis(unpacked_dir, keep_abis={"arm64-v8a"})
