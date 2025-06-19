# ocm-mcp

MCP server for Red Hat OpenShift Cluster Manager

## Running with Podman or Docker

You can run the ocm-mcp server in a container using Podman or Docker. Make sure you have a valid OCM token, which you can obtain by logging into https://console.redhat.com/openshift/token:

Example configuration for running with Podman:

```json
{
  "mcpServers": {
    "ocm-mcp": {
      "command": "podman",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "ACCESS_TOKEN_URL",
        "-e", "OCM_CLIENT_ID",
        "-e", "OCM_OFFLINE_TOKEN",
        "quay.io/maorfr/ocm-mcp"
      ],
      "env": {
        "ACCESS_TOKEN_URL": "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token",
        "OCM_CLIENT_ID": "cloud-services",
        "OCM_OFFLINE_TOKEN": "REDACTED"
      }
    }
  }
}
```

Replace `REDACTED` with the value from https://console.redhat.com/openshift/token.

## Running with MCPHost and Podman

```json
{
  "mcpServers": {
    "ocm-mcp": {
      "url": "http://0.0.0.0:8080/sse",
      "headers":[
        "Authorization: Bearer my-token"
       ]
    }
  }
}
```

Where the MCP Server is deployed via:

```bash
# start up the MCP Server
podman run --network podman -i --rm \
-p 8080:8080 \
-e ACCESS_TOKEN_URL="https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token" \
-e OCM_CLIENT_ID="cloud-services" \
-e OCM_API_BASE="https://api.openshift.com" \
-e OCM_OFFLINE_TOKEN="$OCM_OFFLINE_TOKEN" \
quay.io/cdoan25/ocm-mcp:sse
```
