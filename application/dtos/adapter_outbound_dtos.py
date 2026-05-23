from dataclasses import dataclass
from typing import Optional

@dataclass(slots=True, frozen=True)
class InitOutboundAdapterDto:
    """Configures the hardware audio output device properties."""
    device_index: Optional[int] = None
    target_keywords: tuple[str, ...] = ("i2s", "hw", "default", "sysdefault")
