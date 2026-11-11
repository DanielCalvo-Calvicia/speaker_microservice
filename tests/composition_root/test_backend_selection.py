"""SPEAKER_BACKEND picks the playback adapter before the sounddevice driver is imported (T-01.2, ADR-012)."""

import importlib
import sys
import types

import pytest
from fastapi.testclient import TestClient

from infrastructure.config.server_config import ServerConfig
from infrastructure.config.speaker_config import SpeakerConfig

DRIVER_MODULE = "infrastructure.outbound.sounddevice_playback.sounddevice_driver"
REAL_ADAPTER = "infrastructure.outbound.sounddevice_playback"


def fresh_container_module(monkeypatch: pytest.MonkeyPatch, sounddevice):
    """Re-import the composition root as if the process had just started, with ``sounddevice`` as given."""
    monkeypatch.setitem(sys.modules, "sounddevice", sounddevice)
    for name in list(sys.modules):
        if name.startswith(("composition_root", DRIVER_MODULE)):
            monkeypatch.delitem(sys.modules, name)
    return importlib.import_module("composition_root.containers.http_container")


def build(module, **env: str):
    return module.new_http_container(ServerConfig.from_env({}), SpeakerConfig.from_env(dict(env)))


def test_null_starts_with_sounddevice_unimportable_and_never_imports_the_driver(monkeypatch):
    module = fresh_container_module(monkeypatch, None)  # `import sounddevice` now raises ImportError
    with pytest.raises(ImportError):
        import sounddevice  # noqa: F401

    container = build(module, SPEAKER_BACKEND="null")

    client = TestClient(container.app)
    assert client.get("/health").json()["status"] == "success"
    assert DRIVER_MODULE not in sys.modules


def test_null_answers_the_three_probes_and_says_it_is_a_null_sink(monkeypatch):
    module = fresh_container_module(monkeypatch, None)
    client = TestClient(build(module, SPEAKER_BACKEND="null").app)

    available = client.get("/available").json()["data"]
    ready = client.get("/ready").json()["data"]

    assert available["is_available"] is True
    assert "null" in available["reason"].lower() and "SPEAKER_BACKEND" in available["reason"]
    assert ready["is_ready"] is True
    assert ready["pending_reason"] is None  # a ready service has nothing pending


def test_real_is_the_default_and_needs_the_sounddevice_module(monkeypatch):
    module = fresh_container_module(monkeypatch, None)
    with pytest.raises(ImportError):
        build(module)  # nothing set: the real adapter, which needs PortAudio's module
    with pytest.raises(ImportError):
        build(module, SPEAKER_BACKEND="real")


def test_real_is_built_from_the_driver_module_and_fails_without_a_device(monkeypatch):
    stub = types.ModuleType("sounddevice")
    stub.query_devices = lambda *args, **kwargs: []  # type: ignore[attr-defined]
    stub.default = types.SimpleNamespace(device=(None, None))  # type: ignore[attr-defined]
    module = fresh_container_module(monkeypatch, stub)
    assert DRIVER_MODULE not in sys.modules  # not imported yet: the import is lazy

    with pytest.raises(Exception, match="sounddevice bootstrap failed"):
        build(module, SPEAKER_BACKEND="real")  # no output device: the same failure as before

    assert DRIVER_MODULE in sys.modules


class RecordingLogger:
    def __init__(self) -> None:
        self.records: list[tuple[str, str]] = []

    def warning(self, message: str, **fields: object) -> None:
        self.records.append(("warning", message))

    def info(self, message: str, **fields: object) -> None:
        self.records.append(("info", message))


def test_null_is_announced_with_one_warning_and_real_logs_nothing_new(monkeypatch):
    from composition_root.dependencies import audio_playback_dependency as deps

    recorder = RecordingLogger()
    monkeypatch.setattr(deps, "logger", recorder)

    deps.new_audio_playback(SpeakerConfig.from_env({"SPEAKER_BACKEND": "null"}))

    assert recorder.records == [("warning", "Speaker backend is null: audio is discarded")]


def test_the_null_wiring_builds_the_paced_sink(monkeypatch):
    from composition_root.dependencies import audio_playback_dependency as deps
    from infrastructure.outbound.null_playback.null_audio_playback import NullAudioPlayback

    sink = deps.new_audio_playback(SpeakerConfig.from_env({"SPEAKER_BACKEND": "null"}))

    assert isinstance(sink, NullAudioPlayback)
    assert sink._realtime is True  # Q01-3: paced to real time by default
