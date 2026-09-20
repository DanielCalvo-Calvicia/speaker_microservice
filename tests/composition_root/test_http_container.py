import pytest
from fastapi.testclient import TestClient

from composition_root.containers import http_container
from composition_root.dependencies import speaker_dependencies
from infrastructure.config.server_config import ServerConfig
from infrastructure.config.speaker_config import SpeakerConfig
from infrastructure.outbound.sounddevice_playback.audio_driver import DeviceInfo


class FakeDriver:
    def output_devices(self):
        return [DeviceInfo(0, "Speakers", 2)]

    def default_output_index(self):
        return 0

    def device_info(self, index):
        return self.output_devices()[index]

    def open_output(self, index, audio_format):
        raise NotImplementedError


@pytest.fixture(autouse=True)
def fake_sounddevice_driver(monkeypatch):
    monkeypatch.setattr(speaker_dependencies, "SoundDeviceDriver", FakeDriver)


def test_container_wires_an_app_that_answers_health():
    server_cfg = ServerConfig.from_env({})

    container = http_container.new_http_container(server_cfg, SpeakerConfig.from_env({}))

    body = TestClient(container.app).get("/health").json()
    assert body["status"] == "success" and body["action"] == "health_check"
    assert container.speaker.is_available() is False


def test_no_route_needs_credentials():
    client = TestClient(
        http_container.new_http_container(ServerConfig.from_env({}), SpeakerConfig.from_env({})).app
    )

    ok = client.get("/available")
    assert ok.status_code == 200 and "is_available" in ok.json()["data"]
