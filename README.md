# XKV8 Miner Dashboard

A real-time mining dashboard for [XKV8](https://github.com/trgarrett/xkv8) miners on the Chia blockchain.

Track your miners, watch on-chain balance update with each win, and give your mining crew unique pixel-art personalities.

![Dashboard Preview](docs/preview.png)

## Features

- **Real-time stats** from journalctl (bundles submitted, wins, losses)
- **On-chain XKV8 balance** queried directly from the Chia blockchain
- **Animated pixel miners** with customizable names, traits, and tools
- **Multi-miner support** (1-10 miners with unique appearances)
- **Interactive setup wizard** for easy onboarding
- **Mobile responsive** design
- **Win flash animations** when you land a block
- **Activity log** with color-coded events

## Quick Start

### Prerequisites

- Python 3.10+
- Rust toolchain (for `chia_wallet_sdk`)
- XKV8 miner running as a systemd service (`xkv8.service`)

### Install

```bash
git clone https://github.com/FlipThisCrypto/XKV8-Dashboard.git
cd XKV8-Dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Setup

Run the interactive setup wizard:

```bash
python3 setup.py
```

This will ask you for:
- Your XKV8 reward address
- Dashboard port (default: 8092)
- Number of miners
- Each miner's name, appearance, and animation style

### Run

```bash
python3 server.py
```

Then open `http://localhost:8092` in your browser.

### Run as a systemd service

```bash
sudo tee /etc/systemd/system/xkv8-dashboard.service > /dev/null << EOF
[Unit]
Description=XKV8 Miner Dashboard
After=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python3 server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable xkv8-dashboard
sudo systemctl start xkv8-dashboard
```

## Customization

### Miner Traits

Each miner can have one facial feature:

| Trait | Description |
|-------|-------------|
| `beard` | Brown bushy beard |
| `mustache` | Wide handlebar mustache |
| `smudge` | Dark dirt smudges on face |
| `bandana` | Red bandana under helmet |
| `scar` | Faint scar across cheek |
| `goggles` | Blue-tinted welding goggles |
| `mohawk` | Red mohawk poking through helmet |
| `eyepatch` | Black eyepatch with strap |

### Miner Animations

| Action | Description |
|--------|-------------|
| `pickaxe` | Overhead swing with spark particles |
| `shovel` | Dig, scoop, and toss dirt |
| `wheelbarrow` | Walk back and forth with ore cart |

### Shirt Colors

blue, navy, green, red, purple, teal, brown, gray, orange, black

### Helmet Colors

gold, silver, yellow-green, red, blue, lime, white, orange, dark

## Configuration

All settings are stored in `config.json`:

```json
{
  "target_address": "xch1...",
  "cat_tail_hash": "f09c8d63...",
  "genesis_height": 8521888,
  "dashboard_port": 8092,
  "balance_check_interval": 30,
  "miners": [
    {
      "name": "MyMiner",
      "host": "server1",
      "trait": "beard",
      "action": "pickaxe",
      "shirt_color": "#3366cc",
      "helmet_color": "#e8922a",
      "fee_mojos": 20000000,
      "node_type": "localhost",
      "instances": 1
    }
  ]
}
```

You can edit `config.json` directly or re-run `python3 setup.py`.

## How It Works

1. **server.py** reads `xkv8` service logs via `journalctl` to count bundles, wins, and losses
2. **balance_checker.py** queries the Chia blockchain (via `chia_wallet_sdk`) for your on-chain XKV8 balance
3. **static/index.html** renders the dashboard UI, fetching `/api/status` and `/api/config` every second
4. Miners are drawn dynamically on an HTML5 canvas based on your `config.json`

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | Current mining stats, balance, activity |
| `GET /api/config` | Miner configuration (for frontend rendering) |

## License

MIT

## Credits

Built for the [XKV8](https://github.com/trgarrett/xkv8) mining community.
