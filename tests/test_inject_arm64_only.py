import json
from pathlib import Path

import repack


class FakeBinary:
    def __init__(self):
        self.libraries: list[str] = []
        self.added: list[str] = []
        self.writes: list[str] = []

    def add_library(self, library_name: str) -> None:
        self.libraries.append(library_name)
        self.added.append(library_name)

    def write(self, output_path: str) -> None:
        self.writes.append(output_path)


def test_inject_gadget_into_unpacked_dir_only_touches_arm64(tmp_path: Path) -> None:
    unpacked_dir = tmp_path / "unpacked"
    arm64_dir = unpacked_dir / "lib" / "arm64-v8a"
    x64_dir = unpacked_dir / "lib" / "x86_64"

    arm64_dir.mkdir(parents=True)
    x64_dir.mkdir(parents=True)

    arm64_target = arm64_dir / "libmain.so"
    arm64_target.write_bytes(b"arm64 target")
    (x64_dir / "libmain.so").write_bytes(b"x64 target")

    gadget_source = tmp_path / "frida-gadget.so"
    gadget_source.write_bytes(b"gadget payload")

    fake_binary = FakeBinary()
    parsed_paths: list[Path] = []

    def fake_parse(path_str: str) -> FakeBinary:
        parsed_paths.append(Path(path_str))
        return fake_binary

    repack.inject_gadget_into_unpacked_dir(
        unpacked_dir=unpacked_dir,
        gadget_so_path=gadget_source,
        config=repack.build_frida_config(),
        parser=fake_parse,
    )

    arm64_gadget_path = arm64_dir / repack.INTERNAL_GADGET_NAME
    arm64_config_path = arm64_dir / repack.INTERNAL_CONFIG_NAME
    x64_gadget_path = x64_dir / repack.INTERNAL_GADGET_NAME
    x64_config_path = x64_dir / repack.INTERNAL_CONFIG_NAME

    assert arm64_gadget_path.exists()
    assert arm64_gadget_path.read_bytes() == b"gadget payload"

    assert arm64_config_path.exists()
    config = json.loads(arm64_config_path.read_text(encoding="utf-8"))
    assert config["interaction"]["address"] == "127.0.0.1"

    assert not x64_gadget_path.exists()
    assert not x64_config_path.exists()

    assert parsed_paths == [arm64_target]
    assert fake_binary.added == [repack.INTERNAL_GADGET_NAME]
    assert fake_binary.writes == [str(arm64_target)]
