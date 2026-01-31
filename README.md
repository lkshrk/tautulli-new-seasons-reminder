# Tautulli New Seasons Reminder

[![Tests](https://github.com/lkshrk/tautulli-new-seasons-reminder/actions/workflows/test.yml/badge.svg)](https://github.com/lkshrk/tautulli-new-seasons-reminder/actions/workflows/test.yml)
[![Release](https://github.com/lkshrk/tautulli-new-seasons-reminder/actions/workflows/release.yml/badge.svg)](https://github.com/lkshrk/tautulli-new-seasons-reminder/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A custom script for Tautulli that sends weekly webhook notifications for all newly finished TV show seasons from the past week. It specifically **ignores brand new shows** and only notifies about existing shows that have received a new completed season.

## Features

- 🔔 Sends weekly webhook notifications
- 📺 Tracks only **new seasons of existing shows** (not new series)
- ✅ Only includes **finished seasons** (all episodes available)
- 🗓️ Configurable lookback period (default: 7 days)
- 🔍 Smart detection of new shows vs. new seasons
- 🐳 **Docker support** - Run anywhere with a single command

## Quick Start (Docker)

### Run with Docker

```bash
# Pull and run the latest image
docker run -e TAUTULLI_URL=http://tautulli:8181 \
           -e TAUTULLI_APIKEY=your-api-key \
           -e WEBHOOK_URL=your-webhook-url \
           ghcr.io/lkshrk/tautulli-new-seasons-reminder:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  new-seasons-reminder:
    image: ghcr.io/lkshrk/tautulli-new-seasons-reminder:latest
    environment:
      - TAUTULLI_URL=http://tautulli:8181
      - TAUTULLI_APIKEY=your-api-key
      - WEBHOOK_URL=your-webhook-url
      - WEBHOOK_MODE=signal-cli
      - SIGNAL_NUMBER=+1234567890
      - SIGNAL_RECIPIENTS=+0987654321
      - LOOKBACK_DAYS=7
    restart: unless-stopped
```

## Configuration

Configure via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `WEBHOOK_URL` | URL to send notifications to | Required |
| `TAUTULLI_URL` | Tautulli instance URL | Required |
| `TAUTULLI_APIKEY` | Tautulli API key | Required |
| `PLEX_URL` | Plex server URL (for cover images) | Optional |
| `PLEX_TOKEN` | Plex token (for cover images) | Optional |
| `LOOKBACK_DAYS` | Days to look back for new seasons | 7 |
| `DEBUG` | Enable verbose logging | false |
| `WEBHOOK_MODE` | Webhook mode: `default`, `signal-cli`, or `custom` | `default` |
| `SIGNAL_NUMBER` | Signal sender phone number (for signal-cli mode) | Required for signal-cli |
| `SIGNAL_RECIPIENTS` | Comma-separated recipient phone numbers | Required for signal-cli |
| `SIGNAL_TEXT_MODE` | Signal text mode: `styled`, `normal`, or `extended` | `styled` |
| `SIGNAL_INCLUDE_COVERS` | Attach show covers as base64 | `false` |
| `WEBHOOK_ON_EMPTY` | Send webhook even with no new seasons | `false` |

## Webhook Payload Format

By default, the script sends this JSON payload:

```json
{
  "timestamp": "2026-01-30T12:00:00",
  "period_days": 7,
  "season_count": 3,
  "seasons": [
    {
      "show": "Breaking Bad",
      "season": 3,
      "season_title": "Season 3",
      "added_at": "2026-01-28T10:30:00",
      "episode_count": 13,
      "rating_key": "12345",
      "cover_url": "http://plex-server:32400/library/metadata/12345/thumb/..."
    }
  ],
  "message": "📺 3 new season(s) completed this week!"
}
```

## How It Works

1. The script queries Tautulli's API for recently added seasons
2. It filters for items added within the last 7 days
3. It checks if the show is "new" (only Season 1) or an existing show
4. It verifies that all episodes of the season are available
5. It sends the compiled list to your webhook

## License

MIT License
