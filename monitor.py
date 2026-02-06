#!/usr/bin/env python3
"""
Monitor SF Law Enforcement Dispatched Calls for Service (Real-Time)
and send push notifications via ntfy.sh when new calls appear.
"""

import json
import os
import requests
import time
from pathlib import Path
from datetime import datetime, timezone

# --- Configuration ---
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "sf-dispatch-alerts-3190")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL", "300"))
STATE_DIR = Path(os.environ.get("STATE_DIR", str(Path(__file__).parent)))
STATE_FILE = STATE_DIR / ".last_state.json"

DATASET_ID = "gnap-fj3t"
BASE_URL = f"https://data.sfgov.org/resource/{DATASET_ID}.json"
METADATA_URL = f"https://data.sfgov.org/api/views/{DATASET_ID}.json"


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"seen_ids": [], "rows_updated_at": None}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state))


def get_rows_updated_at():
    resp = requests.get(METADATA_URL, timeout=30)
    resp.raise_for_status()
    return resp.json().get("rowsUpdatedAt")


def fetch_recent_calls(limit=200):
    params = {
        "$order": "received_datetime DESC",
        "$limit": limit,
        "$where": "onview_flag = 'HSOC' OR call_type_original_desc IN ('SIT/LIE ENFORCEMENT', 'HOMELESS COMPLAINT', 'MEET W/CITY EMPLOYEE')",
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def format_call(call):
    # Format datetime as "2/5/2026 8:51 PM"
    received = call.get("received_datetime", "")
    if received:
        try:
            dt = datetime.fromisoformat(received.replace("Z", "+00:00"))
            received_formatted = dt.strftime("%-m/%-d/%Y %-I:%M %p")
        except:
            received_formatted = received
    else:
        received_formatted = "Unknown time"

    call_type = call.get("call_type_original_desc") or "Unknown"
    intersection = call.get("intersection_name") or "Unknown location"
    neighborhood = call.get("analysis_neighborhood") or ""
    agency = call.get("agency") or "Unknown agency"
    sensitive = call.get("sensitive_call", False)

    if sensitive:
        intersection = "[Sensitive - location suppressed]"

    lines = [
        f"Time: {received_formatted}",
        f"Type: {call_type}",
        f"Location: {intersection}",
    ]
    if neighborhood and not sensitive:
        lines.append(f"Neighborhood: {neighborhood}")
    lines.append(f"Agency: {agency}")

    return "\n".join(lines)


def send_notification(title, message):
    resp = requests.post(
        NTFY_URL,
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": "default",
            "Tags": "rotating_light",
        },
        timeout=15,
    )
    resp.raise_for_status()
    print(f"  Notification sent: {title}")


def send_notification_with_backoff(title, message, max_retries=5):
    """Send notification with exponential backoff on rate limit errors."""
    backoff = 2  # Start with 2 second backoff
    max_backoff = 64  # Cap at 64 seconds

    for attempt in range(max_retries):
        try:
            send_notification(title, message)
            return True
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                if attempt < max_retries - 1:
                    print(f"  Rate limit hit, retrying in {backoff}s...")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
                else:
                    print(f"  Rate limit hit, max retries reached")
                    return False
            else:
                print(f"  Failed to send notification: {e}")
                return False
        except Exception as e:
            print(f"  Failed to send notification: {e}")
            return False

    return False


def check_and_notify():
    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    last_updated = state.get("rows_updated_at")

    # Check if dataset has been updated
    current_updated = get_rows_updated_at()
    if current_updated == last_updated and seen_ids:
        print(f"[{datetime.now(timezone.utc).isoformat()}] No update detected, skipping.")
        return

    print(f"[{datetime.now(timezone.utc).isoformat()}] Update detected, fetching calls...")

    calls = fetch_recent_calls()
    current_ids = {c.get("id") or c.get("cad_number") for c in calls}

    # Find new calls
    if not seen_ids:
        # First run — don't notify for everything, just record state
        print(f"  First run: recording {len(current_ids)} existing calls.")
        new_calls = []
    else:
        new_calls = [c for c in calls if (c.get("id") or c.get("cad_number")) not in seen_ids]

    if new_calls:
        print(f"  Found {len(new_calls)} new HSOC calls.")

        # Send individual notification for each HSOC call
        sent_call_ids = []
        for i, call in enumerate(new_calls):
            call_type = call.get("call_type_original_desc") or "Unknown"
            success = send_notification_with_backoff(
                title=f"SF Dispatch - {call_type}",
                message=format_call(call),
            )

            if success:
                # Track successfully sent call
                call_id = call.get("id") or call.get("cad_number")
                if call_id:
                    sent_call_ids.append(call_id)
                # Add delay between notifications to avoid rate limits
                if i < len(new_calls) - 1:
                    time.sleep(1)
            else:
                # Rate limited after backoff - stop sending, will retry next run
                print(f"  Stopped after {i + 1}/{len(new_calls)} notifications")
                break
    else:
        sent_call_ids = []
        if seen_ids:
            print("  No new calls in this update.")

    # Update state - only mark successfully sent calls as seen
    updated_seen_ids = list(seen_ids) + sent_call_ids
    state = {
        "seen_ids": updated_seen_ids,
        "rows_updated_at": current_updated,
    }
    save_state(state)


def main():
    print(f"SF Dispatch Monitor - single run")
    print(f"Notifications → {NTFY_URL}")
    print()

    try:
        check_and_notify()
    except Exception as e:
        print(f"[{datetime.now(timezone.utc).isoformat()}] Error: {e}")
        exit(1)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Run complete.")
    exit(0)


if __name__ == "__main__":
    main()
