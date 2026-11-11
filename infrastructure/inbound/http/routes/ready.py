from contracts.api.microservices.common.readiness import ReadinessResponse
from fastapi.responses import JSONResponse

from application.ports.inbound.speaker_inbound_port import SpeakerInboundPort
from infrastructure.inbound.http.response.http_envelope import success


async def handle_ready(inbound: SpeakerInboundPort) -> JSONResponse:
    """GET /ready: whether the output device can be used (probed without opening a stream)."""
    readiness = await inbound.check_readiness()
    return success(
        "check_readiness",
        "Speaker device readiness checked",
        ReadinessResponse(
            is_ready=readiness.is_ready,
            # a ready service has nothing pending (the null backend's note is for /available)
            pending_reason=None if readiness.is_ready else readiness.message or None,
        ),
    )
