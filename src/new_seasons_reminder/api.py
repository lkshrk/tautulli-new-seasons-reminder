"""Tautulli API functions for fetching metadata and cover images."""

import base64
import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import urlopen

# Module-level logger
logger = logging.getLogger(__name__)


def make_tautulli_request(
    cmd: str,
    params: dict[str, Any] | None = None,
    tautulli_url: str = "",
    tautulli_apikey: str = "",
) -> Any:
    """Make a request to the Tautulli API.

    Args:
        cmd: The Tautulli API command to execute.
        params: Additional parameters for the API request.
        tautulli_url: URL to the Tautulli instance.
        tautulli_apikey: Tautulli API key.

    Returns:
        The API response data if successful, None otherwise.
    """
    if not tautulli_url or not tautulli_apikey:
        logger.error("tautulli_url or tautulli_apikey not set")
        return None

    base_params = {
        "apikey": tautulli_apikey,
        "cmd": cmd,
    }
    if params:
        base_params.update(params)

    url = urljoin(tautulli_url.rstrip("/") + "/", "api/v2") + "?" + urlencode(base_params)

    try:
        logger.debug(f"Making request to Tautulli API: {cmd}")
        with urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("response", {}).get("result") == "success":
                return data.get("response", {}).get("data")
            else:
                logger.error(f"Tautulli API error: {data}")
                return None
    except HTTPError as e:
        logger.error(f"HTTP Error: {e.code} - {e.reason}")
        return None
    except URLError as e:
        logger.error(f"URL Error: {e.reason}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None


def get_recently_added(
    media_type: str = "show",
    count: int = 100,
    tautulli_url: str = "",
    tautulli_apikey: str = "",
) -> list[dict]:
    """Get recently added items from Tautulli.

    Args:
        media_type: Type of media to fetch (show, season, episode, movie).
        count: Maximum number of items to return.
        tautulli_url: URL to the Tautulli instance.
        tautulli_apikey: Tautulli API key.

    Returns:
        List of recently added media items.
    """
    params = {
        "media_type": media_type,
        "count": count,
    }
    data = make_tautulli_request(
        "get_recently_added",
        params,
        tautulli_url=tautulli_url,
        tautulli_apikey=tautulli_apikey,
    )
    if data:
        return data if isinstance(data, list) else []
    return []


def get_metadata(
    rating_key: str,
    tautulli_url: str = "",
    tautulli_apikey: str = "",
) -> dict | None:
    """Get metadata for a specific item.

    Args:
        rating_key: The rating key of the item.
        tautulli_url: URL to the Tautulli instance.
        tautulli_apikey: Tautulli API key.

    Returns:
        Metadata dictionary if successful, None otherwise.
    """
    params = {"rating_key": rating_key}
    result = make_tautulli_request(
        "get_metadata",
        params,
        tautulli_url=tautulli_url,
        tautulli_apikey=tautulli_apikey,
    )
    return result if isinstance(result, dict) else None


def get_children_metadata(
    rating_key: str,
    tautulli_url: str = "",
    tautulli_apikey: str = "",
) -> list[dict]:
    """Get children (episodes/seasons) of an item.

    Args:
        rating_key: The rating key of the parent item.
        tautulli_url: URL to the Tautulli instance.
        tautulli_apikey: Tautulli API key.

    Returns:
        List of child items with rating keys.
    """
    params = {"rating_key": rating_key}
    data = make_tautulli_request(
        "get_children_metadata",
        params,
        tautulli_url=tautulli_url,
        tautulli_apikey=tautulli_apikey,
    )
    if data:
        children: list[dict] = data if isinstance(data, list) else []
        return [child for child in children if child.get("rating_key")]
    return []


def get_cover_url(
    thumb_path: str,
    plex_url: str = "",
    plex_token: str = "",
) -> str | None:
    """Build full cover URL from thumb path using Plex URL and token.

    Args:
        thumb_path: The thumb path from metadata.
        plex_url: URL to the Plex server.
        plex_token: Plex authentication token.

    Returns:
        Full cover URL with authentication token, or None if not available.
    """
    if not thumb_path:
        return None

    if not plex_url or not plex_token:
        logger.debug("plex_url or plex_token not set, cannot build cover URL")
        return None

    full_url = urljoin(plex_url.rstrip("/") + "/", thumb_path.lstrip("/"))
    separator = "&" if "?" in full_url else "?"
    return f"{full_url}{separator}X-Plex-Token={plex_token}"


def get_show_cover(
    rating_key: str,
    plex_url: str = "",
    plex_token: str = "",
    tautulli_url: str = "",
    tautulli_apikey: str = "",
) -> str | None:
    """Get cover URL for a show.

    Args:
        rating_key: The rating key of the show.
        plex_url: URL to the Plex server.
        plex_token: Plex authentication token.
        tautulli_url: URL to the Tautulli instance.
        tautulli_apikey: Tautulli API key.

    Returns:
        Cover URL if available, None otherwise.
    """
    metadata = get_metadata(
        rating_key,
        tautulli_url=tautulli_url,
        tautulli_apikey=tautulli_apikey,
    )
    if not metadata:
        return None

    thumb = metadata.get("thumb") or metadata.get("art") or metadata.get("poster_thumb")
    if thumb:
        return get_cover_url(thumb, plex_url=plex_url, plex_token=plex_token)
    return None


def download_cover_as_base64(cover_url: str) -> str | None:
    """Download cover image and return as base64 encoded string.

    Args:
        cover_url: URL to the cover image.

    Returns:
        Base64 encoded image data, or None if download fails.
    """
    if not cover_url:
        return None

    try:
        with urlopen(cover_url, timeout=30) as response:
            image_data = response.read()
            return base64.b64encode(image_data).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to download cover: {e}")
        return None
