"""
ASGI config for djproject project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.staticfiles import StaticFiles
from django.conf import settings
from pathlib import Path
from django.contrib.staticfiles import finders

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djproject.settings")

django_application = get_asgi_application()


# ───────────────────────────────────────────────
# FastMCP Setup
# ───────────────────────────────────────────────
from mcp_app.mcp_server import djmcp as mcp_instance  # your FastMCP object
# from apps.mcp.auth_basic import BasicAuthMiddleware
# from apps.mcp.auth_session import SessionAuthMiddleware
from mcp_app.auth_middleware import CombinedAuthMiddleware
from mcp_app.metadata import oauth_authorization_server, oauth_protected_resource

# Optional CORS middleware
middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
    Middleware(CombinedAuthMiddleware),
]

# Create the FastMCP ASGI app (only once!)
mcp_asgi_app = mcp_instance.http_app(path="/", middleware=middleware)

# ───────────────────────────────────────────────
# Compose Starlette ASGI app combining Django + MCP
# ───────────────────────────────────────────────
application = Starlette(
    routes=[
        # allow the inspector to fetch metadata without redirecting
        Route("/.well-known/oauth-authorization-server",
              oauth_authorization_server, methods=["GET","OPTIONS"]),
        Route("/.well-known/oauth-protected-resource",
              oauth_protected_resource,  methods=["GET","OPTIONS"]),

        Mount("/mcp", mcp_asgi_app),  # /mcp endpoint for FastMCP tools
        Mount("/",    django_application),   # all other routes handled by Django
    ],
    lifespan=mcp_asgi_app.lifespan  # ✅ ensures FastMCP session manager starts
)


# Static file serving logic
# Serve static files (assumes collectstatic was run)
static_dir = settings.STATIC_ROOT
if static_dir and Path(static_dir).exists():
    application.routes.insert(
        2,
        Mount("/static", StaticFiles(directory=static_dir), name="static")
    )