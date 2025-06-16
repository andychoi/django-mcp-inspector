import logging
import subprocess
import secrets
import hashlib
import base64
import re
from urllib.parse import urlencode

import requests
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from oauth2_provider.models import get_application_model
from .forms import MCPLauncherForm, CodeEntryForm

# Logging setup
logger = logging.getLogger("mcp.launcher")
logging.basicConfig(level=logging.INFO)

# Constants
AUTH_URL       = "http://127.0.0.1:8000/o/authorize/"
TOKEN_URL      = "http://127.0.0.1:8000/o/token/"
INTROSPECT_URL = "http://127.0.0.1:8000/o/introspect/"
REVOKE_URL     = "http://127.0.0.1:8000/o/revoke/"
INSPECTOR_HTTP = "http://127.0.0.1:8000/mcp/"
INSPECTOR_UI   = "http://127.0.0.1:6274/"
REDIRECT_URI   = INSPECTOR_UI + "auth/callback"
SCOPE          = "read write"


def generate_pkce_pair():
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    logger.info(f"PKCE generated: verifier={verifier}, challenge={challenge}")
    return verifier, challenge



def mcp_launcher(request):
    """
    Step 1: show form to enter client credentials,
    then open OAuth in new tab and show code entry form.
    """
    code_form = None
    if request.method == "POST" and "start_auth" in request.POST:
        form = MCPLauncherForm(request.POST)
        if form.is_valid():
            # create/fetch app if needed
            client_id = form.cleaned_data['client_id']
            client_secret = form.cleaned_data['client_secret']
            username = form.cleaned_data['mcp_service_username'] or 'mcp_service'

            Application = get_application_model()
            if not client_id:
                user, _ = get_user_model().objects.get_or_create(
                    username=username,
                    defaults={'email': f"{username}@localhost", 'is_superuser': True, 'is_staff': True}
                )
                client_type = (Application.CLIENT_CONFIDENTIAL if client_secret
                               else Application.CLIENT_PUBLIC)
                app, _ = Application.objects.get_or_create(
                    name=f"MCP Inspector App ({username})",
                    user=user,
                    client_type=client_type,
                    authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                    defaults={'redirect_uris': REDIRECT_URI},
                )
                client_id = app.client_id
                client_secret = app.client_secret or client_secret
                logger.info(f"Created OAuth app: {client_id}, confidential={bool(client_secret)}")

            # PKCE
            verifier, challenge = generate_pkce_pair()
            request.session['pkce_verifier'] = verifier
            request.session['client_id'] = client_id
            request.session['client_secret'] = client_secret

            # Build authorize URL
            params = {
                'response_type': 'code',
                'client_id': client_id,
                'redirect_uri': REDIRECT_URI,
                'scope': SCOPE,
                'code_challenge': challenge,
                'code_challenge_method': 'S256',
            }
            auth_url = f"{AUTH_URL}?{urlencode(params)}"
            logger.info(f"Opening OAuth URL: {auth_url}")

            # In template JS, this will be opened in new tab
            code_form = CodeEntryForm()
        else:
            logger.warning(f"Launcher form invalid: {form.errors}")
    else:
        form = MCPLauncherForm()

    return render(request, 'mcp_launcher.html', {
        'form': form,
        'code_form': code_form,
        'auth_url': auth_url if code_form else None,
    })


def mcp_finalize(request):
    """
    Step 2: receive pasted code, exchange for token, launch Inspector CLI.
    """
    form = CodeEntryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        code = form.cleaned_data['code']
        verifier = request.session.get('pkce_verifier')
        client_id = request.session.get('client_id')
        client_secret = request.session.get('client_secret')
        logger.info(f"Finalizing with code={code}")

        # Exchange code for access token
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,
            'code_verifier': verifier,
            'client_id': client_id,
        }
        if client_secret:
            data['client_secret'] = client_secret
        resp = requests.post(TOKEN_URL, data=data)
        if not resp.ok:
            logger.error(f"Token exchange error: {resp.status_code} {resp.text}")
            return render(request, 'mcp_error.html', {'error': 'Token exchange failed.'})
        token = resp.json().get('access_token')
        logger.info(f"Access token: {token}")

        # Launch the Inspector CLI
        cmd = [
            'npx', '@modelcontextprotocol/inspector', INSPECTOR_HTTP,
            '--transport', 'streamable-http',
            '--header', 'Accept:application/json, text/event-stream',
            '--header', f'Authorization: Bearer {token}',
            '--auth-url', AUTH_URL,
            '--token-url', TOKEN_URL,
            '--introspect', INTROSPECT_URL,
            '--revocation', REVOKE_URL,
            '--client-id', client_id,
            '--redirect', REDIRECT_URI,
        ]
        if client_secret:
            cmd += ['--client-secret', client_secret]

        # 1) Spawn the Inspector CLI
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # 2) Capture the MCP_PROXY_AUTH_TOKEN from the printed URL
        proxy_token = None
        token_re    = re.compile(r"MCP_PROXY_AUTH_TOKEN=([0-9a-f]+)")
        for line in proc.stdout:
            logger.info("Inspector CLI: %s", line.rstrip())
            m = token_re.search(line)
            if m:
                proxy_token = m.group(1)
                logger.info("Captured MCP_PROXY_AUTH_TOKEN: %s", proxy_token)
                break

        if not proxy_token:
            logger.error("Failed to capture MCP_PROXY_AUTH_TOKEN from Inspector CLI output")
            return render(request, "mcp_error.html", {
                "error": "Could not start Inspector (no proxy token)."
            })

        # 3) Render the “launched” page with that token embedded in the link
        return render(request, "mcp_launched.html", {
            "inspector_ui": INSPECTOR_UI,      # e.g. http://127.0.0.1:6274/
            'bearer_token': token,
            'proxy_token': proxy_token,
        })

