import asyncio
import math
import os
import socket
import struct
import subprocess
import sys

from dotenv import find_dotenv, load_dotenv

# Add the project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def sine_wave_generator(sample_rate=44100, duration=2.0, freq=440.0, channels=1):
    """
    Generate mathematical pure sine wave audio chunks.
    """
    num_samples = int(sample_rate * duration)
    chunk_size = 2048

    for i in range(0, num_samples, chunk_size):
        chunk_bytes = bytearray()
        for j in range(chunk_size):
            if i + j >= num_samples:
                break

            # Pure sine tone
            val = int(
                math.sin(2 * math.pi * freq * (i + j) / sample_rate) * 20000
            )  # Slightly reduced amplitude for testing comfort
            packed_value = struct.pack("<h", val)

            for _ in range(channels):
                chunk_bytes.extend(packed_value)

        yield bytes(chunk_bytes)
        # Yield control to match physical playback speed
        await asyncio.sleep((chunk_size / sample_rate) * 0.8)


def is_port_open(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect((host, port))
            return True
    except OSError:
        return False


async def run_test():
    # 1. Load config
    dotenv_path = find_dotenv(".env")
    if dotenv_path:
        load_dotenv(dotenv_path)

    host = os.getenv("SERVICE_HOST", "127.0.0.1")
    port = int(os.getenv("SERVICE_PORT", "8003"))

    print(f"Targeting server on {host}:{port}")

    # 2. Spin up Uvicorn Speaker Microservice in its own directory
    print("Booting Uvicorn Speaker Microservice in background...")
    python_executable = sys.executable
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    server_process = subprocess.Popen(
        [python_executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=project_root,
    )
    if server_process.stdout is None:
        raise RuntimeError("Server process stdout pipe was not created.")
    server_stdout = server_process.stdout

    # Start a thread to read and print server logs in real-time
    def log_streamer():
        for line in iter(server_stdout.readline, ""):
            sys.stdout.write(f"[Server] {line}")
            sys.stdout.flush()

    import threading

    log_thread = threading.Thread(target=log_streamer, daemon=True)
    log_thread.start()

    # Wait until the port opens or the process dies
    attempts = 0
    max_attempts = 30
    server_healthy = False

    while attempts < max_attempts:
        if server_process.poll() is not None:
            print("Server background process failed to start!")
            sys.exit(1)

        if is_port_open(host, port):
            server_healthy = True
            print("Server is up and listening!")
            break

        await asyncio.sleep(0.2)
        attempts += 1

    if not server_healthy:
        print("Timed out waiting for server to startup.")
        server_process.terminate()
        sys.exit(1)

    # 3. Query health check first
    import json
    import urllib.request

    health_url = f"http://{host}:{port}/health"
    print(f"Querying health endpoint: {health_url}")
    try:
        with urllib.request.urlopen(health_url, timeout=2.0) as response:
            health_data = json.loads(response.read().decode())
            print(f"Health response: {health_data}")
    except Exception as e:
        print(f"Health check failed: {e}")
        server_process.terminate()
        sys.exit(1)

    # 4. Play a sine wave through POST /process/stream/set as Speaker inbound contract events
    import base64

    import httpx
    from contracts.stream.codec import EventSequencer, NdjsonDecoder, encode_ndjson
    from contracts.stream.common.base import EventType
    from contracts.stream.microservices.speaker.inbound.stream_started import (
        SpeakerStreamStartedInboundEvent,
        SpeakerStreamStartedInboundEventDTO,
    )
    from contracts.stream.microservices.speaker.inbound.partial import (
        SpeakerPartialInboundEvent,
        SpeakerPartialInboundEventDTO,
    )
    from contracts.stream.schemas import SPEAKER_OUTBOUND

    sample_rate = 24000
    headers = {"Content-Type": "application/x-ndjson"}

    async def brain_like_upload():
        events = EventSequencer()
        yield encode_ndjson(
            events.next(
                SpeakerStreamStartedInboundEvent,
                SpeakerStreamStartedInboundEventDTO(sample_rate=sample_rate, channels=1),
            )
        )
        async for chunk in sine_wave_generator(
            sample_rate=sample_rate, duration=2.0, freq=440.0, channels=1
        ):
            yield encode_ndjson(
                events.next(
                    SpeakerPartialInboundEvent,
                    SpeakerPartialInboundEventDTO(bytes_base64=base64.b64encode(chunk).decode()),
                )
            )

    print("Playing 2 seconds of a 440 Hz sine wave...")
    try:
        decoder = NdjsonDecoder(SPEAKER_OUTBOUND)
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"http://{host}:{port}/process/stream/set",
                params={"sample_rate": sample_rate, "channels": 1},
                content=brain_like_upload(),
                headers=headers,
            ) as response:
                response.raise_for_status()
                async for body in response.aiter_bytes():
                    for event in decoder.feed(body):
                        print(f"Stream event: {event.type.value} {event.payload}")
                        if event.type is EventType.ERROR:
                            raise RuntimeError(event.payload.message)
        print("Playback test completed successfully.")

    except Exception as e:
        print(f"E2E Test error occurred: {e}")
    finally:
        print("Shutting down background server process...")
        server_process.terminate()
        try:
            server_process.wait(timeout=2.0)
            print("Server terminated gracefully.")
        except subprocess.TimeoutExpired:
            print("Force terminating server process.")
            server_process.kill()


if __name__ == "__main__":
    asyncio.run(run_test())
