# M365 Productivity Assistant MCP

Standalone MCP server for Microsoft 365 productivity tools.

This folder is repository-ready and can be moved directly into its own Git repository.

## Setup

1. Create local environment variables:

```bash
cp .env.example .env
```

2. Install dependencies with uv:

```bash
uv sync
```

Alternative with pip:

```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`:

```env
client_id=your-application-client-id-here
tenant_id=your-directory-tenant-id-here
```

## Graph Permission Matrix

Configured scopes are defined in `modules/graph_client.py`.

| Scope | Tool coverage |
| --- | --- |
| `User.Read` | `get_user_profile` |
| `Tasks.Read`, `Tasks.ReadWrite` | `get_todo_tasks`, `create_todo_task`, `complete_todo_task` |
| `Mail.Read`, `Mail.Send` | `get_messages`, `search_messages`, `get_message_by_id`, `send_message` |
| `Calendars.Read`, `Calendars.ReadWrite` | `get_calendar_events`, `create_calendar_event` |
| `Contacts.Read` | `get_contacts` |
| `Files.Read`, `Files.Read.All` | `get_recent_files`, `search_files`, `get_trending_files` |
| `Chat.Read`, `Chat.ReadWrite` | `get_teams_chats`, `get_chat_messages`, `send_chat_message` |
| `Channel.ReadBasic.All`, `Group.Read.All` | `get_teams_and_channels` |
| `Presence.Read.All` | `get_user_presence` |
| `People.Read` | `get_relevant_people` |
| `Sites.Read.All`, `Notes.Read` | `get_onenote_notebooks`, `get_onenote_pages` |
| `ThreatHunting.Read.All` | Reserved for future personal security insights tools |

## Run

```bash
uv run python main.py
```

Optional HTTP mode:

```bash
uv run python main.py --transport http --port 8001
```

## Claude/Copilot Integration

See `CLAUDE_SETUP.md` in this folder for standalone MCP configuration examples.

## Standalone Repo Contents

- `main.py` - MCP server entrypoint
- `modules/` - Personal assistant and Graph client modules
- `pyproject.toml` - Project metadata and dependencies
- `uv.lock` - Locked dependency graph for reproducible installs
- `.env.example` - Environment template
- `.gitignore` - Local repo ignores
