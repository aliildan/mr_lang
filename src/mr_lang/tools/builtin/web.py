"""HTTP request tool."""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def http_request(url: str, method: str = "GET", body: str = "") -> str:
    """Make an HTTP request and return the response.

    Args:
        url: The URL to request
        method: HTTP method (GET, POST, PUT, DELETE)
        body: Request body for POST/PUT (optional)
    """
    import httpx

    try:
        with httpx.Client(timeout=30) as client:
            kwargs: dict = {}
            if body and method.upper() in ("POST", "PUT", "PATCH"):
                kwargs["content"] = body
            response = client.request(method.upper(), url, **kwargs)
            return f"Status: {response.status_code}\n\n{response.text[:5000]}"
    except httpx.HTTPError as e:
        return f"Error: {e}"
