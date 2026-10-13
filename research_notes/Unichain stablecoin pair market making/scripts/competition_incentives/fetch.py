#!/usr/bin/env python3
"""Fetch Merkl + DefiLlama data for Unichain (chain id 130) into a data dir.
Usage: python3 -I fetch.py <outdir>
"""
import json
import os
import sys
import urllib.request
import urllib.error

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

URLS = {
    # Merkl v4 API
    "merkl_opps_130_live.json": "https://api.merkl.xyz/v4/opportunities?chainId=130&status=LIVE&items=100",
    "merkl_opps_130_live_p1.json": "https://api.merkl.xyz/v4/opportunities?chainId=130&status=LIVE&items=100&page=1",
    "merkl_opps_130_past.json": "https://api.merkl.xyz/v4/opportunities?chainId=130&status=PAST&items=100",
    "merkl_campaigns_130.json": "https://api.merkl.xyz/v4/campaigns?chainId=130&items=100",
    "merkl_chain_130.json": "https://api.merkl.xyz/v4/chains/130",
    # DefiLlama
    "llama_chains.json": "https://api.llama.fi/v2/chains",
    "llama_tvl_unichain.json": "https://api.llama.fi/v2/historicalChainTvl/Unichain",
    "llama_protocols.json": "https://api.llama.fi/protocols",
    "llama_dexs_unichain.json": "https://api.llama.fi/overview/dexs/Unichain?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true",
    "llama_fees_unichain.json": "https://api.llama.fi/overview/fees/Unichain?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true",
    "llama_stables_chains.json": "https://stablecoins.llama.fi/stablecoinchains",
    "llama_stables_unichain.json": "https://stablecoins.llama.fi/stablecoincharts/Unichain",
    "llama_yields_pools.json": "https://yields.llama.fi/pools",
}

ua = {"User-Agent": "Mozilla/5.0 research-script"}
only = set(sys.argv[2:])
for name, url in URLS.items():
    if only and name not in only:
        continue
    try:
        req = urllib.request.Request(url, headers=ua)
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(data)
        print(f"OK {name} {len(data)} bytes")
    except urllib.error.HTTPError as e:
        print(f"HTTPERR {name} {e.code} {e.read()[:200]!r}")
    except Exception as e:
        print(f"ERR {name} {e!r}")
