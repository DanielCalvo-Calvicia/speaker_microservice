from shared_logging import get_logger

from application.ports.outbound.speaker_outbound_port import SpeakerOutboundPort
from infrastructure.config.speaker_config import SpeakerConfig
from infrastructure.outbound.null_playback.null_audio_playback import NullAudioPlayback
from infrastructure.outbound.sounddevice_playback.sounddevice_audio_playback import (
    SoundDeviceAudioPlayback,
)
from infrastructure.outbound.sounddevice_playback.sounddevice_device_selector import (
    DeviceSelector,
)

logger = get_logger(__name__)


def new_audio_playback(cfg: SpeakerConfig) -> SpeakerOutboundPort:
    """Choose the playback adapter (SPEAKER_BACKEND, ADR-012).

    The sound-card driver is imported only on the ``real`` branch: it imports ``sounddevice``, which
    needs PortAudio, and a machine without it must still be able to run ``null``.
    """
    if cfg.backend == "null":
        logger.warning("Speaker backend is null: audio is discarded")
        return NullAudioPlayback()
    from infrastructure.outbound.sounddevice_playback.sounddevice_driver import SoundDeviceDriver

    driver = SoundDeviceDriver()
    return SoundDeviceAudioPlayback(
        driver=driver,
        selector=DeviceSelector(driver, cfg.target_keywords, cfg.device_index),
    )
