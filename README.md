# New Seasons Reminder

[![CI](https://github.com/lkshrk/tautulli-new-seasons-reminder/actions/workflows/test.yml/badge.svg)](https://github.com/lkshrk/tautulli-new-seasons-reminder/actions/workflows/test.yml)
[![Release](https://github.com/lkshrk/tautulli-new-seasons-reminder/actions/workflows/release.yml/badge.svg)](https://github.com/lkshrk/tautulli-new-seasons-reminder/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Sends webhook notifications when TV show seasons are completed in your media library. Supports **Tautulli** and **Jellyfin** as media sources, with optional episode-count validation via **TMDB** or **TVDB**.

## Quick Start

**Tautulli:**
```bash
docker run \
  -e SOURCE_TYPE=tautulli \
  -e TAUTULLI_URL=http://tautulli:8181 \
  -e TAUTULLI_APIKEY=your-api-key \
  -e WEBHOOK_URL=http://your-webhook-url \
  ghcr.io/lkshrk/tautulli-new-seasons-reminder:latest
```

**Jellyfin:**
```bash
docker run \
  -e SOURCE_TYPE=jellyfin \
  -e JELLYFIN_URL=http://jellyfin:8096 \
  -e JELLYFIN_APIKEY=your-api-key \
  -e JELLYFIN_USER_ID=your-user-id \
  -e WEBHOOK_URL=http://your-webhook-url \
  ghcr.io/lkshrk/tautulli-new-seasons-reminder:latest
```

### Docker Compose

```yaml
services:
  new-seasons-reminder:
    image: ghcr.io/lkshrk/tautulli-new-seasons-reminder:latest
    environment:
      - SOURCE_TYPE=tautulli
      - TAUTULLI_URL=http://tautulli:8181
      - TAUTULLI_APIKEY=your-api-key
      - WEBHOOK_URL=http://your-webhook-url
      - LOOKBACK_DAYS=7
      # Optional: validate episode counts against TMDB
      - METADATA_PROVIDERS=tmdb
      - TMDB_APIKEY=your-tmdb-key
    restart: unless-stopped
```

## Configuration

All configuration is via environment variables.

### Media Source

| Variable | Description | Default |
|----------|-------------|---------|
| `SOURCE_TYPE` | `tautulli` or `jellyfin` | `tautulli` |

**Tautulli** (when `SOURCE_TYPE=tautulli`):

| Variable | Description |
|----------|-------------|
| `TAUTULLI_URL` | Tautulli instance URL |
| `TAUTULLI_APIKEY` | Tautulli API key |

**Jellyfin** (when `SOURCE_TYPE=jellyfin`):

| Variable | Description |
|----------|-------------|
| `JELLYFIN_URL` | Jellyfin instance URL |
| `JELLYFIN_APIKEY` | Jellyfin API key |
| `JELLYFIN_USER_ID` | Jellyfin user ID |

### Metadata Providers (Optional)

Metadata providers validate that a season's episode count matches the expected total before notifying.

| Variable | Description | Default |
|----------|-------------|---------|
| `METADATA_PROVIDERS` | Comma-separated list: `tmdb`, `tvdb` | _(none)_ |
| `TMDB_APIKEY` | TMDB API key (required if `tmdb` in providers) | — |
| `TVDB_APIKEY` | TVDB API key (required if `tvdb` in providers) | — |

> **Note:** TVDB v4 requires a paid subscription for full episode data. If TVDB is listed as a fallback after TMDB and TMDB resolves successfully, TVDB is never queried.

### Webhook

| Variable | Description | Default |
|----------|-------------|---------|
| `WEBHOOK_URL` | URL to POST notifications to | Required |
| `WEBHOOK_MODE` | `default`, `signal-cli`, or `custom` | `default` |
| `WEBHOOK_ON_EMPTY` | Send webhook even when no seasons found | `false` |
| `WEBHOOK_MESSAGE_TEMPLATE` | Message template (supports `{season_count}`) | `📺 {season_count} new season(s) completed this week!` |
| `WEBHOOK_PAYLOAD_TEMPLATE` | Custom JSON payload template | `default` |

### Application

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOKBACK_DAYS` | Days to look back for completed seasons (1–365) | `7` |
| `INCLUDE_NEW_SHOWS` | Include shows first added within the lookback window | `false` |
| `REQUIRE_FULLY_AIRED` | Only notify if all episodes have aired (requires TMDB) | `false` |
| `DISABLE_SSL_VERIFY` | Disable TLS certificate verification for HTTP calls | `false` |
| `DEBUG` | Verbose logging | `false` |

### Signal CLI Mode

Set `WEBHOOK_MODE=signal-cli` and configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `SIGNAL_NUMBER` | Signal sender phone number | Required |
| `SIGNAL_RECIPIENTS` | Comma-separated recipient phone numbers | Required |
| `SIGNAL_TEXT_MODE` | `styled`, `normal`, or `extended` | `styled` |

## Webhook Payload

Default JSON payload:

```json
{
  "timestamp": "2026-01-30T12:00:00",
  "period_days": 7,
  "season_count": 1,
  "seasons": [
    {
      "show": "Breaking Bad",
      "season": 3,
      "season_title": "Season 3",
      "added_at": "2026-01-28T10:30:00",
      "episode_count": 13,
      "rating_key": "12345",
      "reason": "Complete: 13/13 episodes in library",
      "expected_count": 13
    }
  ],
  "message": "📺 1 new season(s) completed this week!"
}
```

### Custom Payload Template

Set `WEBHOOK_PAYLOAD_TEMPLATE` to a JSON string with these placeholders:

| Variable | Description |
|----------|-------------|
| `{timestamp}` | ISO 8601 timestamp |
| `{period_days}` | Lookback period in days |
| `{season_count}` | Number of seasons found |
| `{message}` | Formatted message string |
| `{show_list}` | Comma-separated list (e.g. `Breaking Bad S3, Lost S2`) |
| `{seasons}` | Full seasons array as JSON |

## How It Works

1. Queries the media source (Tautulli or Jellyfin) for seasons added within `LOOKBACK_DAYS`
2. Optionally validates episode counts against TMDB/TVDB metadata
3. Optionally checks that all episodes have aired (`REQUIRE_FULLY_AIRED`)
4. Skips shows first added within the lookback window (configurable via `INCLUDE_NEW_SHOWS`)
5. Sends results to the configured webhook

## License

MIT
