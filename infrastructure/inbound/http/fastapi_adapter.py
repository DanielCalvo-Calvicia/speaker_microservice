import time
import logging
import asyncio
from typing import AsyncGenerator, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.responses import JSONResponse

from application.ports.adapter_inbound_port import AdapterInboundPort
from application.ports.service_port import SpeakerServicePort

from application.dtos.adapter_inbound_dtos import (
    InitInboundAdapterDto,
    StartSpeakerStreamRequestDto,
    StartSpeakerStreamResponseDto,
)

from application.dtos.mapper.adapter_inbound_to_service import map_inbound_to_service_playback_request
from application.dtos.mapper.service_to_adapter_inbound import map_service_to_inbound_playback_response
from infrastructure.inbound.http.audio_stream_autoloader import AudioStreamAutoloader

logger = logging.getLogger("speaker_microservice.infrastructure.inbound")


class FastApiAdapter(AdapterInboundPort):
    def __init__(self, service_port: SpeakerServicePort, app: FastAPI, config: InitInboundAdapterDto):
        self.service_port = service_port
        self.app = app
        self.config = config        
        logger.info(
            "Initializing FastApiAdapter: allow_origins=%s autoload_enabled=%s",
            config.allow_origins,
            bool(config.autoload_stream_url),
        )
        
        self.autoloader = None
        if config.autoload_stream_url:
            logger.info("Creating audio stream autoloader for URL: %s", config.autoload_stream_url)
            self.autoloader = AudioStreamAutoloader(config.autoload_stream_url, self)

        self.register_routes(self.app)
        logger.info("FastApiAdapter route registration complete.")

    def register_routes(self, app: FastAPI):
        logger.info("Registering FastAPI inbound routes.")

        @app.get("/health", tags=["Health"])
        async def health_check():
            logger.info("Health check requested.")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "action": "health_check",
                    "status": "success",
                    "status_code": status.HTTP_200_OK,
                    "message": "Speaker microservice is healthy",
                    "timestamp": time.time(),
                    "data": {"timestamp": time.time()}
                }
            )

        @app.post("/play/stream", tags=["Playback"])
        async def play_stream_http(request: Request, sample_rate: int = 24000, channels: int = 1):
            """
            Accepts raw audio bytes via HTTP Chunked Transfer-Encoding,
            transfers it to the service, and blocks until playback is complete.
            """
            logger.info(
                "HTTP playback stream request received: client=%s sample_rate=%s channels=%s",
                request.client,
                sample_rate,
                channels,
            )
            chunk_count = 0
            total_bytes = 0
            try:
                async def http_stream_generator() -> AsyncGenerator[bytes, None]:
                    nonlocal chunk_count, total_bytes
                    async for chunk in request.stream():
                        if chunk:
                            chunk_count += 1
                            total_bytes += len(chunk)
                        yield chunk

                inbound_request = StartSpeakerStreamRequestDto(
                    audio_stream=http_stream_generator(),
                    sample_rate=sample_rate,
                    channels=channels
                )
                
                response = await self.play(inbound_request)
                
                if not response.success:
                    logger.warning(
                        "HTTP playback failed: chunks=%s bytes=%s message=%s",
                        chunk_count,
                        total_bytes,
                        response.message,
                    )
                    return JSONResponse(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        content={
                            "action": "play_stream_http",
                            "status": "error",
                            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "message": response.message,
                            "timestamp": time.time(),
                            "data": None
                        }
                    )

                logger.info(
                    "HTTP playback completed successfully: chunks=%s bytes=%s message=%s",
                    chunk_count,
                    total_bytes,
                    response.message,
                )
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "action": "play_stream_http",
                        "status": "success",
                        "status_code": status.HTTP_200_OK,
                        "message": response.message,
                        "timestamp": time.time(),
                        "data": None
                    }
                )
            except Exception as e:
                logger.exception(
                    "HTTP playback request failed with exception after chunks=%s bytes=%s",
                    chunk_count,
                    total_bytes,
                )
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "action": "play_stream_http",
                        "status": "error",
                        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "message": f"Failed to play stream: {str(e)}",
                        "timestamp": time.time(),
                        "data": str(e)
                    }
                )

        @app.websocket("/play/ws")
        async def play_stream_ws(websocket: WebSocket, sample_rate: int = 24000, channels: int = 1):
            """
            WebSocket connection accepting binary messages containing raw PCM chunks.
            """
            await websocket.accept()
            logger.info(
                "Client connected to speaker playback WebSocket: client=%s sample_rate=%s channels=%s",
                websocket.client,
                sample_rate,
                channels,
            )
            
            queue: asyncio.Queue[bytes] = asyncio.Queue()
            chunk_count = 0
            total_bytes = 0

            async def ws_audio_generator() -> AsyncGenerator[bytes, None]:
                while True:
                    chunk = await queue.get()
                    if chunk == b"":  # Termination sentinel
                        queue.task_done()
                        logger.info("WebSocket audio generator received termination sentinel.")
                        break
                    yield chunk
                    queue.task_done()

            # Prepare the inbound payload
            inbound_request = StartSpeakerStreamRequestDto(
                audio_stream=ws_audio_generator(),
                sample_rate=sample_rate,
                channels=channels
            )

            # Start playback orchestration task in the background
            playback_coro = self.play(inbound_request)
            playback_task = asyncio.create_task(playback_coro)
            logger.info("WebSocket playback orchestration task started.")

            try:
                while True:
                    message = await websocket.receive()
                    if "bytes" in message:
                        binary_data = message["bytes"]
                        if binary_data:
                            chunk_count += 1
                            total_bytes += len(binary_data)
                            await queue.put(binary_data)
                    elif "text" in message:
                        text_data = message["text"]
                        if text_data == "EOF":
                            logger.info(
                                "Received EOF command via WebSocket after chunks=%s bytes=%s.",
                                chunk_count,
                                total_bytes,
                            )
                            break
            except WebSocketDisconnect:
                logger.info(
                    "WebSocket playback stream disconnected after chunks=%s bytes=%s.",
                    chunk_count,
                    total_bytes,
                )
            finally:
                # Stop streaming
                await queue.put(b"")
                # Wait for playback orchestration completion
                try:
                    response = await playback_task
                    logger.info(
                        "WebSocket playback task completed: success=%s message=%s chunks=%s bytes=%s",
                        response.success,
                        response.message,
                        chunk_count,
                        total_bytes,
                    )
                except Exception as e:
                    logger.exception("WebSocket playback task failure: %s", e)
                
                try:
                    await websocket.close()
                    logger.info("WebSocket connection closed.")
                except Exception:
                    logger.debug("WebSocket close failed or connection was already closed.", exc_info=True)
                    pass

    def start_autoload(self) -> None:
        if self.autoloader:
            logger.info("Starting configured audio stream autoloader.")
            self.autoloader.start()
        else:
            logger.info("Autoload start requested, but no autoload stream URL is configured.")

    async def stop_autoload(self) -> None:
        if self.autoloader:
            logger.info("Stopping configured audio stream autoloader.")
            await self.autoloader.stop()
        else:
            logger.info("Autoload stop requested, but no autoloader exists.")

    @property
    def get_app(self) -> Any:
        logger.debug("FastAPI app requested from inbound adapter.")
        return self.app

    async def play(self, request: StartSpeakerStreamRequestDto) -> StartSpeakerStreamResponseDto:
        logger.info(
            "Inbound adapter forwarding playback request to service: sample_rate=%s channels=%s",
            request.sample_rate,
            request.channels,
        )
        service_request_dto = map_inbound_to_service_playback_request(request)
        service_response_dto = await self.service_port.play(service_request_dto)
        adapter_response_dto = map_service_to_inbound_playback_response(service_response_dto)
        logger.info(
            "Inbound adapter received service playback response: success=%s message=%s",
            adapter_response_dto.success,
            adapter_response_dto.message,
        )
        return adapter_response_dto
