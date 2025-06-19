import os
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn

mcp = FastMCP("ocm")

OCM_API_BASE = os.environ.get("OCM_API_BASE", "https://api.openshift.com")

async def make_request(url: str) -> dict[str, Any] | None:
    client_id = os.environ["OCM_CLIENT_ID"]
    offline_token = os.environ["OCM_OFFLINE_TOKEN"]
    access_token_url = os.environ["ACCESS_TOKEN_URL"]
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": offline_token,
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(access_token_url, data=data, timeout=30.0)
            response.raise_for_status()
            token = response.json().get("access_token")
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(e)
            return None


def format_clusters_response(data):
    if not data or "items" not in data:
        return "No clusters found or invalid response."

    lines = []
    for cluster in data["items"]:
        name = cluster.get("name", "N/A")
        cid = cluster.get("id", "N/A")
        api_url = cluster.get("api", {}).get("url", "N/A")
        console_url = cluster.get("console", {}).get("url", "N/A")
        lines.append(
            f"Cluster: {name}\n"
            f"  ID: {cid}\n"
            f"  API URL: {api_url}\n"
            f"  Console URL: {console_url}\n"
        )
    return "\n".join(lines)

def format_whoami_response(data):
    if not data:
        return "No whoami data found."

    lines = []
    username = data.get("username", "N/A")
    id = data.get("id", "N/A")

    lines.append(
        f"Username: {username}\n"
        f"  ID: {id}\n"
    )
    return "\n".join(lines)


def format_addons_response(data):
    if not data or "items" not in data:
        return "No addons found or invalid response."

    lines = []
    for addon in data["items"]:
        name = addon.get("name", "N/A")
        state = addon.get("state", "N/A")
        lines.append(f"Addon: {name}\n" f"  State: {state}\n")
    return "\n".join(lines)


def format_fleet_manager_service_clusters_response(data):
    print(data)
    if not data or "items" not in data:
        return "No service clusters found or invalid response."

    lines = []
    for cluster in data["items"]:
        name = cluster.get("name", "N/A")
        id = cluster.get("id", "N/A")
        status = cluster.get("status", "N/A")
        sector = cluster.get("sector", "N/A")
        creation = cluster.get("creation_timestamp", "N/A")
        lines.append(
            f"Cluster: {name}\n"
            f"  ID: {id}\n"
            f"  STATUS: {status}\n"
            f"  SECTOR: {sector}\n"
            f"  CREATION_TIMESTAMP: {creation}\n"
        )
    return "\n".join(lines)

@mcp.tool()
async def get_clusters(state: str) -> str:
    url = f"{OCM_API_BASE}/api/clusters_mgmt/v1/clusters"
    data = await make_request(url)

    formatted = format_clusters_response(data)
    print(formatted)
    return formatted

@mcp.tool()
async def get_cluster(cluster_id: str) -> str:
    url = f"{OCM_API_BASE}/api/clusters_mgmt/v1/clusters/{cluster_id}"
    data = await make_request(url)
    print(data)
    if data and data.get("id"):
        return format_clusters_response({"items": [data]})


@mcp.tool()
async def get_cluster_addons(cluster_id: str) -> str:
    url = f"{OCM_API_BASE}/api/clusters_mgmt/v1/clusters/{cluster_id}/addons"
    data = await make_request(url)
    print(data)
    if data:
        return format_addons_response(data)
    return "Failed to fetch addons data."


# /api/accounts_mgmt/v1/current_account
@mcp.tool()
async def get_whoami(state: str) -> str:
    url = f"{OCM_API_BASE}/api/accounts_mgmt/v1/current_account"
    data = await make_request(url)
    print(data)
    if data:
        return format_whoami_response(data)
    return "Failed to fetch addons data."

# /api/osd_fleet_mgmt/v1/service_clusters
@mcp.tool()
async def get_fleet_manager_service_clusters(state: str) -> str:
    url = f"{OCM_API_BASE}/api/osd_fleet_mgmt/v1/service_clusters"
    data = await make_request(url)

    formatted = format_fleet_manager_service_clusters_response(data)
    print(formatted)
    return formatted


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

if __name__ == "__main__":
    mcp_server = mcp._mcp_server  # noqa: WPS437

    import argparse

    parser = argparse.ArgumentParser(description='Run MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    uvicorn.run(starlette_app, host=args.host, port=args.port)


# if __name__ == "__main__":
#     mcp.run(transport="stdio")
