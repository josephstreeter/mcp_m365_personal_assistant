# M365 Productivity Assistant MCP

Standalone MCP server for Microsoft 365 productivity tools.

This folder is repository-ready and can be moved directly into its own Git repository.

## Setup

1. Create local environment variables:

```bash
cp .env.example .env
```

1. Install dependencies with uv:

```bash
uv sync
```

Alternative with pip:

```bash
pip install -r requirements.txt
```

1. Configure environment variables in `.env`:

```env
client_id=your-application-client-id-here
tenant_id=your-directory-tenant-id-here
```

## Graph Permission Matrix

Configured scopes are defined in `modules/graph_client.py`.

| Scope | Tool coverage |
| --- | --- |
| `User.Read` | `get_user_profile`, `health_check`, `get_daily_briefing` |
| `Tasks.Read`, `Tasks.ReadWrite` | `get_todo_tasks`, `create_todo_task`, `complete_todo_task`, `get_todo_lists`, `update_todo_task`, `delete_todo_task`, `create_todo_list`, `get_daily_briefing` |
| `Mail.Read`, `Mail.Send` | `get_messages`, `search_messages`, `get_message_by_id`, `send_message`, `list_mail_folders`, `get_message_attachments`, `get_daily_briefing`, `prepare_meeting_brief` |
| `Mail.ReadWrite` | `reply_to_message`, `mark_message_read`, `move_message` |
| `Calendars.Read`, `Calendars.ReadWrite` | `get_calendar_events`, `create_calendar_event`, `update_calendar_event`, `delete_calendar_event`, `respond_to_event`, `find_meeting_times`, `get_daily_briefing`, `prepare_meeting_brief` |
| `Contacts.Read` | `get_contacts` |
| `Files.Read`, `Files.Read.All` | `get_recent_files`, `search_files`, `get_trending_files`, `list_drive_items`, `get_daily_briefing`, `prepare_meeting_brief` |
| `Files.ReadWrite` | `create_share_link`, `upload_small_text_file` |
| `Chat.Read`, `Chat.ReadWrite` | `get_teams_chats`, `get_chat_messages`, `send_chat_message` |
| `ChannelMessage.Send` | `send_channel_message` |
| `Channel.ReadBasic.All`, `Group.Read.All` | `get_teams_and_channels` |
| `Presence.Read.All` | `get_user_presence` |
| `People.Read` | `get_relevant_people`, `get_daily_briefing`, `prepare_meeting_brief` |
| `Sites.Read.All`, `Notes.Read` | `get_onenote_notebooks`, `get_onenote_pages`, `get_onenote_page_content` |
| `Notes.ReadWrite` | `create_onenote_page` |
| `ThreatHunting.Read.All` | Reserved for future personal security insights tools |
| No additional scope (introspective) | `list_supported_tools`, `get_effective_scopes` |

## Run

```bash
uv run python main.py
```

Optional HTTP mode:

```bash
uv run python main.py --transport http --port 8001
```

## Testing

Run the full test suite:

```bash
make test
```

Run only smoke tests:

```bash
make test-smoke
```

Run only phase-1 mail tests:

```bash
make test-mail
```

Run only phase-2 calendar tests:

```bash
make test-calendar
```

Run only phase-3 files/sharing tests:

```bash
make test-files-phase3
```

Run only phase-4 Teams enhancement tests:

```bash
make test-teams-phase4
```

Run only phase-5 To Do lifecycle tests:

```bash
make test-todo-phase5
```

Run only phase-6 OneNote authoring tests:

```bash
make test-onenote-phase6
```

Run only phase-7/8 composite and operability tests:

```bash
make test-phase7-phase8
```

Run only To Do and files wrapper-validation tests:

```bash
make test-todo-files
```

Run only collaboration/context wrapper-validation tests:

```bash
make test-collab-context
```

Equivalent direct commands (without make):

```bash
uv run --with pytest pytest -q tests/test_smoke.py tests/test_mail_phase1.py
uv run --with pytest pytest -q tests/test_smoke.py
uv run --with pytest pytest -q tests/test_mail_phase1.py
uv run --with pytest pytest -q tests/test_calendar_phase2.py
uv run --with pytest pytest -q tests/test_files_phase3.py
uv run --with pytest pytest -q tests/test_teams_phase4.py
uv run --with pytest pytest -q tests/test_todo_phase5.py
uv run --with pytest pytest -q tests/test_onenote_phase6.py
uv run --with pytest pytest -q tests/test_phase7_phase8.py
uv run --with pytest pytest -q tests/test_validation_todo_files.py
uv run --with pytest pytest -q tests/test_validation_collab_context.py
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
