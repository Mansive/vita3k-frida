import repack


def test_build_frida_config_defaults_to_localhost() -> None:
    config = repack.build_frida_config()

    assert config["interaction"]["type"] == "listen"
    assert config["interaction"]["address"] == "127.0.0.1"
    assert config["interaction"]["port"] == 27042
    assert config["interaction"]["on_load"] == "resume"


def test_build_frida_config_allows_address_override() -> None:
    config = repack.build_frida_config(listen_address="0.0.0.0")

    assert config["interaction"]["address"] == "0.0.0.0"
    assert config["interaction"]["port"] == 27042
