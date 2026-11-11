"""Fitness function: the service and every adapter implement a port, and the ports are the contract.

    inbound adapter (SpeakerHandler)   implements  SpeakerInboundPort
    service (SpeakerService)           implements  SpeakerServicePort
    outbound adapter (the backends)    implement   SpeakerOutboundPort

A new inbound or outbound adapter implements the same port as the others, so its functions are the same.
"""

import ast
from pathlib import Path

import pytest

from application.ports.inbound.speaker_inbound_port import SpeakerInboundPort
from application.ports.outbound.speaker_outbound_port import SpeakerOutboundPort
from application.ports.service.speaker_service_port import SpeakerServicePort
from application.services.speaker_service import SpeakerService
from infrastructure.inbound.http.http_handler import SpeakerHandler
from infrastructure.outbound.null_playback.null_audio_playback import NullAudioPlayback
from infrastructure.outbound.sounddevice_playback.sounddevice_audio_playback import (
    SoundDeviceAudioPlayback,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("component", "port"),
    [
        (SpeakerService, SpeakerServicePort),
        (SpeakerHandler, SpeakerInboundPort),
        (SoundDeviceAudioPlayback, SpeakerOutboundPort),
        (NullAudioPlayback, SpeakerOutboundPort),
    ],
)
def test_each_component_implements_its_port(component, port):
    assert issubclass(component, port)
    assert not component.__abstractmethods__, "a port operation is not implemented"


@pytest.mark.parametrize(
    ("port", "operations"),
    [
        (SpeakerInboundPort, {"health", "check_readiness", "play"}),
        (SpeakerServicePort, {"play", "stop_playback", "check_readiness", "is_available"}),
        (SpeakerOutboundPort, {"play", "close", "check_readiness", "is_playing"}),
    ],
)
def test_the_port_is_the_contract(port, operations):
    assert port.__abstractmethods__ == operations


def _classes(package: str, suffix: str) -> list[tuple[str, ast.ClassDef]]:
    found = []
    for path in sorted((ROOT / "infrastructure" / package).rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.ClassDef) and node.name.endswith(suffix):
                found.append((f"{path.relative_to(ROOT)}:{node.name}", node))
    return found


def _base_names(node: ast.ClassDef) -> set[str]:
    return {base.id for base in node.bases if isinstance(base, ast.Name)}


def test_every_inbound_adapter_implements_the_inbound_port():
    adapters = _classes("inbound", "Handler")
    assert adapters, "no inbound adapter found"
    missing = [name for name, node in adapters if "SpeakerInboundPort" not in _base_names(node)]
    assert not missing, f"inbound adapters that do not implement SpeakerInboundPort: {missing}"


def test_every_outbound_adapter_implements_the_outbound_port():
    adapters = _classes("outbound", "AudioPlayback")
    assert adapters, "no outbound adapter found"
    missing = [name for name, node in adapters if "SpeakerOutboundPort" not in _base_names(node)]
    assert not missing, f"outbound adapters that do not implement SpeakerOutboundPort: {missing}"
