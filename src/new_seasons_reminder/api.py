"""Tautulli API functions for fetching metadata."""

import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin

from .http import HTTPClient

# Module-level logger
logger = logging.getLogger(__name__)

# Shared HTTP client instance
_http_client = HTTPClient()


def set_http_client(http_client: HTTPClient) -> None:
    global _http_client
    _http_client = http_client


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

    url = urljoin(tautulli_url.rstrip("/") + "/", "api/v2")

    try:
        logger.debug("Making request to Tautulli API: %s", cmd)
        data = _http_client.get_json(url, params=base_params)
        if isinstance(data, dict) and data.get("response", {}).get("result") == "success":
            return data.get("response", {}).get("data")
        if cmd == "get_recently_added" and isinstance(data, dict) and "recently_added" in data:
            return data
        # Handle empty dict response for get_recently_added - return empty list
        if data == {} and cmd == "get_recently_added":
            return []
        else:
            logger.error("Tautulli API error: %s", data)
            return None
    except HTTPError as e:
        logger.error("HTTP Error on cmd=%s params=%s: %s - %s", cmd, params, e.code, e.reason)
        return None
    except URLError as e:
        logger.error("URL Error on cmd=%s params=%s: %s", cmd, params, e.reason)
        return None
    except ValueError as e:
        logger.error("JSON Decode Error on cmd=%s: %s", cmd, e)
        return None
    except Exception as e:
        logger.error("Unexpected error on cmd=%s: %s", cmd, e)
        return None


def get_recently_added(
    media_type: str = "show",
    count: int = 100,
    tautulli_url: str = "",
    tautulli_apikey: str = "",
) -> list[dict[str, Any]]:
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
    logger.debug("get_recently_added raw data type=%s", type(data).__name__)
    if data:
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("recently_added", [])
        else:
            items = []
        logger.debug("get_recently_added extracted %s items", len(items))
        for item in items:
            logger.debug(
                "get_recently_added item rating_key=%s title=%s media_type=%s",
                item.get("rating_key"),
                item.get("title"),
                item.get("media_type"),
            )
        return items

    return []


def get_metadata(
    rating_key: str,
    tautulli_url: str = "",
    tautulli_apikey: str = "",
) -> dict[str, Any] | None:
    """Get metadata for a specific item.

    Args:
        rating_key: The rating key of the item.
        tautulli_url: URL to the Tautulli instance.
        tautulli_apikey: Tautulli API key.

    Returns:
        Metadata dictionary if successful, None otherwise.
    """
    params = {"rating_key": rating_key}
    logger.debug("get_metadata rating_key=%s", rating_key)
    result = make_tautulli_request(
        "get_metadata",
        params,
        tautulli_url=tautulli_url,
        tautulli_apikey=tautulli_apikey,
    )
    logger.debug("get_metadata found=%s", isinstance(result, dict))
    return result if isinstance(result, dict) else None


def get_libraries(
    tautulli_url: str = "",
    tautulli_apikey: str = "",
) -> list[dict[str, Any]]:
    data = make_tautulli_request(
        "get_libraries",
        tautulli_url=tautulli_url,
        tautulli_apikey=tautulli_apikey,
    )
    if isinstance(data, list):
        return data
    return []


def get_children_metadata(
    rating_key: str,
    tautulli_url: str = "",
    tautulli_apikey: str = "",
    media_type: str = "season",
) -> list[dict[str, Any]]:
    """Get children (episodes/seasons) of an item.

    Args:
        rating_key: The rating key of the parent item.
        tautulli_url: URL to the Tautulli instance.
        tautulli_apikey: Tautulli API key.

    Returns:
        List of child items with rating keys.
    """
    params = {"rating_key": rating_key}
    params["media_type"] = media_type
    data = make_tautulli_request(
        "get_children_metadata",
        params,
        tautulli_url=tautulli_url,
        tautulli_apikey=tautulli_apikey,
    )
    logger.debug("get_children_metadata rating_key=%s", rating_key)
    logger.debug("get_children_metadata raw data type=%s", type(data).__name__)
    if data:
        if isinstance(data, list):
            children = data
        elif isinstance(data, dict):
            children = data.get("children_list", [])
        else:
            children = []
        filtered_children = [child for child in children if child.get("rating_key")]
        logger.debug("get_children_metadata extracted %s children", len(filtered_children))
        return filtered_children

    return []
