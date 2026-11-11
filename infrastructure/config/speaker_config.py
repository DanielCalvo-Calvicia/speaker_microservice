import os
from collections.abc import Mapping
from dataclasses import dataclass

_DEFAULT_KEYWORDS = "i2s,hw,default,sysdefault"
BACKENDS = ("real", "null")


@dataclass(slots=True, frozen=True)
class SpeakerConfig:
    device_index: int | None
    target_keywords: tuple[str, ...]
    backend: str = "real"  # SPEAKER_BACKEND: "real" (the sound card) or "null" (plays nothing)

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "SpeakerConfig":
        raw_index = env.get("SPEAKER_DEVICE_INDEX", "").strip()
        raw_keywords = env.get("SPEAKER_DEVICE_KEYWORDS", _DEFAULT_KEYWORDS)
        return cls(
            device_index=int(raw_index) if raw_index else None,
            target_keywords=tuple(k.strip() for k in raw_keywords.split(",") if k.strip()),
            backend=cls._backend_from(env),
        )

    @staticmethod
    def _backend_from(env: Mapping[str, str]) -> str:
        backend = env.get("SPEAKER_BACKEND", "").strip().lower() or "real"
        if backend not in BACKENDS:
            raise ValueError(
                f"SPEAKER_BACKEND must be one of {', '.join(BACKENDS)}, not {backend!r}"
            )
        return backend
