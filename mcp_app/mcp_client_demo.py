# apps/mcp/mcp_client_demo.py

import asyncio
import base64
import argparse
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

async def example(url: str, username: str, password: str):
    # Build the Basic auth header
    creds = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {creds}",
        # Ensure you still accept SSE if using StreamableHttpTransport
        "Accept": "application/json, text/event-stream",
    }

    transport = StreamableHttpTransport(url, headers=headers)
    async with Client(transport) as client:
        await client.ping()
        print("✅ Ping successful!")

        tools = await client.list_tools()
        print("🛠️ Available tools:", tools)

        resp = await client.call_tool("echo", {"message": "Hello, FastMCP!"})
        print("🔁 Echo:", resp)

        resp = await client.call_tool("ai_prompt", {"prompt": "What is the capital of France?"})
        print("🧠 AI Prompt:", resp)

        resp = await client.call_tool("search_project", {"query": "Station"})
        print("🔍 Search Project:", resp)

        resp = await client.call_tool("search_any", {"model": "project", "query": "Station"})
        print("📦 Search Any:", resp)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp/", help="MCP base URL")
    parser.add_argument("--username", required=True, help="Django username")
    parser.add_argument("--password", required=True, help="Django password")
    args = parser.parse_args()

    asyncio.run(example(args.url, args.username, args.password))