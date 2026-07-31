"""Supported Streamlit launcher with redirects for nested runtime probes."""

from pathlib import Path

import streamlit as st
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.middleware import Middleware
from starlette.routing import Route


def _runtime_redirect(request: Request, target: str) -> RedirectResponse:
    query = request.url.query
    location = f"{target}?{query}" if query else target
    return RedirectResponse(location, status_code=307)


async def redirect_health(request: Request) -> RedirectResponse:
    return _runtime_redirect(request, "/_stcore/health")


async def redirect_host_config(request: Request) -> RedirectResponse:
    return _runtime_redirect(request, "/_stcore/host-config")


def root_stream_path(path: str) -> str:
    parts = path.split("/")
    if len(parts) == 4 and parts[2:] == ["_stcore", "stream"]:
        return "/_stcore/stream"
    return path


class NestedStreamPathMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "websocket":
            rewritten = root_stream_path(scope.get("path", ""))
            if rewritten != scope.get("path"):
                scope = dict(scope)
                scope["path"] = rewritten
                scope["raw_path"] = rewritten.encode("utf-8")
        await self.app(scope, receive, send)


async def nested_page_index(_request: Request) -> HTMLResponse:
    index_path = Path(st.__file__).resolve().parent / "static" / "index.html"
    index_html = index_path.read_text(encoding="utf-8")
    backend_config = """
    <script>
      window.__streamlit = {
        BACKEND_BASE_URL: window.location.origin,
        HOST_CONFIG_BASE_URL: window.location.origin,
        MAIN_PAGE_BASE_URL: window.location.origin
      }
    </script>
    """
    return HTMLResponse(
        index_html.replace("<head>", f"<head>{backend_config}", 1)
    )


app = st.App(
    "app.py",
    middleware=(Middleware(NestedStreamPathMiddleware),),
    routes=(
        Route(
            "/{page:str}/_stcore/health",
            redirect_health,
            methods=["GET"],
        ),
        Route(
            "/{page:str}/_stcore/host-config",
            redirect_host_config,
            methods=["GET"],
        ),
        Route("/選題", nested_page_index, methods=["GET"]),
        Route("/成效", nested_page_index, methods=["GET"]),
        Route("/設定", nested_page_index, methods=["GET"]),
    ),
)
