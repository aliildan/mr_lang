"""Lightweight REST API for observability data using aiohttp or stdlib."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mr_lang.observability.collector import EventCollector


def create_app(collector: EventCollector) -> Any:
    """Create an aiohttp web application with observability routes.

    Falls back gracefully if aiohttp is not installed.
    """
    from aiohttp import web

    from mr_lang.api.dashboard import DASHBOARD_HTML

    async def health(request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def list_sessions(request: web.Request) -> web.Response:
        sessions = await collector.get_sessions()
        return web.json_response({"sessions": sessions})

    async def get_session(request: web.Request) -> web.Response:
        session_id = request.match_info["session_id"]
        events = await collector.get_session_events(session_id)
        stats = await collector.get_session_stats(session_id)
        return web.json_response(
            {
                "session_id": session_id,
                "stats": stats.model_dump(),
                "events": [e.model_dump() for e in events],
            },
            dumps=lambda x: json.dumps(x, default=str),
        )

    async def dashboard(request: web.Request) -> web.Response:
        return web.Response(text=DASHBOARD_HTML, content_type="text/html")

    app = web.Application()
    app.router.add_get("/api/health", health)
    app.router.add_get("/api/sessions", list_sessions)
    app.router.add_get("/api/sessions/{session_id}", get_session)
    app.router.add_get("/dashboard", dashboard)

    return app
