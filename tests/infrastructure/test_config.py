from infrastructure.config.server_config import ServerConfig
from infrastructure.config.speaker_config import SpeakerConfig


def test_server_config_defaults():
    cfg = ServerConfig.from_env({})
    assert cfg == ServerConfig(
        service_name="Speaker Microservice",
        host="127.0.0.1",
        port=8003,
        allowed_origins=("*",),
    )


def test_server_config_overrides():
    cfg = ServerConfig.from_env(
        {
            "SERVICE_NAME": "X",
            "SERVICE_HOST": "0.0.0.0",
            "SERVICE_PORT": "9000",
            "ALLOWED_ORIGINS": " http://a.test , http://b.test ,,",
        }
    )
    assert cfg == ServerConfig(
        "X", "0.0.0.0", 9000, ("http://a.test", "http://b.test")
    )


def test_speaker_config_defaults():
    cfg = SpeakerConfig.from_env({})
    assert cfg == SpeakerConfig(None, ("i2s", "hw", "default", "sysdefault"))


def test_speaker_config_parses_index_and_keywords():
    cfg = SpeakerConfig.from_env(
        {
            "SPEAKER_DEVICE_INDEX": " 3 ",
            "SPEAKER_DEVICE_KEYWORDS": " usb , dac ,,",
        }
    )
    assert cfg == SpeakerConfig(3, ("usb", "dac"))


def test_blank_index_means_unset():
    cfg = SpeakerConfig.from_env({"SPEAKER_DEVICE_INDEX": "  "})
    assert cfg.device_index is None
