djproject

A Django + FastMCP starter project integrating OAuth2 authentication (via django-oauth-toolkit) with a FastMCP server mounted alongside your Django app under Starlette.

Features
	•	Django Core: Standard Django 5.2 project structure with custom users.User model.
	•	OAuth2: Full Authorization Code + PKCE flow powered by django-oauth-toolkit.
	•	FastMCP: Exposes an MCP endpoint (/mcp/) alongside Django, with tools registered via the FastMCP SDK.
	•	Combined Authentication: CombinedAuthMiddleware automatically checks for Authorization: Bearer <token> (DOT) or falls back to Django session cookies.
	•	Management Commands:
	•	mcp_inspect: Walks you through PKCE flow and launches the MCP Inspector UI + proxy.
	•	mcp_oauth_admin: Bootstraps an admin user + DOT application.
	•	run_mcp: Runs the FastMCP server over stdio (for CLI/desktop clients).
	•	MCP Client Demo: Example Python script showing how to call MCP tools via fastmcp.Client.
	•	Search Registry: Sample registry mapping Django models (projects, users) to MCP search tools.

Prerequisites
	•	Python 3.10+
	•	Node.js & npm (for npx @modelcontextprotocol/inspector)
	•	SQLite (default) or your choice of Django-supported database

Installation
	1.	Clone the repo:

git clone <repo-url> djproject
cd djproject


	2.	Install Python dependencies:

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt


	3.	Apply migrations:

python manage.py migrate


	4.	Collect static files:

python manage.py collectstatic --no-input



Configuration
	•	Edit djproject/settings.py for database, allowed hosts, and OAuth2 settings.
	•	Ensure OAUTH2_PROVIDER settings (e.g. ACCESS_TOKEN_EXPIRE_SECONDS) are configured if you need custom expiration.

Running the Server

Start Django + FastMCP via ASGI:

uvicorn djproject.asgi:application --host 127.0.0.1 --port 8000

This serves:
	•	http://127.0.0.1:8000/ → Django app
	•	http://127.0.0.1:8000/o/ → OAuth2 endpoints
	•	http://127.0.0.1:8000/mcp/ → FastMCP tools endpoint

Launching the MCP Inspector

The mcp_inspect command will guide you through creating a DOT application (if needed), running the PKCE flow, and launching the Inspector UI + proxy:

python manage.py mcp_inspect

Follow the printed 🔗 Open inspector... link to connect to the UI. Hit Ping to verify connectivity.

Bootstrapping OAuth2 Admin

If you only need to set up the admin user + DOT app without launching the Inspector:

python manage.py mcp_oauth_admin

MCP Client Demo

A standalone Python script demonstrating basic MCP usage:

python apps/mcp/mcp_client_demo.py --username admin --password secret

Project Structure

djproject/
├── asgi.py       # ASGI mount combining Django + FastMCP
├── settings.py   # Django settings + INSTALLED_APPS
├── urls.py       # Django & DOT URL conf
├── wsgi.py       # WSGI entrypoint
├── manage.py     # Django CLI
└── mcp_app/      # FastMCP integration
    ├── auth_basic.py      # Basic HTTP auth middleware
    ├── auth_middleware.py # Combined OAuth2 + session middleware
    ├── auth_session.py    # Session-only middleware
    ├── mcp_server.py     # FastMCP tool definitions
    ├── metadata.py       # OAuth discovery endpoints
    └── management/commands/
        ├── mcp_inspect.py
        ├── mcp_oauth_admin.py
        └── run_mcp.py

Tests

Add your Django TestCases under each app’s tests.py and run:

python manage.py test

License

This project is licensed under the MIT License. Feel free to adapt and extend for your own needs.