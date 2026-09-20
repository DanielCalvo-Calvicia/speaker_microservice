import pytest
from fastapi.testclient import TestClient
from shared_logging.testing import capture

from composition_root.containers import http_container
from composition_root.dependencies import speaker_dependencies
from infrastructure.config.server_config import ServerConfig
from infrastructure.config.speaker_config import SpeakerConfig
from infrastructure.outbound.sounddevice_playback.audio_driver import DeviceInfo

TRACE_ID = "0af7651916cd43dd8448eb211c80319c"
TRACEPARENT = f"00-{TRACE_ID}-b7ad6b7169203331-01"


class FakeDriver:
    def output_devices(self):
        return [DeviceInfo(0, "Speakers", 2)]

    def default_output_index(self):
        return 0

    def device_info(self, index):
        return self.output_devices()[index]

    def open_output(self, index, audio_format):
        raise NotImplementedError


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(speaker_dependencies, "SoundDeviceDriver", FakeDriver)
    container = http_container.new_http_container(
        ServerConfig.from_env({}), SpeakerConfig.from_env({})
    )
    return TestClient(container.app)


def test_incoming_trace_is_continued_and_logged_with_the_service_name(client):
    with capture("speaker") as logs:
        response = client.get("/health", headers={"traceparent": TRACEPARENT})

    assert response.status_code == 200
    assert response.headers["x-trace-id"] == TRACE_ID
    request_logs = [r for r in logs.records if r["logger"] == "shared_logging.http"]
    assert request_logs and {r["trace_id"] for r in request_logs} == {TRACE_ID}
    assert {r["service"] for r in logs.records} == {"speaker"}
