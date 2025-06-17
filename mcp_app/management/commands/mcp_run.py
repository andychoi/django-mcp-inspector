# apps/mcp/management/commands/mcp_run.py
# this is only for running the MCP server over stdio for Claude Desktop
import os
import django
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Run FastMCP server (stdio only, for Claude Desktop)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--transport",
            choices=["stdio", "streamable-http", "sse"],
            default="stdio",
            help="Transport protocol for FastMCP"
        )

    def handle(self, *args, **options):
        # 1) Ensure we point at the correct settings module
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djproject.settings")
        django.setup()

        # 2) Import your MCP instance
        from mcp_app.mcp_server import djmcp as mcp_instance

        transport = options["transport"]
        self.stdout.write(self.style.SUCCESS(
            f"🚀 Running FastMCP server over {transport}"
        ))

        # 3) Start it—stdout/stderr will go to your console by default
        mcp_instance.run(transport=transport)