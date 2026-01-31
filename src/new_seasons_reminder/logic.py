import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _safe_get_nested(d: dict, *keys: str, default: Any = None) -> Any:
    current: Any = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def is_new_show(
    grandparent_rating_key: str,
    cutoff_date: datetime,
    get_metadata_func: Callable[[str], dict | None],
) -> bool:
    show_metadata = get_metadata_func(grandparent_rating_key)
    if not show_metadata:
        logger.warning(f"Could not get metadata for show {grandparent_rating_key}")
        return False

    show_added_at = show_metadata.get("added_at")
    if not show_added_at:
        return False

    try:
        show_date = datetime.fromtimestamp(int(show_added_at))
        if show_date >= cutoff_date:
            logger.debug(f"Show added at {show_date} - this is a NEW SHOW")
            return True
    except (ValueError, TypeError) as e:
        logger.warning(f"Error parsing added_at for show: {e}")

    return False


def is_season_finished(
    season_rating_key: str,
    get_children_func: Callable[[str], list[dict]],
) -> bool:
    episodes = get_children_func(season_rating_key)
    if not episodes:
        return False

    total_episodes = len(episodes)
    available_episodes = 0
    for ep in episodes:
        if ep.get("media_type") != "episode":
            continue
        file_path = _safe_get_nested(ep, "media_info", "parts", "file", default="")
        if file_path and not str(file_path).endswith(".strm"):
            available_episodes += 1

    logger.debug(f"Season has {available_episodes}/{total_episodes} episodes available")
    return available_episodes > 0


def get_new_finished_seasons(
    lookback_days: int,
    get_recently_added_func: Callable[[str, int], list[dict]],
    is_new_show_func: Callable[[str, datetime], bool],
    is_season_finished_func: Callable[[str], bool],
    get_show_cover_func: Callable[[str], str | None],
    get_children_func: Callable[[str], list[dict]],
) -> list[dict[str, Any]]:
    cutoff_date = datetime.now() - timedelta(days=lookback_days)
    logger.info(f"Looking for seasons added since {cutoff_date}")

    recently_added = get_recently_added_func("season", 100)
    if not recently_added:
        logger.info("No recently added items found")
        return []

    new_seasons = []

    for item in recently_added:
        media_type = item.get("media_type")
        if media_type != "season":
            continue

        rating_key = item.get("rating_key")
        title = item.get("title", "Unknown")
        parent_title = item.get("parent_title", "Unknown")
        grandparent_rating_key = item.get("grandparent_rating_key")
        season_index = item.get("parent_index", 0)
        added_at_timestamp = item.get("added_at")

        if not added_at_timestamp:
            logger.debug(f"Skipping {title} - no added_at timestamp")
            continue

        try:
            added_at = datetime.fromtimestamp(int(added_at_timestamp))
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing added_at for {title}: {e}")
            continue

        if added_at < cutoff_date:
            logger.debug(f"Skipping {title} - added at {added_at} (before cutoff)")
            continue

        logger.info(f"Processing: {parent_title} - Season {season_index} (added {added_at})")

        if not grandparent_rating_key:
            logger.debug(f"Skipping {title} - no grandparent_rating_key")
            continue

        if is_new_show_func(str(grandparent_rating_key), cutoff_date):
            logger.info(f"Skipping {parent_title} - this is a NEW SHOW, not a new season")
            continue

        if not rating_key:
            logger.debug(f"Skipping {title} - no rating_key")
            continue

        if not is_season_finished_func(str(rating_key)):
            logger.info(f"Skipping {parent_title} Season {season_index} - season not finished")
            continue

        episodes = get_children_func(str(rating_key))
        episode_count = len([ep for ep in episodes if ep.get("media_type") == "episode"])

        cover_url = get_show_cover_func(str(grandparent_rating_key))

        new_seasons.append(
            {
                "show": parent_title,
                "season": season_index,
                "season_title": title,
                "added_at": added_at.isoformat(),
                "episode_count": episode_count,
                "rating_key": rating_key,
                "cover_url": cover_url,
            }
        )

    return new_seasons
