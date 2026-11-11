"""A stop must not wait for an open stream forever: uvicorn is told to give open requests a few seconds (R-16 / T-07.3)."""

import asyncio

import pytest

from main_flow import http as main_http


class FakeServer:
    def __init__(self, config) -> None:
        self.config = config

    async def serve(self) -> None:
        return None


def run_with_fakes(monkeypatch: pytest.MonkeyPatch) -> dict:
    seen: dict = {}

    def fake_config(app, **kwargs):  # noqa: ANN001, ANN202
        seen.update(kwargs)
        return kwargs

    class Container:
        app = object()

        class speaker:  # noqa: N801
            @staticmethod
            async def stop_playback() -> None:
                seen["released"] = True

    monkeypatch.setattr(main_http, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(main_http, "new_http_container", lambda *a, **k: Container())
    monkeypatch.setattr(main_http.uvicorn, "Config", fake_config)
    monkeypatch.setattr(main_http.uvicorn, "Server", FakeServer)
    asyncio.run(main_http.run_http())
    return seen


def test_uvicorn_gives_open_streams_a_few_seconds_then_closes_them(monkeypatch):
    seen = run_with_fakes(monkeypatch)
    assert seen["timeout_graceful_shutdown"] == main_http.GRACEFUL_SHUTDOWN_SECONDS
    assert 1 <= main_http.GRACEFUL_SHUTDOWN_SECONDS <= 8  # well under Docker's 10 s grace period


def test_the_cleanup_still_runs_after_the_server_returns(monkeypatch):
    assert run_with_fakes(monkeypatch)["released"] is True
