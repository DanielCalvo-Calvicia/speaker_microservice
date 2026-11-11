from contracts.api.microservices.common.health_check import HealthCheckResponse
from fastapi.responses import JSONResponse

from application.ports.inbound.speaker_inbound_port import SpeakerInboundPort
from infrastructure.inbound.http.response.http_envelope import success


async def handle_health(inbound: SpeakerInboundPort) -> JSONResponse:
    """GET /health: liveness. 200 while the process answers HTTP."""
    return success(
        "health_check",
        "Speaker microservice is healthy",
        HealthCheckResponse(healthy=inbound.health()),
    )
