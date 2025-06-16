# MCP server

If you want HTTP-based testing, that should be done via uvicorn djproject.asgi:application

## Run FastMCP
Thanks for sharing your wsgi.py and asgi.py setup — you’re combining a Django app with a FastMCP server, served via ASGI with Starlette (and optionally via WSGI for traditional HTTP deployments).

Here’s how to run your FastMCP server for testing given your setup:

⸻

✅ 1. Best Way to Run for Dev Testing: ASGI App (Recommended)

Since you’re integrating MCP into your ASGI app, just run the whole project via uvicorn, which supports both Starlette and Django ASGI.

✅ Run with uvicorn:

uvicorn djproject.asgi:application --reload

	•	This will:
	•	Serve Django under /
	•	Serve FastMCP tools under /mcp
	•	With --reload, it auto-restarts on code changes (great for development).
	•	By default, it’ll run on http://127.0.0.1:8000.

🔍 Test your MCP tool

To test the /mcp/echo tool via HTTP:

curl -X POST http://localhost:8000/mcp/echo -H "Content-Type: application/json" -d '{"message": "Hello"}'

Response should be:

{"Echo": "Hello"}


⸻

✅ 2. Alternative: Stdio Mode for Claude Desktop

If you still want to run FastMCP via stdio mode (e.g. for Claude Desktop), you can still use your original mcp_server.py as a standalone script:

a. Modify mcp_server.py (already done above, just make sure Django is initialized):

import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djproject.settings.settings")
django.setup()

b. Run it with Python:

python apps/mcp/server/mcp_server.py

Claude Desktop will then use stdio transport to communicate with this subprocess.

⸻

✅ 3. Notes on Deployment / Production
	•	Production HTTP mode: Your asgi.py is ready for production with uvicorn or daphne.
	•	Static file handling: You’re using WhiteNoise when not using NGINX, which is fine for simple setups or small deployments.

⸻

✅ 4. Summary

Scenario	Command
Dev server via ASGI	uvicorn djproject.asgi:application --reload
Claude Desktop (stdio)	python apps/mcp/server/mcp_server.py
Production ASGI (e.g. NGINX)	uvicorn djproject.asgi:application + serve via reverse proxy

Let me know if you want to integrate this into Django management commands or Dockerize it for deployment.




To integrate the MCP server into a Django management command, follow these steps:

⸻

✅ Step 1: Create a Custom Django Management Command

Create a new file:

apps/mcp/management/commands/run_mcp.py

If management/commands folders don’t exist yet, create them manually.

⸻

✅ Step 2: Add the Command Code

# apps/mcp/management/commands/run_mcp.py

import os
import django
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Run FastMCP server (stdio or http mode)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--transport',
            type=str,
            choices=['stdio', 'http'],
            default='stdio',
            help="Transport method for FastMCP (default: stdio)",
        )
        parser.add_argument('--host', type=str, default='127.0.0.1', help="Host for HTTP transport")
        parser.add_argument('--port', type=int, default=8001, help="Port for HTTP transport")

    def handle(self, *args, **options):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djproject.settings.settings")
        django.setup()

        from apps.mcp.server.mcp_server import mcp as mcp_instance

        transport = options['transport']
        host = options['host']
        port = options['port']

        if transport == "stdio":
            self.stdout.write(self.style.SUCCESS("Running FastMCP server (stdio)..."))
            mcp_instance.run(transport="stdio")
        else:
            self.stdout.write(self.style.SUCCESS(f"Running FastMCP server (http) on {host}:{port}..."))
            mcp_instance.run(transport="http", host=host, port=port)


⸻

✅ Step 3: Run the MCP Server with the Command

➤ Run in stdio mode (Claude Desktop):

python manage.py run_mcp

➤ Run in HTTP mode:

python manage.py run_mcp --transport http --host 127.0.0.1 --port 8001


⸻

✅ Bonus: Add Autocomplete Shell Option (Optional)

If you want a nicer shell experience, you could add aliases in your Makefile or shell script:

run-mcp:
	python manage.py run_mcp --transport http --host 127.0.0.1 --port 8001


⸻

Let me know if you’d like to:
	•	Add logging
	•	Auto-restart on code change (dev mode)
	•	Run it in a Docker container
	•	Or expose the MCP tools via Django URLs directly (without Starlette mount)

## TEST

```
curl -X POST http://127.0.0.1:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "echo",
    "params": {
      "message": "hello"
    },
    "id": 1
  }'
{"jsonrpc":"2.0","id":"server-error","error":{"code":-32600,"message":"Bad Request: Missing session ID"}}%       


SID=$(curl -s -I \
        -H "Accept: text/event-stream" \
        http://127.0.0.1:8000/mcp/session/new |
      awk -F': ' '/^mcp-session-id:/ {print $2}' | tr -d '\r')

echo "Session ID  👉  $SID"
```


## Django-MCP-Server package    
Below is a sketch of how you can leverage django-mcp-server to give your AI agent a way to “call” Django-side functions (e.g. search models, fetch user info, etc.) instead of embedding those lookups directly in your chat_api. In essence, you:
	1.	Install and configure django-mcp-server.
	2.	Register a small set of “MCP commands” (e.g. search_project, search_any, get_user_info, etc.) on the server. Each command is just a Python method that returns JSON.
	3.	In your AI‐prompt handler (e.g. in chat_api when type="ai_prompt"), you call the MCP endpoint (using requests or the built-in HTTP client in your AI wrapper). The AI agent’s prompt can include instructions like “call MCP command search_project with query=‘urgent’.”
	4.	django‐mcp‐server routes that call to the Python method, which runs Django ORM lookups or any other logic. The MCP server then returns JSON to your AI agent.
	5.	Finally, you take that JSON reply and send it back to the user (or feed it into your LLM as context).

Below is a step-by-step walk-through. (If you only want a quick code snippet, skip to “Putting it all together” at the end.)

⸻

1. Install & configure django-mcp-server

pip install django-mcp-server

In your settings.py, add mcpserver to INSTALLED_APPS, and configure its URL:

# settings.py

INSTALLED_APPS = [
    # … your other apps …
    "mcpserver",
    "apps.ai",         # your AI app
    "apps.psm",        # your PSM app
    # etc.
]

# (any other MCP settings can go here, but defaults usually work)

In your project’s urls.py, mount the MCP server endpoint:

# project_root/urls.py

from django.urls import path, include

urlpatterns = [
    # … other includes …

    # All MCP calls should go to /mcp/ (for example)
    path("mcp/", include("mcpserver.urls")),

    # If you also have your existing chat_api views:
    path("api/chat/", include(("apps.ai.views", "ai"), namespace="chat_api")),
]

By default, django-mcp-server will listen on /mcp/. Anyone doing an HTTP POST there with a JSON payload like:

{
  "command": "my_command_name",
  "arguments": { /* … */ }
}

will be routed to a Python function mcp_my_command_name(request, **arguments) that you register. The reply should be JSON.

⸻

2. Register your MCP commands

In any app (e.g. apps/ai), create a file called mcp_handlers.py. Each function you want to expose via MCP must be named mcp_<command>. For example:

# apps/ai/mcp_handlers.py

import json
from django.contrib.auth import get_user_model
from django.db.models import Q
from psm.models import Project
from .search_registry import SEARCHABLE_MODELS

User = get_user_model()


def mcp_search_projects(request, query: str):
    """
    MCP command: { "command": "search_projects", "arguments": { "query": "foo" } }
    Returns up to 5 project names (strings).
    """
    qs = Project.objects.filter(name__icontains=query)[:5]
    names = [p.name for p in qs]
    return {"results": names}


def mcp_search_any(request, model: str, query: str):
    """
    MCP command: { "command": "search_any", "arguments": { "model": "projects", "query": "foo" } }
    Returns a list of { name, url } dicts for the first 5 matches.
    """
    if model not in SEARCHABLE_MODELS:
        return {"error": "Unknown model"}

    conf = SEARCHABLE_MODELS[model]
    Qobj = Q()
    for f in conf["fields"]:
        Qobj |= Q(**{f"{f}__icontains": query})

    matches = conf["model"].objects.filter(Qobj)[:5]
    output = []
    for obj in matches:
        name = conf["display"](obj)
        url = conf["get_url"](obj)
        output.append({"name": name, "url": url})
    return {"results": output}


def mcp_get_user_info(request):
    """
    MCP command: { "command": "get_user_info", "arguments": {} }
    Returns simple username/alias strings (requires logged‐in user).
    """
    if not request.user.is_authenticated:
        return {"error": "Not authenticated"}
    uname = request.user.username
    alias = getattr(request.user, "alias", "")
    return {"results": {"username": uname, "alias": alias}}


def mcp_ai_prompt(request, prompt: str):
    """
    MCP command: { "command": "ai_prompt", "arguments": { "prompt": "<text>" } }
    Generates an AI response (no RAG). Uses your GenAIWrapper.
    """
    from .aiwrapper import GenAIWrapper

    prompt = prompt.strip()
    if not prompt:
        return {"error": "Empty prompt"}

    genai = GenAIWrapper()
    try:
        answer = genai.ai_response(prompt)
    except Exception as e:
        return {"error": f"AI error: {e}"}

    return {"results": answer}

Important: django-mcp-server automatically scans each installed app’s mcp_handlers.py (if it exists). Any function that starts with mcp_ becomes a valid MCP command. The request object is passed in, along with any named arguments you specify in the JSON payload.

⸻

3. Adjust your front‐end or chat_api to call MCP

3.1. Option A – Direct MCP calls from Vue

You can bypass your old /api/chat/ view entirely for AI calls and search calls, and call /mcp/ directly from your Vue widget. Example for “search_any”:

async function callMcp(command, args) {
  const payload = {
    command: command,
    arguments: args
  };
  const res = await fetch("/mcp/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return await res.json();
}

// When user picks “Search Any” in Vue:
const argObj = { model: "projects", query: this.newMessage };
const responseJson = await callMcp("search_any", argObj);
if (responseJson.results) {
  responseJson.results.forEach(item => {
    // item = { name: "...", url: "..." }
    this.messages.push({ from: "bot", text: item.name, url: item.url });
  });
}

Similarly for "search_projects", "get_user_info", or "ai_prompt". In each case, you:
	1.	Build { command: "mcp_command_name", arguments: { … } }.
	2.	POST it to /mcp/.
	3.	MCP server introspects the JSON, discovers mcp_<command>, calls it, and returns the Python dict as JSON.
	4.	Vue parses out .results and displays it.

3.2. Option B – “chat_api” delegates to MCP

If you’d rather keep one endpoint (/api/chat/) and want all logic to remain in chat_api, you can have that view simply forward certain types to MCP. For example:

# apps/ai/views.py (inside chat_api logic)

import requests
from django.conf import settings

# … inside your chat_api(req): …

elif req_type == "search_any":
    # Forward JSON to the MCP endpoint
    mcp_payload = {
        "command": "search_any",
        "arguments": {
            "model": payload["model"],
            "query": payload["query"],
        }
    }
    mcp_res = requests.post(
        request.build_absolute_uri("/mcp/"),
        json=mcp_payload,
        cookies=request.COOKIES,  # to preserve session/auth if needed
        timeout=10,
    )
    if mcp_res.status_code != 200:
        return JsonResponse({"error": "MCP server error"}, status=500)
    mcp_data = mcp_res.json()
    # Expect {"results": [ ... ]} or {"error": "..."}
    if "error" in mcp_data:
        return JsonResponse({"error": mcp_data["error"]}, status=400)
    return JsonResponse({
        "type": "search_any",
        "replies": mcp_data["results"]
    })

elif req_type == "ai_prompt":
    # Forward to MCP:
    mcp_payload = {
        "command": "ai_prompt",
        "arguments": {
            "prompt": payload.get("message", "")
        }
    }
    mcp_res = requests.post(
        request.build_absolute_uri("/mcp/"),
        json=mcp_payload,
        cookies=request.COOKIES,
        timeout=30,
    )
    if mcp_res.status_code != 200:
        return JsonResponse({"error": "MCP server error"}, status=500)
    mcp_data = mcp_res.json()
    if "error" in mcp_data:
        return JsonResponse({"error": mcp_data["error"]}, status=400)

    # Optionally save to ChatMessage
    ai_text = mcp_data["results"]
    if request.user.is_authenticated:
        ChatMessage.objects.create(user=request.user, message=payload.get("message", ""), response=ai_text)

    return JsonResponse({"type": "ai_prompt", "replies": [ai_text]})

That way, chat_api becomes a thin “router” that forwards specialized calls to MCP. You could do the same for “search_projects” or “get_user_info” if you prefer to centralize everything in MCP.

⸻

4. Putting it all together

Below is a minimal end‐to‐end example. Assume you want to keep a single /api/chat/ endpoint, and you route "search_any" and "ai_prompt" through MCP.

4.1. apps/ai/mcp_handlers.py

# apps/ai/mcp_handlers.py

import json
from django.db.models import Q
from django.contrib.auth import get_user_model
from psm.models import Project
from .search_registry import SEARCHABLE_MODELS
from .aiwrapper import GenAIWrapper
from .models import Document

User = get_user_model()

def mcp_search_any(request, model: str, query: str):
    if model not in SEARCHABLE_MODELS:
        return {"error": "Unknown model"}
    conf = SEARCHABLE_MODELS[model]
    Qobj = Q()
    for f in conf["fields"]:
        Qobj |= Q(**{f"{f}__icontains": query})
    matches = conf["model"].objects.filter(Qobj)[:5]
    output = []
    for obj in matches:
        output.append({
            "name": conf["display"](obj),
            "url": conf["get_url"](obj)
        })
    return {"results": output}

def mcp_ai_prompt(request, prompt: str):
    prompt = prompt.strip()
    if not prompt:
        return {"error": "Empty prompt"}
    # Optionally: do RAG here (omitted for brevity)
    genai = GenAIWrapper()
    try:
        answer = genai.ai_response(prompt)
    except Exception as e:
        return {"error": f"AI error: {e}"}
    return {"results": answer}

4.2. apps/ai/views.py (chat_api)

# apps/ai/views.py

import json, requests
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import ChatMessage

@csrf_exempt
@require_POST
def chat_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponseBadRequest("Invalid JSON")

    req_type = payload.get("type", "chat")

    # … your chat, search_projects, get_user_info code here …

    elif req_type == "search_any":
        model_key = payload.get("model")
        query = payload.get("query", "")
        if not model_key or not query:
            return HttpResponseBadRequest("Missing model or query")

        # Forward to MCP:
        mcp_payload = {
            "command": "search_any",
            "arguments": {"model": model_key, "query": query}
        }
        mcp_res = requests.post(
            request.build_absolute_uri("/mcp/"),
            json=mcp_payload,
            cookies=request.COOKIES
        )
        if mcp_res.status_code != 200:
            return JsonResponse({"error": "MCP error"}, status=500)
        mcp_data = mcp_res.json()
        if "error" in mcp_data:
            return JsonResponse({"error": mcp_data["error"]}, status=400)
        return JsonResponse({"type": "search_any", "replies": mcp_data["results"]})

    elif req_type == "ai_prompt":
        prompt = payload.get("message", "").strip()
        if not prompt:
            return HttpResponseBadRequest("Empty prompt")
        mcp_payload = {
            "command": "ai_prompt",
            "arguments": {"prompt": prompt}
        }
        mcp_res = requests.post(
            request.build_absolute_uri("/mcp/"),
            json=mcp_payload,
            cookies=request.COOKIES,
            timeout=30,
        )
        if mcp_res.status_code != 200:
            return JsonResponse({"error": "MCP error"}, status=500)
        mcp_data = mcp_res.json()
        if "error" in mcp_data:
            return JsonResponse({"error": mcp_data["error"]}, status=400)

        ai_text = mcp_data["results"]
        if request.user.is_authenticated:
            ChatMessage.objects.create(user=request.user, message=prompt, response=ai_text)

        return JsonResponse({"type": "ai_prompt", "replies": [ai_text]})

    else:
        return HttpResponseBadRequest(f"Unknown type: {req_type}")

4.3. Vue calls (in _chat.html)

Wherever you have:

async _callApiAndHandleReplies(payload) {
  const res = await fetch("/api/chat/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  // … deal with data.replies …
}

When payload = { type: "search_any", model: "projects", query: "urgent" }, your Django view automatically forwards to MCP, which runs mcp_search_any behind the scenes. The JSON {"results":[{name,url},…]} comes back to your Vue and gets rendered as clickable links.

Similarly, when payload = { type: "ai_prompt", message: "Explain Q2 status" }, your view forwards to MCP, which calls mcp_ai_prompt, which in turn calls your GenAIWrapper and returns {"results": "<AI’s answer>"}. Vue then displays that as a bot bubble.

⸻

5. Why use django-mcp-server?
	•	Separation of concerns: Instead of stuffing RAG or search logic into one giant view, you register small self‐contained “commands” (mcp_search_any, mcp_ai_prompt, etc.) in mcp_handlers.py.
	•	LLM agents can “call” commands: If you ever adopt function‐calling in a true LLM (e.g. OpenAI function API), you can have the LLM generate a JSON like:

{
  "name": "search_any",
  "arguments": {"model":"projects","query":"urgent"}
}

and your front‐end simply POSTs that to /mcp/—no extra glue code is needed.

	•	Uniform interface: All “functions” (search, ai_prompt, etc.) run under the same /mcp/ endpoint. You don’t need a dozen separate URLs.

⸻

6. Final checklist
	1.	pip install django-mcp-server
	2.	Add "mcpserver" to INSTALLED_APPS and path("mcp/", include("mcpserver.urls")) to your urls.py.
	3.	Create apps/ai/mcp_handlers.py with mcp_<command> functions for each action you want available to the AI agent (e.g. mcp_search_any, mcp_ai_prompt, etc.).
	4.	In chat_api (or your front-end), forward the right JSON to /mcp/ whenever you need your AI agent or your search calls to run a server‐side function.
	5.	Test by hitting /mcp/ with a simple curl:

curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"command":"search_any","arguments":{"model":"projects","query":"urgent"}}'

You should see a JSON reply like:

{ "results": [ { "name":"Urgent Q2","url":"/psm/project/123/" }, … ] }


	6.	Wire up your Vue widget so that when the user clicks “AI Prompt” or “Search Any,” it builds exactly the {"type":"…","model":…,"query":…} or {"type":"ai_prompt","message":…} payload and sends it to /api/chat/. The view will forward those to MCP under the hood.

That’s it—now your AI agent truly “calls” Django functions (including ORM queries, business logic, etc.) through a standard MCP interface.