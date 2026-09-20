import os
from collections.abc import Mapping
from dataclasses import dataclass

_DEFAULT_KEYWORDS = "i2s,hw,default,sysdefault"


@dataclass(slots=True, frozen=True)
class SpeakerConfig:
    device_index: int | None
    target_keywords: tuple[str, ...]

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "SpeakerConfig":
        raw_index = env.get("SPEAKER_DEVICE_INDEX", "").strip()
        raw_keywords = env.get("SPEAKER_DEVICE_KEYWORDS", _DEFAULT_KEYWORDS)
        return cls(
            device_index=int(raw_index) if raw_index else None,
            target_keywords=tuple(k.strip() for k in raw_keywords.split(",") if k.strip()),
        )
