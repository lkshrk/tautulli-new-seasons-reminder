"""Media sources package."""

from __future__ import annotations

from new_seasons_reminder.sources.base import MediaSource
from new_seasons_reminder.sources.jellyfin import JellyfinMediaSource
from new_seasons_reminder.sources.tautulli import TautulliMediaSource

__all__ = ["MediaSource", "TautulliMediaSource", "JellyfinMediaSource"]
