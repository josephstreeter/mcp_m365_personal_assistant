# M365 Productivity Assistant MCP - V2 Tooling Contract

## Goal

Define a practical, implementation-ready set of new MCP tools that extend the current server with high-value workflows while preserving the existing response style (JSON string payloads, defensive error handling, Graph-first design).

## Design Principles

- Keep tool names action-oriented and predictable.
- Preserve current response style: return serialized JSON with success/error payloads.
- Add minimally required scopes only when a capability is introduced.
- Prefer small composable tools over large opaque tools, then add a few composite assistant tools.
- Keep existing tools stable; introduce V2 tools as additive changes.

## Tool Contract Format

Each tool contract includes:

- Name
- Purpose
- Inputs
- Output schema
- Required Graph scopes
- Notes

---

## 1) Email Actions

### reply_to_message

Purpose: Reply to an existing message.

Inputs:

- message_id: string (required)
- body: string (required)
- content_type: string (optional, text|html, default text)
- reply_all: boolean (optional, default false)
- mailbox: string | null (optional shared mailbox)

Output schema:

- status: string (sent|error)
- message_id: string | null
- reply_all: boolean
- mailbox: string | null
- error: string | null

Required scopes:

- Mail.ReadWrite
- Mail.Send

Notes:

- Use /messages/{id}/reply or /replyAll.

### forward_message

Purpose: Forward an existing message to one or more recipients.

Inputs:

- message_id: string (required)
- to: string[] (required)
- comment: string | null (optional)
- mailbox: string | null (optional shared mailbox)

Output schema:

- status: string (sent|error)
- message_id: string
- to: string[]
- mailbox: string | null
- error: string | null

Required scopes:

- Mail.ReadWrite
- Mail.Send

### mark_message_read

Purpose: Set read state for a message.

Inputs:

- message_id: string (required)
- is_read: boolean (optional, default true)
- mailbox: string | null (optional shared mailbox)

Output schema:

- status: string (updated|error)
- message_id: string
- is_read: boolean
- mailbox: string | null
- error: string | null

Required scopes:

- Mail.ReadWrite

### move_message

Purpose: Move message to a target folder.

Inputs:

- message_id: string (required)
- destination_folder_id: string (required)
- mailbox: string | null (optional shared mailbox)

Output schema:

- status: string (moved|error)
- source_message_id: string
- destination_message_id: string | null
- destination_folder_id: string
- mailbox: string | null
- error: string | null

Required scopes:

- Mail.ReadWrite

### list_mail_folders

Purpose: List mail folders and IDs for move operations.

Inputs:

- mailbox: string | null (optional shared mailbox)
- top: number (optional, default 100)

Output schema:

- folders: array of
  - id: string
  - display_name: string
  - total_item_count: number | null
  - unread_item_count: number | null
- error: string | null

Required scopes:

- Mail.Read

### get_message_attachments

Purpose: List attachment metadata for a message.

Inputs:

- message_id: string (required)
- mailbox: string | null (optional shared mailbox)

Output schema:

- message_id: string
- attachments: array of
  - id: string
  - name: string
  - content_type: string | null
  - size: number | null
  - is_inline: boolean | null
- error: string | null

Required scopes:

- Mail.Read

---

## 2) Calendar Workflow

### update_calendar_event

Purpose: Update an existing event.

Inputs:

- event_id: string (required)
- subject: string | null
- start: string | null (ISO 8601)
- end: string | null (ISO 8601)
- attendees: string[] | null
- location: string | null
- body: string | null
- is_all_day: boolean | null

Output schema:

- status: string (updated|error)
- event_id: string
- error: string | null

Required scopes:

- Calendars.ReadWrite

### delete_calendar_event

Purpose: Delete an event.

Inputs:

- event_id: string (required)

Output schema:

- status: string (deleted|error)
- event_id: string
- error: string | null

Required scopes:

- Calendars.ReadWrite

### respond_to_event

Purpose: Accept/decline/tentative a meeting invitation.

Inputs:

- event_id: string (required)
- response: string (required, accept|decline|tentative)
- comment: string | null (optional)
- send_response: boolean (optional, default true)

Output schema:

- status: string (responded|error)
- event_id: string
- response: string
- send_response: boolean
- error: string | null

Required scopes:

- Calendars.ReadWrite

### find_meeting_times

Purpose: Retrieve suggested meeting times.

Inputs:

- attendees: string[] (required)
- duration_minutes: number (required)
- time_window_start: string (required, ISO 8601)
- time_window_end: string (required, ISO 8601)
- max_candidates: number (optional, default 10)

Output schema:

- suggestions: array of
  - confidence: number | null
  - start: string
  - end: string
  - attendee_availability: array
- empty_reason: string | null
- error: string | null

Required scopes:

- Calendars.Read

---

## 3) Microsoft To Do Lifecycle

### get_todo_lists

Purpose: List To Do lists.

Inputs:

- none

Output schema:

- lists: array of
  - id: string
  - display_name: string
  - is_shared: boolean | null
  - wellknown_list_name: string | null
- error: string | null

Required scopes:

- Tasks.Read

### update_todo_task

Purpose: Update task details by task ID.

Inputs:

- list_id: string (required)
- task_id: string (required)
- title: string | null
- due_date: string | null (ISO 8601)
- status: string | null (notStarted|inProgress|completed|waitingOnOthers|deferred)

Output schema:

- status: string (updated|error)
- list_id: string
- task_id: string
- error: string | null

Required scopes:

- Tasks.ReadWrite

### delete_todo_task

Purpose: Delete a task.

Inputs:

- list_id: string (required)
- task_id: string (required)

Output schema:

- status: string (deleted|error)
- list_id: string
- task_id: string
- error: string | null

Required scopes:

- Tasks.ReadWrite

### create_todo_list

Purpose: Create a new To Do list.

Inputs:

- display_name: string (required)

Output schema:

- status: string (created|error)
- list:
  - id: string
  - display_name: string
- error: string | null

Required scopes:

- Tasks.ReadWrite

---

## 4) Files and Sharing

### list_drive_items

Purpose: List folder contents from OneDrive.

Inputs:

- item_id: string | null (optional; null means root)
- top: number (optional, default 50)

Output schema:

- items: array of
  - id: string
  - name: string
  - is_folder: boolean
  - size: number | null
  - web_url: string | null
  - last_modified: string | null
- next_link: string | null
- error: string | null

Required scopes:

- Files.Read

### create_share_link

Purpose: Generate a sharing link for a file/folder.

Inputs:

- item_id: string (required)
- link_type: string (required, view|edit)
- scope: string (optional, organization|anonymous, default organization)

Output schema:

- status: string (created|error)
- item_id: string
- web_url: string | null
- link_type: string
- scope: string
- error: string | null

Required scopes:

- Files.ReadWrite

### upload_small_text_file

Purpose: Upload a small text file to a folder.

Inputs:

- parent_item_id: string | null (optional; null means root)
- file_name: string (required)
- content: string (required)
- content_type: string (optional, default text/plain)

Output schema:

- status: string (uploaded|error)
- item:
  - id: string
  - name: string
  - web_url: string | null
  - size: number | null
- error: string | null

Required scopes:

- Files.ReadWrite

---

## 5) Teams Enhancements

### get_chat_participants

Purpose: Retrieve participants of a specific chat.

Inputs:

- chat_id: string (required)

Output schema:

- chat_id: string
- participants: array of
  - id: string | null
  - display_name: string | null
  - email: string | null
  - roles: string[]
- error: string | null

Required scopes:

- Chat.Read

### send_channel_message

Purpose: Send message to a Teams channel.

Inputs:

- team_id: string (required)
- channel_id: string (required)
- message: string (required)
- content_type: string (optional, text|html, default text)

Output schema:

- status: string (sent|error)
- team_id: string
- channel_id: string
- message_id: string | null
- error: string | null

Required scopes:

- ChannelMessage.Send
- Group.Read.All

---

## 6) OneNote Authoring

### get_onenote_page_content

Purpose: Retrieve rendered content of a OneNote page.

Inputs:

- page_id: string (required)

Output schema:

- page_id: string
- title: string | null
- content_html: string | null
- error: string | null

Required scopes:

- Notes.Read

### create_onenote_page

Purpose: Create a page in a OneNote section.

Inputs:

- section_id: string (required)
- title: string (required)
- content_html: string (required)

Output schema:

- status: string (created|error)
- page:
  - id: string
  - title: string
  - web_url: string | null
- error: string | null

Required scopes:

- Notes.ReadWrite

---

## 7) Composite Assistant Tools

### get_daily_briefing

Purpose: Create a compact daily summary for agent workflows.

Inputs:

- date: string | null (optional, YYYY-MM-DD; default today)
- timezone: string | null (optional; default UTC)

Output schema:

- date: string
- calendar:
  - upcoming_events: array
- mail:
  - unread_count: number
  - priority_messages: array
- tasks:
  - due_today: array
  - overdue: array
- files:
  - recent: array
- people:
  - relevant_contacts: array
- error: string | null

Required scopes:

- User.Read
- Calendars.Read
- Mail.Read
- Tasks.Read
- Files.Read
- People.Read

Notes:

- Keep payload brief and deterministic; avoid large bodies.

### prepare_meeting_brief

Purpose: Build pre-meeting context bundle.

Inputs:

- event_id: string (required)
- include_recent_threads: boolean (optional, default true)

Output schema:

- event:
  - id: string
  - subject: string
  - start: string
  - end: string
  - attendees: array
- attendee_context: array
- related_messages: array
- related_files: array
- prep_notes: array
- error: string | null

Required scopes:

- Calendars.Read
- Mail.Read
- Files.Read
- People.Read

---

## 8) Operability and Diagnostics

### health_check

Purpose: Verify Graph connectivity and auth viability.

Inputs:

- none

Output schema:

- status: string (ok|degraded|error)
- graph_reachable: boolean
- auth_valid: boolean
- checked_at: string
- details: array

Required scopes:

- User.Read

### get_effective_scopes

Purpose: Report configured scopes and token-evidenced capabilities.

Inputs:

- none

Output schema:

- configured_scopes: string[]
- granted_scopes: string[] | null
- missing_recommended_scopes: string[]
- error: string | null

Required scopes:

- none (introspective)

### list_supported_tools

Purpose: Return MCP tool catalog with scope mapping.

Inputs:

- none

Output schema:

- tools: array of
  - name: string
  - description: string
  - required_scopes: string[]
  - version: string
- generated_at: string

Required scopes:

- none

---

## Backward Compatibility and Versioning

- Keep existing tool names unchanged.
- Introduce this set as additive V2 capabilities.
- Include a response field version for new tools, value: 2.
- Keep default top values conservative to avoid large payloads.

## Error Model

Use consistent error payloads:

- error: string
- error_type: string (AuthError|NotFound|ValidationError|GraphError|UnknownError)
- retryable: boolean

## Input Validation Rules

- Reject empty required strings.
- Validate ISO 8601 for date-time fields.
- Constrain list lengths for recipients/attendees.
- Constrain top and max_candidates to safe ranges.

## Suggested Implementation Sequence

1. Email actions: reply_to_message, mark_message_read, list_mail_folders, move_message, get_message_attachments.
2. Calendar actions: respond_to_event, update_calendar_event, find_meeting_times.
3. To Do lifecycle: get_todo_lists, update_todo_task, delete_todo_task, create_todo_list.
4. Files collaboration: list_drive_items, create_share_link, upload_small_text_file.
5. Composite assistant tools: get_daily_briefing, prepare_meeting_brief.
6. Operability tools: health_check, list_supported_tools, get_effective_scopes.

## Scope Delta from Current Server

Likely additional scopes beyond current set:

- Mail.ReadWrite
- Files.ReadWrite
- Notes.ReadWrite
- ChannelMessage.Send

Potentially optional later:

- Contacts.ReadWrite
- OnlineMeetings.ReadWrite

## Testing Additions

- Unit tests for input validation per tool.
- Unit tests for serialization shape consistency.
- Integration smoke tests gated by environment variables for Graph live calls.
- Regression tests for existing tools to ensure no behavior drift.

## Security Notes

- Do not return token material or sensitive headers.
- Avoid logging message bodies or full HTML in error logs.
- For anonymous share links, require explicit scope argument and reject implicit anonymous defaults.
- Keep principle of least privilege for all new scopes.
