# apps/mcp/server/mcp_server.py
from fastmcp import FastMCP
from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import login_required

djmcp = FastMCP(name="django_mcp")

# Most minimal tool: echoes input
@djmcp.tool
def echo(message: str) -> str:
    return f'{{"Echo": "{message}"}}'
