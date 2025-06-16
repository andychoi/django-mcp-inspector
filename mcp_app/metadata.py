# apps/mcp/metadata.py
from starlette.responses import JSONResponse

async def oauth_authorization_server(request):
    host = request.headers["host"]
    base = f"https://{host}/o"  # or http:// if you’re not on SSL
    return JSONResponse({
        "issuer":                 base,
        "authorization_endpoint": f"{base}/authorize/",
        "token_endpoint":         f"{base}/token/",
        "introspection_endpoint": f"{base}/introspect/",
        "revocation_endpoint":    f"{base}/revoke/",
    })

async def oauth_protected_resource(request):
    host = request.headers["host"]
    return JSONResponse({
        "introspection_endpoint": f"https://{host}/o/introspect/"
    })