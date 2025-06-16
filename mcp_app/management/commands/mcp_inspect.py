# mcp_inspect.py
import subprocess
import webbrowser
import hashlib
import secrets
import base64
import requests
from urllib.parse import urlencode

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from oauth2_provider.models import get_application_model

"""
Usage:
  python manage.py mcp_inspect [--client-id <ID> --client-secret <SECRET>] [--no-browser]

- If --client-id is passed, the script uses the existing Application.
- For Confidential apps, you must pass --client-secret.
- For Public apps, omit --client-secret (PKCE-only).
"""

def generate_pkce_pair():
    # Generate a code_verifier (43–128 chars) and its S256 code_challenge
    code_verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge

class Command(BaseCommand):
    help = "Perform OAuth2 PKCE flow and launch MCP Inspector."

    def add_arguments(self, parser):
        parser.add_argument("--client-id",     type=str, help="Existing OAuth2 client ID")
        parser.add_argument("--client-secret", type=str, default="", help="OAuth2 client secret (confidential)")
        parser.add_argument("--username",      type=str, default="mcp_service", help="Admin username for new app")
        parser.add_argument("--password",      type=str, default="mcp_service123!", help="Admin password for new app")
        parser.add_argument("--email",         type=str, default="mcp_service@localhost", help="Admin email for new app")
        parser.add_argument("--client-name",   type=str, default="MCP Inspector App", help="OAuth app name when creating")
        parser.add_argument("--redirect-uri",  type=str, default="http://127.0.0.1:6274/auth/callback", help="OAuth2 redirect URI")
        parser.add_argument("--auth-url",      type=str, default="http://127.0.0.1:8000/o/authorize/", help="Authorization endpoint")
        parser.add_argument("--token-url",     type=str, default="http://127.0.0.1:8000/o/token/", help="Token endpoint")
        parser.add_argument("--introspect-url",type=str, default="http://127.0.0.1:8000/o/introspect/", help="Introspection endpoint")
        parser.add_argument("--revoke-url",    type=str, default="http://127.0.0.1:8000/o/revoke/", help="Revocation endpoint")
        parser.add_argument("--scope",         type=str, default="read write", help="OAuth scopes (space-separated)")
        parser.add_argument("--inspector-url", type=str, default="http://127.0.0.1:8000/mcp/", help="MCP HTTP URL")
        parser.add_argument("--transport",     type=str, default="streamable-http", help="Inspector transport protocol")
        parser.add_argument("--no-browser", dest="no_browser", action="store_true", help="Skip opening browser")

    def handle(self, *args, **opts):
        Application = get_application_model()
        client_id = opts.get("client_id")
        client_secret = opts.get("client_secret")

        # If client_id provided, fetch the Application
        if client_id:
            try:
                app = Application.objects.get(client_id=client_id)
            except Application.DoesNotExist:
                raise CommandError(f"OAuth2 Application with client_id={client_id} not found.")
        else:
            # Create admin user and public app
            User = get_user_model()
            user, created = User.objects.get_or_create(
                username=opts["username"],
                defaults={"email": opts["email"], "is_superuser": True, "is_staff": True},
            )
            if created:
                user.set_password(opts["password"])
                user.save()
                self.stdout.write(self.style.SUCCESS(f"✅ Created admin user: {user.username}"))
            else:
                self.stdout.write(self.style.WARNING(f"ℹ️ Admin user '{user.username}' already exists"))

            app, created = Application.objects.get_or_create(
                name=opts["client_name"], user=user,
                client_type=Application.CLIENT_PUBLIC,
                authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                defaults={"redirect_uris": opts["redirect_uri"]},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Created OAuth2 app: {app.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"ℹ️ OAuth2 app '{app.name}' already exists"))

        # Determine client type
        client_id = client_id or app.client_id
        client_secret = client_secret or getattr(app, "client_secret", "")
        is_confidential = app.client_type == Application.CLIENT_CONFIDENTIAL

        # If confidential, require secret
        if is_confidential and not client_secret:
            raise CommandError("OAuth2 client secret is required for a confidential application.")

        # Generate PKCE verifier & challenge
        code_verifier, code_challenge = generate_pkce_pair()
        self.stdout.write(f"🔐 Generated PKCE verifier (len={len(code_verifier)})")

        # Build authorization URL
        params = {
            "response_type":         "code",
            "client_id":             client_id,
            "redirect_uri":          opts["redirect_uri"],
            "scope":                 opts["scope"],
            "code_challenge":        code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"{opts['auth_url']}?{urlencode(params)}"
        self.stdout.write("\n📎 Open this URL to authorize:")
        self.stdout.write(auth_url)
        if not opts["no_browser"]:
            webbrowser.open(auth_url)

        # Prompt for code
        code = input("\n🔑 Paste the `code` from the callback URL: ").strip()
        if not code:
            raise CommandError("No authorization code provided; aborting.")

        # Prepare token exchange
        token_data = {
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  opts["redirect_uri"],
            "code_verifier": code_verifier,
        }
        headers = {"Accept": "application/json"}

        if is_confidential:
            # Confidential: use Basic auth
            auth = (client_id, client_secret)
        else:
            # Public: include client_id in body
            auth = None
            token_data["client_id"] = client_id

        self.stdout.write(f"\n📡 Exchanging code at {opts['token_url']}…")
        resp = requests.post(opts["token_url"], data=token_data, auth=auth, headers=headers)
        if not resp.ok:
            raise CommandError(f"❌ Token request failed: {resp.status_code} {resp.text}")
        tok = resp.json()
        access_token = tok.get("access_token")
        if not access_token:
            raise CommandError(f"❌ No access_token in response: {tok}")
        self.stdout.write(self.style.SUCCESS("✅ Access token acquired."))
        # Log the bearer token for Inspector use
        self.stdout.write(f"🔑 Bearer token: {access_token}")

        # Launch MCP Inspector
        inspector_url = opts["inspector_url"].rstrip("/") + "/"
        cmd = [
            "npx", "@modelcontextprotocol/inspector", inspector_url,
            "--transport", opts["transport"],
            "--header", "Accept:application/json, text/event-stream",
            "--header", f"Authorization: Bearer {access_token}",
            "--auth-url", opts["auth_url"],
            "--token-url", opts["token_url"],
            "--introspect", opts["introspect_url"],
            "--revocation", opts["revoke_url"],
            "--client-id", client_id,
            "--redirect", opts["redirect_uri"],
        ]
        self.stdout.write(self.style.NOTICE(f"\n🕵️ Running Inspector:\n    {' '.join(cmd)}"))
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                self.stdout.write(line.rstrip())
            exit_code = proc.wait()
            if exit_code != 0:
                raise CommandError(f"❌ Inspector exit code {exit_code}")
            self.stdout.write(self.style.SUCCESS("✅ Inspector finished successfully"))
        except FileNotFoundError:
            raise CommandError("`npx` not found: please install Node.js & npm/npx.")
