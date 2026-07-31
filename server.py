"""Supported Streamlit launcher with redirects for nested runtime probes."""

import streamlit as st
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.routing import Route


def _runtime_redirect(request: Request, target: str) -> RedirectResponse:
    query = request.url.query
    location = f"{target}?{query}" if query else target
    return RedirectResponse(location, status_code=307)


async def redirect_health(request: Request) -> RedirectResponse:
    return _runtime_redirect(request, "/_stcore/health")


async def redirect_host_config(request: Request) -> RedirectResponse:
    return _runtime_redirect(request, "/_stcore/host-config")


app = st.App(
    "app.py",
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
    ),
)
