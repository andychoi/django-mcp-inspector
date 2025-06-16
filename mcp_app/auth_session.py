# apps/mcp/auth_session.py

import typing
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from asgiref.sync import sync_to_async

User = get_user_model()

async def get_user_from_session(session_key: str) -> typing.Union[User, AnonymousUser]:
    """
    Load the Django user associated with a session key.
    Runs in a thread so we're safe in async context.
    """
    def _load():
        store = SessionStore(session_key=session_key)
        data = store.load()  # may raise, or return {}
        uid = data.get("_auth_user_id")
        if uid:
            try:
                return User.objects.get(pk=uid)
            except User.DoesNotExist:
                pass
        return AnonymousUser()

    return await sync_to_async(_load, thread_sensitive=True)()

class SessionAuthMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that reads the Django sessionid cookie, 
    loads request.scope['user'], so @login_required and request.user work.
    """
    async def dispatch(self, request: Request, call_next):
        # 1) grab the sessionid cookie
        session_key = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if session_key:
            user = await get_user_from_session(session_key)
        else:
            user = AnonymousUser()

        # 2) inject into scope, so current_context().request.scope['user'] is set
        request.scope["user"] = user

        # 3) proceed
        return await call_next(request)