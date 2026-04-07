#!/usr/bin/env python3
"""XKV8 Miner Dashboard Server — open source edition.

Reads config.json for miner setup, tracks wins/losses from journalctl,
queries on-chain balance, and serves the dashboard UI.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
STATE_FILE = SCRIPT_DIR / ".dashboard_state.json"
STATIC_DIR = SCRIPT_DIR / "static"

# ── Config ──────────────────────────────────────────────────────────────

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

CFG = load_config()

# ── Shared State ────────────────────────────────────────────────────────

_lock = threading.Lock()
_state = {
    "bundlesSubmitted": 0,
    "wins": 0,
    "losses": 0,
    "lastHeight": 0,
    "lastActivity": None,
    "miningAddress": CFG.get("target_address", ""),
    "isGrinding": False,
    "status": "OFFLINE",
    "serviceStartTime": None,
}

_balance_cache = {"value": 0.0, "ts": 0}

def save_state():
    with _lock:
        snapshot = dict(_state)
    try:
        STATE_FILE.write_text(json.dumps(snapshot, default=str))
    except Exception:
        pass

def load_state():
    global _state
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            with _lock:
                for k in ("bundlesSubmitted", "wins", "losses", "lastHeight",
                           "miningAddress", "serviceStartTime"):
                    if k in data:
                        _state[k] = data[k]
            print(f"Loaded state: {_state['bundlesSubmitted']} bundles, {_state['wins']} wins")
        except Exception as e:
            print(f"Could not load state: {e}")

# ── Log Parsing ─────────────────────────────────────────────────────────

RE_SUBMITTED = re.compile(r"Submitted mining spend bundle for height (\d+)")
RE_LOSS = re.compile(r"mined by another miner at height (\d+)")
RE_WIN = re.compile(r"Win CONFIRMED at height (\d+)")
RE_HEIGHT = re.compile(r"Height: (\d+)")
RE_ADDRESS = re.compile(r"Mining to address: (xch\w+)")
RE_STARTED = re.compile(r"Starting miner")
RE_REWARD = re.compile(r"Reward of ([\d.]+) XKV8")

def parse_log_line(line):
    msg_match = re.search(r"xkv8\[\d+\]: (.+)$", line)
    if not msg_match:
        # Handle -o cat format (no syslog prefix)
        msg = line.strip()
    else:
        msg = msg_match.group(1)

    with _lock:
        if RE_WIN.search(msg):
            _state["wins"] += 1
            _state["lastActivity"] = msg.strip()
            return
        if RE_REWARD.search(msg):
            _state["lastActivity"] = msg.strip()
            return
        sub_m = RE_SUBMITTED.search(msg)
        if sub_m:
            _state["bundlesSubmitted"] += 1
            _state["lastHeight"] = int(sub_m.group(1))
            _state["isGrinding"] = True
            _state["status"] = "MINING"
            _state["lastActivity"] = msg.strip()
            return
        if RE_LOSS.search(msg):
            _state["losses"] += 1
            _state["lastActivity"] = msg.strip()
            return
        h_m = RE_HEIGHT.search(msg)
        if h_m:
            _state["lastHeight"] = int(h_m.group(1))
            return
        addr_m = RE_ADDRESS.search(msg)
        if addr_m:
            _state["miningAddress"] = addr_m.group(1)
            return
        if RE_STARTED.search(msg):
            _state["serviceStartTime"] = datetime.now().isoformat()
            return
        if "Failed to push tx" in msg:
            _state["lastActivity"] = msg.strip()
            return

def do_initial_backfill():
    """Read all xkv8 journal entries since service start for accurate counts."""
    print("Backfilling from journal history...")
    try:
        # Try to get service start time
        ts_result = subprocess.run(
            ["systemctl", "show", "xkv8", "--property=ActiveEnterTimestamp"],
            capture_output=True, text=True, timeout=5
        )
        since_arg = []
        if ts_result.returncode == 0:
            ts_val = ts_result.stdout.strip().split("=", 1)[1].strip() if "=" in ts_result.stdout else ""
            if ts_val:
                since_arg = ["--since", ts_val]
                with _lock:
                    _state["serviceStartTime"] = ts_val

        cmd = ["journalctl", "-u", "xkv8", "--no-pager", "-o", "cat"]
        if since_arg:
            cmd += since_arg

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            # Try without journalctl (might not have xkv8 service locally)
            print("No local xkv8 service found. Dashboard will show on-chain data only.")
            return

        with _lock:
            _state["bundlesSubmitted"] = 0
            _state["wins"] = 0
            _state["losses"] = 0

        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parse_log_line(f"xkv8[0]: {line}")

        with _lock:
            print(f"Backfill complete: {_state['bundlesSubmitted']} bundles, "
                  f"{_state['wins']} wins, {_state['losses']} losses")
        save_state()
    except Exception as e:
        print(f"Backfill error: {e}")

def journal_tail_loop():
    """Live-tail the xkv8 journal."""
    try:
        proc = subprocess.Popen(
            ["journalctl", "-u", "xkv8", "-f", "--no-pager", "-n", "0"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )
        print("Journal tail started")
        for line in proc.stdout:
            line = line.strip()
            if line:
                parse_log_line(line)
                save_state()
    except Exception as e:
        print(f"Journal tail error: {e}")

def status_watchdog():
    """Check if xkv8 service is active."""
    while True:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "xkv8"],
                capture_output=True, text=True, timeout=5
            )
            with _lock:
                if result.stdout.strip() != "active":
                    _state["isGrinding"] = False
                    _state["status"] = "OFFLINE"
        except Exception:
            pass
        time.sleep(10)

# ── Balance ─────────────────────────────────────────────────────────────

def get_xkv8_balance():
    now = time.time()
    interval = CFG.get("balance_check_interval", 30)
    if now - _balance_cache["ts"] < interval:
        return _balance_cache["value"]

    try:
        checker = SCRIPT_DIR / "balance_checker.py"
        result = subprocess.run(
            [sys.executable, str(checker)],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0:
            data = json.loads(result.stdout.strip())
            _balance_cache["value"] = data.get("xkv8_balance", 0.0)
            _balance_cache["ts"] = now
    except Exception:
        pass

    return _balance_cache["value"]

# ── HTTP Handler ────────────────────────────────────────────────────────

class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self.send_miner_status()
        elif parsed.path == "/api/config":
            self.send_config()
        else:
            super().do_GET()

    def send_miner_status(self):
        with _lock:
            data = {
                "currentBlock": _state["lastHeight"] or None,
                "bundlesSubmitted": _state["bundlesSubmitted"],
                "wins": _state["wins"],
                "losses": _state["losses"],
                "miningAddress": _state["miningAddress"],
                "isGrinding": _state["isGrinding"],
                "status": _state["status"],
                "lastActivity": _state["lastActivity"],
                "serviceStartTime": _state["serviceStartTime"],
                "xkv8Balance": get_xkv8_balance(),
                "timestamp": datetime.now().isoformat(),
            }
        self._json_response(data)

    def send_config(self):
        """Send miner config for the frontend to render miners."""
        safe_cfg = {
            "miners": CFG.get("miners", []),
            "target_address": CFG.get("target_address", "")[:20] + "..." if CFG.get("target_address") else "",
        }
        self._json_response(safe_cfg)

    def _json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass

# ── Main ────────────────────────────────────────────────────────────────

def main():
    port = CFG.get("dashboard_port", 8092)

    load_state()
    do_initial_backfill()

    tail_thread = threading.Thread(target=journal_tail_loop, daemon=True)
    tail_thread.start()

    watchdog_thread = threading.Thread(target=status_watchdog, daemon=True)
    watchdog_thread.start()

    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"XKV8 Dashboard running on http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        save_state()
        server.shutdown()

if __name__ == "__main__":
    main()
