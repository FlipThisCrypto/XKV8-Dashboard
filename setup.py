#!/usr/bin/env python3
"""XKV8 Dashboard Setup Wizard — configure miners, target address, and appearance."""

import json
import os
import sys
import secrets

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

TRAITS = ["beard", "mustache", "smudge", "bandana", "scar", "goggles", "mohawk", "eyepatch"]
ACTIONS = ["pickaxe", "shovel", "wheelbarrow"]
SHIRT_COLORS = {
    "blue": "#3366cc", "navy": "#2855a8", "green": "#2a6640",
    "red": "#8b3030", "purple": "#5a3080", "teal": "#2a5a5a",
    "brown": "#6b4226", "gray": "#4a4a5a", "orange": "#a85020",
    "black": "#1a1a2a"
}
HELMET_COLORS = {
    "gold": "#e8922a", "silver": "#a0a0a0", "yellow-green": "#b8a830",
    "red": "#d05020", "blue": "#6a6aaa", "lime": "#c0c040",
    "white": "#d0d0d0", "orange": "#e07020", "dark": "#505060"
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {
        "target_address": "",
        "cat_tail_hash": "f09c8d630a0a64eb4633c0933e0ca131e646cebb384cfc4f6718bad80859b5e8",
        "genesis_height": 8521888,
        "dashboard_port": 8092,
        "balance_check_interval": 30,
        "miners": []
    }

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"\n✅ Config saved to {CONFIG_PATH}")

def pick_option(prompt, options, allow_empty=False):
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        choice = input(f"  Choose [1-{len(options)}]: ").strip()
        if allow_empty and not choice:
            return options[0]
        try:
            idx = int(choice)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        except ValueError:
            pass
        print("  Invalid choice, try again.")

def setup_miner(index):
    print(f"\n{'='*50}")
    print(f"  MINER #{index + 1} SETUP")
    print(f"{'='*50}")

    name = input("\n  Miner name (e.g. Cheech, BigDog, etc.): ").strip()
    if not name:
        name = f"Miner-{index + 1}"

    host = input("  Host/machine name (for display, e.g. 'chong'): ").strip() or f"machine-{index+1}"

    trait = pick_option("  Pick a facial feature:", TRAITS)
    action = pick_option("  Pick an animation:", ACTIONS)
    shirt = pick_option("  Pick a shirt color:", list(SHIRT_COLORS.keys()))
    helmet = pick_option("  Pick a helmet color:", list(HELMET_COLORS.keys()))

    fee = input("  Fee in mojos (0 for luck-only): ").strip()
    try:
        fee = int(fee)
    except ValueError:
        fee = 0

    node_type = pick_option("  Node connection:", ["localhost (same machine as full node)", "remote (Tailscale/IP)", "public (mainnet API)"])

    return {
        "name": name,
        "host": host,
        "trait": trait,
        "action": action,
        "shirt_color": SHIRT_COLORS[shirt],
        "helmet_color": HELMET_COLORS[helmet],
        "fee_mojos": fee,
        "node_type": node_type.split(" ")[0],
        "instances": 1
    }

def main():
    print("""
╔══════════════════════════════════════════════════╗
║       ⛏️  XKV8 MINER DASHBOARD SETUP  ⛏️        ║
╠══════════════════════════════════════════════════╣
║  Configure your miners, pick their look, and     ║
║  get your dashboard running in minutes.          ║
╚══════════════════════════════════════════════════╝
    """)

    cfg = load_config()

    # Target address
    print("Your XKV8 reward address (where mining rewards are sent):")
    addr = input("  TARGET_ADDRESS (xch1...): ").strip()
    if addr:
        cfg["target_address"] = addr
    elif not cfg["target_address"]:
        print("  ⚠️  No address set. Dashboard won't show balance until configured.")

    # Port
    port = input(f"\nDashboard port [{cfg['dashboard_port']}]: ").strip()
    if port:
        try:
            cfg["dashboard_port"] = int(port)
        except ValueError:
            pass

    # Number of miners
    while True:
        count = input("\nHow many miners are you running? [1-10]: ").strip()
        try:
            count = int(count)
            if 1 <= count <= 10:
                break
        except ValueError:
            pass
        print("  Enter a number between 1 and 10.")

    cfg["miners"] = []
    for i in range(count):
        miner = setup_miner(i)
        cfg["miners"].append(miner)

    # Summary
    print(f"\n{'='*50}")
    print(f"  CONFIGURATION SUMMARY")
    print(f"{'='*50}")
    print(f"  Target: {cfg['target_address'][:20]}..." if cfg['target_address'] else "  Target: (not set)")
    print(f"  Port: {cfg['dashboard_port']}")
    print(f"  Miners: {len(cfg['miners'])}")
    for m in cfg["miners"]:
        fee_str = f"{m['fee_mojos']/1e6:.0f}M mojos" if m['fee_mojos'] > 0 else "luck-only"
        print(f"    - {m['name']} ({m['host']}) | {m['trait']} | {m['action']} | {fee_str}")

    confirm = input("\n  Save this configuration? [Y/n]: ").strip().lower()
    if confirm in ("", "y", "yes"):
        save_config(cfg)
        print("\n  Run the dashboard with: python3 server.py")
        print(f"  Then open: http://localhost:{cfg['dashboard_port']}")
    else:
        print("\n  Setup cancelled.")

if __name__ == "__main__":
    main()
