from dataclasses import dataclass

from fastapi import FastAPI

from application.ports.inbound.speaker_playback_port import SpeakerPlaybackPort
from composition_root.dependencies import speaker_dependencies as deps
from infrastructure.config.server_config import ServerConfig
from infrastructure.config.speaker_config import SpeakerConfig


@dataclass(slots=True, frozen=True)
class HttpContainer:
    app: FastAPI
    speaker: SpeakerPlaybackPort  # kept so main_flow can release the device on shutdown


def new_http_container(server_cfg: ServerConfig, speaker_cfg: SpeakerConfig) -> HttpContainer:
    playback = deps.new_audio_playback(speaker_cfg)
    service = deps.new_speaker_service(playback, server_cfg.service_name)
    app = deps.new_http_app(
        service, server_cfg.service_name, server_cfg.allowed_origins
    )
    return HttpContainer(app=app, speaker=service)
