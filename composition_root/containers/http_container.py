from dataclasses import dataclass

from fastapi import FastAPI

from application.ports.service.speaker_service_port import SpeakerServicePort
from composition_root.dependencies.audio_playback_dependency import new_audio_playback
from composition_root.dependencies.http_app_dependency import new_http_app
from composition_root.dependencies.speaker_service_dependency import new_speaker_service
from infrastructure.config.server_config import ServerConfig
from infrastructure.config.speaker_config import SpeakerConfig


@dataclass(slots=True, frozen=True)
class HttpContainer:
    app: FastAPI
    speaker: SpeakerServicePort  # kept so main_flow can release the device on shutdown


def new_http_container(server_cfg: ServerConfig, speaker_cfg: SpeakerConfig) -> HttpContainer:
    playback = new_audio_playback(speaker_cfg)
    service = new_speaker_service(playback, server_cfg.service_name)
    app = new_http_app(service, server_cfg.service_name, server_cfg.allowed_origins)
    return HttpContainer(app=app, speaker=service)
