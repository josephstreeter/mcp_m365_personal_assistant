# Claude Setup - M365 Productivity Assistant MCP

## Add via Claude CLI

```bash
claude mcp add m365-productivity-assistant-mcp \
  -t stdio \
  -e client_id=your-client-id-here \
  -e tenant_id=your-tenant-id-here \
  -- uv run python /absolute/path/to/personal_mcp_server/main.py
```

## Manual JSON Configuration

```json
{
  "mcpServers": {
    "m365-productivity-assistant-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "python",
        "/absolute/path/to/personal_mcp_server/main.py"
      ],
      "env": {
        "client_id": "your-client-id-here",
        "tenant_id": "your-tenant-id-here"
      }
    }
  }
}
```
