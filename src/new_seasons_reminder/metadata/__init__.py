"""Metadata providers package."""

from __future__ import annotations

from new_seasons_reminder.metadata.base import ExternalMetadataProvider
from new_seasons_reminder.metadata.resolver import MetadataResolver
from new_seasons_reminder.metadata.tmdb import TMDBMetadataProvider
from new_seasons_reminder.metadata.tvdb import TVDBMetadataProvider

__all__ = [
    "ExternalMetadataProvider",
    "MetadataResolver",
    "TMDBMetadataProvider",
    "TVDBMetadataProvider",
]
