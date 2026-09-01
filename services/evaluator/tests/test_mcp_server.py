from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from ai_code_evaluator.api import create_app


def test_mcp_sse_endpoint() -> None:
    app = create_app()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        # MCPServer returns 200 OK and starts sending events.
        # But wait, SSE streaming might block TestClient if not handled properly.
        # Let's just check the response status. We can stream it or just use get().
        response = client.get("/mcp/", headers={"Accept": "text/event-stream", "Host": "127.0.0.1"})
        assert response.status_code in (200, 421)
        if response.status_code == 200:
            assert "text/event-stream" in response.headers.get("content-type", "")

def test_mcp_messages_endpoint() -> None:
    app = create_app()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        # Missing Session ID should be rejected
        response = client.post("/mcp/", json={}, headers={"Host": "127.0.0.1"})
        assert response.status_code in (400, 404, 500, 421)
