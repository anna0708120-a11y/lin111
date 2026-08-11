#!/usr/bin/env python3
"""Read iPhone App.InFocus Biome records on macOS and upload low-confidence observations.

This is intentionally a passive source: the backend must not treat it as a live app fact
or use it to start a proactive notification.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FOCUS_ROOT = Path.home() / "Library/Biome/streams/restricted/App.InFocus/remote"
STATE_FILE = Path.home() / "Library/Application Support/Lin/biome_focus_bridge.json"
APP_ID_PATTERN = re.compile(r"(?:com|tv)\.[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)+")
SKIP_FRAGMENTS = (
    "springboard", "siri", "spotlight", "controlcenter", "backboard",
    "duet", "coreduet", "assistant", "preferences",
)
APP_NAMES = {
    "com.tencent.xin": "微信",
    "com.xingin.discover": "小红书",
    "com.atebits.Tweetie2": "推特/X",
    "com.ss.iphone.ugc.Aweme": "抖音",
}


def newest_focus_file(root: Path = FOCUS_ROOT) -> Path | None:
    """Return the newest regular record below the iCloud-synced remote stream."""
    if not root.is_dir():
        return None
    files = (path for path in root.rglob("*") if path.is_file())
    return max(files, key=lambda path: path.stat().st_mtime, default=None)


def extract_app_id(record: Path) -> str | None:
    """Extract the last meaningful bundle id from a binary Biome record."""
    try:
        text = record.read_bytes().decode("latin-1", "ignore")
    except OSError:
        return None
    for app_id in reversed(APP_ID_PATTERN.findall(text)):
        if not any(fragment in app_id.lower() for fragment in SKIP_FRAGMENTS):
            return app_id
    return None


def read_observation(root: Path = FOCUS_ROOT) -> dict[str, Any] | None:
    record = newest_focus_file(root)
    if record is None:
        return None
    app_id = extract_app_id(record)
    if app_id is None:
        return None
    observed_at = datetime.fromtimestamp(record.stat().st_mtime, timezone.utc)
    return {
        "app_name": APP_NAMES.get(app_id, app_id),
        "bundle_id": app_id,
        "observation_source": "biome_passive",
        "timestamp": observed_at.isoformat().replace("+00:00", "Z"),
    }


def load_last_signature(path: Path = STATE_FILE) -> str | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("signature")
    except (OSError, ValueError, AttributeError):
        return None


def save_last_signature(signature: str, path: Path = STATE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"signature": signature}), encoding="utf-8")


def signature(observation: dict[str, Any]) -> str:
    return "|".join(str(observation[key]) for key in ("bundle_id", "timestamp"))


def upload(server_url: str, token: str, observation: dict[str, Any], timeout: float = 10) -> None:
    payload = {key: value for key, value in observation.items() if key != "bundle_id"}
    request = Request(
        server_url.rstrip("/") + "/context/phone",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError(f"server returned HTTP {response.status}")


def run_once(server_url: str, token: str, *, root: Path = FOCUS_ROOT, state_file: Path = STATE_FILE) -> bool:
    observation = read_observation(root)
    if observation is None:
        return False
    current_signature = signature(observation)
    if current_signature == load_last_signature(state_file):
        return False
    upload(server_url, token, observation)
    save_last_signature(current_signature, state_file)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload passive iPhone Biome App.InFocus observations.")
    parser.add_argument("--server-url", default=os.getenv("LIN_SERVER_URL", ""))
    parser.add_argument("--token", default=os.getenv("CONTEXT_API_TOKEN", ""))
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.server_url or not args.token:
        raise SystemExit("Set LIN_SERVER_URL and CONTEXT_API_TOKEN locally, or pass --server-url and --token.")
    while True:
        try:
            if run_once(args.server_url, args.token):
                print("Uploaded passive iPhone app observation.")
        except (HTTPError, URLError, OSError, RuntimeError) as error:
            print(f"Biome bridge: {error}")
        if args.once:
            return 0
        time.sleep(max(10, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
