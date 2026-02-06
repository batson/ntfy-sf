# SF Dispatch Monitor

Monitors the [DataSF Law Enforcement Dispatched Calls for Service (Real-Time)](https://data.sfgov.org/Public-Safety/Law-Enforcement-Dispatched-Calls-for-Service-Real-/gnap-fj3t) dataset and sends push notifications via [ntfy.sh](https://ntfy.sh) when new calls appear.

## How it works

- Polls the DataSF SODA API every 5 minutes for new dispatch calls
- Filters to HSOC (High School Outreach) flagged calls plus specific call types: SIT/LIE ENFORCEMENT, HOMELESS COMPLAINT, MEET W/CITY EMPLOYEE
- Tracks seen call IDs in a local state file to detect new entries
- Each new matching call triggers an individual notification
- Notifications go to ntfy.sh topic `sf-dispatch-alerts-3190`

## Files

- `monitor.py` — main script (long-running polling loop)
- `fly.toml` — Fly.io deployment config (sjc region, persistent volume for state)
- `Dockerfile` — Python 3.12-slim container
- `requirements.txt` — just `requests`

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `NTFY_TOPIC` | `sf-dispatch-alerts-3190` | ntfy.sh topic name |
| `CHECK_INTERVAL` | `300` | Polling interval in seconds |
| `STATE_DIR` | script directory | Where to store `.last_state.json` |

## Deploy to Fly.io

This app runs as a **scheduled job** (every 5 minutes) using Fly.io + GitHub Actions (both free tier).

See [DEPLOY.md](DEPLOY.md) for complete deployment instructions.

**Quick start:**
```bash
fly auth login
fly apps create sf-dispatch-monitor
fly volumes create state_data --region sjc --size 1 --app sf-dispatch-monitor
fly secrets set NTFY_TOPIC="sf-dispatch-alerts-3190" --app sf-dispatch-monitor
fly deploy --ha=false
```

Then set up GitHub Actions (see [DEPLOY.md](DEPLOY.md)).

## Run locally

```bash
pip install -r requirements.txt
python monitor.py
```

## Receive notifications

Install the ntfy app (iOS/Android) and subscribe to topic `sf-dispatch-alerts-3190`.
