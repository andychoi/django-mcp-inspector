
# Django + FastMCP Integration

This project integrates FastMCP with a Django ASGI application, supporting both OAuth2 Bearer token and session-based authentication.

This project integrates FastMCP (Model Context Protocol) into a Django ASGI application. It enables secure, streamable, and authenticated communication between Node.js-based MCP Inspector tools and Django-backed FastMCP tools.

✅ Features:
 - OAuth2 and Session-based Authentication via Django OAuth Toolkit
 - Proxy token support for MCP Inspector relay sessions
 - Streamable HTTP transport support for MCP client communication
 - Metadata endpoints for OAuth discovery
 - Pluggable middleware for hybrid Bearer+Session auth

Ideal for setups combining Django admin/UX with real-time tool APIs using the MCP Inspector.

## 📦 Project Structure

```
.
├── djproject/
│   ├── settings.py
│   └── asgi.py  ← Mounts MCP app
├── mcp_app/
│   ├── auth_middleware.py
│   └── mcp_server.py
├── manage.py
└── requirements.txt
```

## ⚙️ Setup Instructions

### 1. Install Requirements

```bash
pip install -r requirements.txt
```

Ensure `django`, `django-oauth-toolkit`, and `fastmcp` are included.

### 2. Django Settings

Ensure your `INSTALLED_APPS` includes:

```python
"oauth2_provider",
"mcp_app",
```

### 3. Configure ASGI in `asgi.py`

```python
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.staticfiles import StaticFiles
from django.core.asgi import get_asgi_application
from pathlib import Path
from django.conf import settings

from mcp_app.mcp_server import djmcp as mcp_instance
from mcp_app.auth_middleware import CombinedAuthMiddleware
from mcp_app.metadata import oauth_authorization_server, oauth_protected_resource

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djproject.settings")

django_application = get_asgi_application()

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
    Middleware(CombinedAuthMiddleware),
]

mcp_asgi_app = mcp_instance.http_app(path="/", middleware=middleware)

application = Starlette(
    routes=[
        Route("/.well-known/oauth-authorization-server", oauth_authorization_server, methods=["GET", "OPTIONS"]),
        Route("/.well-known/oauth-protected-resource", oauth_protected_resource, methods=["GET", "OPTIONS"]),
        Mount("/mcp", mcp_asgi_app),
        Mount("/", django_application),
    ],
    lifespan=mcp_asgi_app.lifespan
)

if settings.STATIC_ROOT and Path(settings.STATIC_ROOT).exists():
    application.routes.insert(
        2,
        Mount("/static", StaticFiles(directory=settings.STATIC_ROOT), name="static")
    )
```

## 🔐 Combined Authentication Middleware

Located at `mcp_app/auth_middleware.py`.

- Checks `Authorization: Bearer ...` and verifies using DOT
- Falls back to Django `sessionid` cookie
- Accepts `x-mcp-proxy-session-token` for trusted proxy-forwarded requests

## 🛠️ Example MCP Tool

```python
from fastmcp import FastMCP

djmcp = FastMCP(name="django_mcp")

@djmcp.tool
def echo(message: str) -> str:
    return f'{{"Echo": "{message}"}}'
```

## 🧪 Debugging Tips

- Ensure `is_valid()` from DOT is used without params.
- Middleware logs errors with `logger.error(...)` if response fails.
- Be aware: `_StreamingResponse` objects don’t support `.body()`.

---
License

This project is licensed under the MIT License. Feel free to adapt and extend for your own needs.