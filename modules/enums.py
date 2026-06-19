"""Shared enum values for MCP tool inputs and helper logic."""

from __future__ import annotations

from enum import StrEnum


class ContentType(StrEnum):
    TEXT = "text"
    HTML = "html"


class TodoStatus(StrEnum):
    NOT_STARTED = "notStarted"
    IN_PROGRESS = "inProgress"
    COMPLETED = "completed"
    WAITING_ON_OTHERS = "waitingOnOthers"
    DEFERRED = "deferred"


class EventResponse(StrEnum):
    ACCEPT = "accept"
    DECLINE = "decline"
    TENTATIVE = "tentative"


class ShareLinkType(StrEnum):
    VIEW = "view"
    EDIT = "edit"


class ShareLinkScope(StrEnum):
    ORGANIZATION = "organization"
    ANONYMOUS = "anonymous"


CONTENT_TYPE_VALUES: tuple[str, ...] = tuple(item.value for item in ContentType)
TODO_STATUS_VALUES: tuple[str, ...] = tuple(item.value for item in TodoStatus)
EVENT_RESPONSE_VALUES: tuple[str, ...] = tuple(item.value for item in EventResponse)
SHARE_LINK_TYPE_VALUES: tuple[str, ...] = tuple(item.value for item in ShareLinkType)
SHARE_LINK_SCOPE_VALUES: tuple[str, ...] = tuple(item.value for item in ShareLinkScope)
