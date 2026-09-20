from collections.abc import Sequence

from shared_logging import get_logger

from infrastructure.outbound.sounddevice_playback.audio_driver import AudioDriver

logger = get_logger(__name__)


class DeviceSelector:
    """Picks an output device: the configured index, else first keyword match, else OS default."""

    def __init__(
        self,
        driver: AudioDriver,
        target_keywords: Sequence[str] = (),
        device_index: int | None = None,
    ) -> None:
        self._driver = driver
        self._target_keywords = tuple(target_keywords)
        self._device_index = device_index

    def select(self) -> int:
        if self._device_index is not None:
            logger.info("Using explicitly configured output device", index=self._device_index)
            return self._device_index

        devices = self._driver.output_devices()
        logger.debug("Scanning for speakers", devices_found=len(devices))

        for device in devices:
            if device.max_output_channels <= 0:
                continue
            logger.debug(
                "Found output device",
                id=device.index,
                name=device.name,
                channels=device.max_output_channels,
            )
            if any(key.lower() in device.name.lower() for key in self._target_keywords):
                logger.info("Auto-selected keyword match", name=device.name, id=device.index)
                return device.index

        try:
            default_output = self._driver.default_output_index()
            if default_output is None:
                raise RuntimeError("No OS default output device configured")
            default_info = self._driver.device_info(default_output)
        except Exception as error:
            raise RuntimeError(f"No valid output devices discovered: {error}") from error
        logger.warning(
            "No keyword match; falling back to default output",
            id=default_output,
            name=default_info.name,
        )
        return default_output
