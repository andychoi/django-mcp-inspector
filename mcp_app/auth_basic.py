# apps/mcp/basic_auth.py
import base64
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, PlainTextResponse
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

User = get_user_model()

class BasicAuthMiddleware(BaseHTTPMiddleware):
    """
    A Starlette middleware that does HTTP Basic-Auth against Django's User model.
    """

    async def dispatch(self, request, call_next):
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Basic "):
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="mcp"'},
                content="Missing Basic Authorization header",
            )

        # Decode credentials
        try:
            b64creds = auth.split(" ", 1)[1]
            decoded = base64.b64decode(b64creds).decode("utf-8")
            username, password = decoded.split(":", 1)
        except Exception:
            return Response(
                status_code=400,
                content="Malformed Basic Authorization header",
            )

        # Lookup user and verify password
        try:
            user = await sync_to_async(User.objects.get)(username=username)
        except User.DoesNotExist:
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="mcp"'},
                content="Invalid credentials",
            )

        if not user.check_password(password) or not user.is_active:
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="mcp"'},
                content="Invalid credentials",
            )

        # Attach the authenticated user to the request’s scope
        request.scope["user"] = user

        return await call_next(request)