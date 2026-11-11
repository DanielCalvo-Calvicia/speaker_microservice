from application.ports.outbound.speaker_outbound_port import SpeakerOutboundPort
from application.ports.service.speaker_service_port import SpeakerServicePort
from application.services.speaker_service import SpeakerService


def new_speaker_service(playback: SpeakerOutboundPort, name: str) -> SpeakerServicePort:
    return SpeakerService(playback=playback, name=name)
