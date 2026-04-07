#!/usr/bin/env python3
"""On-chain XKV8 balance checker. Requires chia_wallet_sdk."""
import asyncio
import json
import sys
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

async def check():
    from chia_wallet_sdk import Address, RpcClient, cat_puzzle_hash

    cfg = load_config()
    if not cfg.get("target_address"):
        print(json.dumps({"xkv8_balance": 0, "coins": 0, "error": "no target_address"}))
        return

    cat_tail = bytes.fromhex(cfg["cat_tail_hash"])
    target_ph = Address.decode(cfg["target_address"]).puzzle_hash
    cat_ph = cat_puzzle_hash(cat_tail, target_ph)

    client = RpcClient.mainnet()
    state = await client.get_blockchain_state()
    height = state.blockchain_state.peak.height

    res = await client.get_coin_records_by_puzzle_hash(
        cat_ph, cfg.get("genesis_height", 8521888), height + 5, False
    )

    total = 0
    coins = 0
    if res.success:
        for cr in res.coin_records:
            total += cr.coin.amount
            coins += 1

    print(json.dumps({
        "xkv8_mojos": total,
        "xkv8_balance": total / 1000,
        "coins": coins,
        "height": height
    }))

if __name__ == "__main__":
    asyncio.run(check())
