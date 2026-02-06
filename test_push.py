#!/usr/bin/env python3
"""
Send a test push notification to verify formatting
"""

import os
import requests
from datetime import datetime

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "sf-dispatch-alerts-3190")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

# Sample HSOC call data
test_call = {
    "received_datetime": "2026-02-04T16:58:12.000",
    "call_type_original_desc": "SIT/LIE ENFORCEMENT",
    "intersection_name": "CASTRO ST \\ STATES ST",
    "analysis_neighborhood": "Castro/Upper Market",
    "agency": "Police",
    "sensitive_call": False,
    "priority_final": "C",
}

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
    print(f"✓ Test notification sent successfully!")
    print(f"  Title: {title}")
    print(f"  Message:\n{message}")

if __name__ == "__main__":
    call_type = test_call["call_type_original_desc"]

    send_notification(
        title=f"SF Dispatch - {call_type}",
        message=format_call(test_call),
    )
