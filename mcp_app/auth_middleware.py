import typing, logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from asgiref.sync import sync_to_async
from oauth2_provider.models import AccessToken

logger = logging.getLogger("mcp.auth")
User = get_user_model()

async def get_user_from_session(session_key: str) -> typing.Union[User, AnonymousUser]:
    def _load():
        store = SessionStore(session_key)
        data = store.load()
        uid = data.get("_auth_user_id")
        if uid:
            try:
                return User.objects.get(pk=uid)
            except User.DoesNotExist:
                pass
        return AnonymousUser()
    return await sync_to_async(_load, thread_sensitive=True)()

async def get_user_from_bearer(token: str) -> typing.Union[User, AnonymousUser]:
    def _load():
        try:
            tok = AccessToken.objects.select_related("user").get(token=token)
            if tok.is_valid():
                return tok.user
        except Exception as e:
            logger.warning("DOT lookup error: %s", e)
        return AnonymousUser()
    return await sync_to_async(_load, thread_sensitive=True)()

class CombinedAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        accept = request.headers.get("accept", "")
        proxy_token = request.headers.get("x-mcp-proxy-session-token")

        # 1) Trust proxy-authenticated requests
        if proxy_token:
            response = await call_next(request)
            if response.status_code != 200:
                if hasattr(response, "body"):
                    # non-stream response: log body
                    body = await response.body()
                    logger.error("Proxy-forwarded MCP error %s: %s", response.status_code, body)
                else:
                    logger.error("Proxy-forwarded MCP error %s (streaming response)", response.status_code)
            return response

        # 2) Allow metadata discovery
        if path.startswith("/.well-known/"):
            return await call_next(request)

        # 3) Initial stream handshake: inject transport param
        if method == "GET" and path.startswith("/mcp") and "text/event-stream" in accept:
            # Required by FastMCP to establish streaming
            request.scope["query_string"] = b"transport=streamable-http"
            response = await call_next(request)
            if response.status_code != 200:
                if hasattr(response, "body"):
                    body = await response.body()
                    logger.error("Stream handshake error %s: %s", response.status_code, body)
                else:
                    logger.error("Stream handshake error %s (streaming response)", response.status_code)
            return response

        # 4) Bearer token authentication
        auth_header = request.headers.get("Authorization", "")
        parts = auth_header.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            user = await get_user_from_bearer(parts[1].strip())
        else:
            # 5) Session cookie fallback
            session_key = request.cookies.get(settings.SESSION_COOKIE_NAME)
            user = await get_user_from_session(session_key) if session_key else AnonymousUser()

        # 6) Reject anonymous
        if isinstance(user, AnonymousUser):
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="mcp", charset="UTF-8"'},
                content="Authentication required",
            )

        # 7) Authenticated tool calls
        request.scope["user"] = user
        response = await call_next(request)
        if response.status_code != 200:
            if hasattr(response, "body"):
                body = await response.body()
                logger.error("Authenticated MCP error %s: %s", response.status_code, body)
            else:
                logger.error("Authenticated MCP error %s (streaming response)", response.status_code)
        return response
