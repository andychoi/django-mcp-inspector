# apps/mcp/management/commands/run_mcp.py
# this is only for running the MCP server over stdio for Claude Desktop
import os
import django
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Run FastMCP server (stdio only, for Claude Desktop)"

    def handle(self, *args, **options):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djproject.settings.settings")
        django.setup()

        from mcp_app.mcp_server import djmcp as mcp_instance

        self.stdout.write(self.style.SUCCESS("Running FastMCP server over stdio for Claude Desktop..."))
        mcp_instance.run(transport="stdio")