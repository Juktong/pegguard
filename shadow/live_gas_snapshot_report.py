from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import constants as C
from .chain_cost_report import HOOK_GAS, PYTH_UPDATE_GAS


ETH_USD_ASSUMPTION = 3_500.0
DEFAULT_TIMEOUT_SEC = 5.0


@dataclass(frozen=True)
class RpcEndpoint:
    chain: str
    env_keys: tuple[str, ...]
    default_url: str
    note: str


@dataclass(frozen=True)
class GasSnapshot:
    chain: str
    block_number: int | None
    gas_price_wei: int | None
    gas_price_gwei: float | None
    source: str
    ok: bool
    error: str | None
    observed_at_ms: int


@dataclass(frozen=True)
class LiveGasRow:
    window: str
    chain: str
    swaps: int
    notional_e6: int
    gas_per_swap: int
    gas_price_gwei: float | None
    gas_e6: int | None
    gas_bps: float | None
    peg_net_bps: float
    net_after_live_gas_bps: float | None
    viability: str


ENDPOINTS = (
    RpcEndpoint("base", ("BASE_RPC_HTTP", "CHAIN_RPC_HTTP", "RPC_HTTP"), "https://mainnet.base.org", "Base public RPC"),
    RpcEndpoint("unichain", ("UNICHAIN_RPC_HTTP", "UNICHAIN_MAINNET_RPC_URL"), "https://mainnet.unichain.org", "Unichain public RPC"),
    RpcEndpoint("arbitrum", ("ARBITRUM_RPC_HTTP", "ARB_RPC_HTTP"), "https://arb1.arbitrum.io/rpc", "Arbitrum public RPC"),
    RpcEndpoint("ethereum", ("ETHEREUM_RPC_HTTP", "MAINNET_RPC_HTTP", "ETH_RPC_HTTP"), "https://ethereum-rpc.publicnode.com", "Ethereum public RPC"),
)


def compute(economic_tests_json: Path, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> dict:
    data = _load_json(economic_tests_json)
    snapshots = [_snapshot(endpoint, timeout_sec) for endpoint in ENDPOINTS]
    rows = []
    for benchmark in data.get("benchmarks", []):
        if str(benchmark.get("name", "")) not in {"PegGuard selected", "PegGuard live shadow"}:
            continue
        for snapshot in snapshots:
            rows.append(_row(benchmark, snapshot))
    return {
        "source": str(economic_tests_json),
        "model": (
            "live gas snapshot from eth_gasPrice applied to measured PegGuard benchmark economics; "
            f"ETH/USD is held at the static chain-cost assumption ${ETH_USD_ASSUMPTION:,.0f} for comparability."
        ),
        "observed_at_ms": int(time.time() * 1000),
        "eth_usd_assumption": ETH_USD_ASSUMPTION,
        "hook_gas": HOOK_GAS,
        "default_pyth_update_gas": PYTH_UPDATE_GAS,
        "snapshots": [asdict(snapshot) for snapshot in snapshots],
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Live Gas Snapshot Economics",
        "",
        "This report samples current `eth_gasPrice` from read-only RPC endpoints and",
        "applies that gas price to the measured PegGuard benchmark windows. It is a",
        "live deployment-cost snapshot, not a calibration input.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        f"- Hook gas: {int(report.get('hook_gas', 0)):,}",
        f"- Pyth update gas: {int(report.get('default_pyth_update_gas', 0)):,}",
        "",
        "## RPC Snapshot",
        "",
        "| Chain | Block | Gas price | Source | Status |",
        "|---|---:|---:|---|---|",
    ]
    for snapshot in report.get("snapshots", []):
        lines.append(
            f"| {snapshot['chain']} | {_int_or_na(snapshot.get('block_number'))} | "
            f"{_gwei(snapshot.get('gas_price_gwei'))} | {snapshot.get('source', 'n/a')} | "
            f"{'ok' if snapshot.get('ok') else _error(snapshot.get('error'))} |"
        )
    lines.extend(
        [
            "",
            "## Economics",
            "",
            "| Window | Chain | Swaps | Notional | Gas/swap | Gas bps | PegGuard net bps | Net after live gas | Viability |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['chain']} | {int(row['swaps'])} | {_usd(int(row['notional_e6']))} | "
            f"{int(row['gas_per_swap']):,} | {_fmt_bps(row.get('gas_bps'))} | "
            f"{float(row['peg_net_bps']):.2f} | {_fmt_bps(row.get('net_after_live_gas_bps'))} | {row['viability']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- RPC URLs are not written to this report; `source` only identifies env/default selection.",
            "- This uses `eth_gasPrice`, so EIP-1559 fee-market details and L1 data fees are simplified.",
            "- Compare this with `chain_cost_report.md`; that report is deterministic, while this one moves with RPC state.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _snapshot(endpoint: RpcEndpoint, timeout_sec: float) -> GasSnapshot:
    observed = int(time.time() * 1000)
    url, source = _endpoint_url(endpoint)
    try:
        block_hex = _rpc(url, "eth_blockNumber", [], timeout_sec)
        gas_hex = _rpc(url, "eth_gasPrice", [], timeout_sec)
        gas_price = int(str(gas_hex), 16)
        return GasSnapshot(
            chain=endpoint.chain,
            block_number=int(str(block_hex), 16),
            gas_price_wei=gas_price,
            gas_price_gwei=gas_price / 1e9,
            source=source,
            ok=True,
            error=None,
            observed_at_ms=observed,
        )
    except (OSError, TimeoutError, ValueError, urllib.error.URLError) as exc:
        return GasSnapshot(
            chain=endpoint.chain,
            block_number=None,
            gas_price_wei=None,
            gas_price_gwei=None,
            source=source,
            ok=False,
            error=exc.__class__.__name__,
            observed_at_ms=observed,
        )


def _endpoint_url(endpoint: RpcEndpoint) -> tuple[str, str]:
    for key in endpoint.env_keys:
        value = os.environ.get(key)
        if value:
            return value, f"env:{key}"
    return endpoint.default_url, "default public RPC"


def _rpc(url: str, method: str, params: list[Any], timeout_sec: float) -> Any:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": "pegguard-economic-suite/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "error" in payload:
        raise ValueError("rpc error")
    return payload["result"]


def _row(benchmark: dict, snapshot: GasSnapshot) -> LiveGasRow:
    swaps = int(benchmark.get("rows", 0))
    notional = int(benchmark.get("notional_e6", 0))
    gas_per_swap = HOOK_GAS + PYTH_UPDATE_GAS
    peg_net = float(benchmark.get("net_bps", 0))
    if not snapshot.ok or snapshot.gas_price_gwei is None:
        return LiveGasRow(
            window=str(benchmark.get("window", "")),
            chain=snapshot.chain,
            swaps=swaps,
            notional_e6=notional,
            gas_per_swap=gas_per_swap,
            gas_price_gwei=None,
            gas_e6=None,
            gas_bps=None,
            peg_net_bps=peg_net,
            net_after_live_gas_bps=None,
            viability="missing gas",
        )
    gas_e6 = _gas_cost_e6(swaps, gas_per_swap, snapshot.gas_price_gwei, ETH_USD_ASSUMPTION)
    gas_bps = _bps_from_e6(gas_e6, notional)
    net_after = peg_net - gas_bps
    return LiveGasRow(
        window=str(benchmark.get("window", "")),
        chain=snapshot.chain,
        swaps=swaps,
        notional_e6=notional,
        gas_per_swap=gas_per_swap,
        gas_price_gwei=snapshot.gas_price_gwei,
        gas_e6=gas_e6,
        gas_bps=gas_bps,
        peg_net_bps=peg_net,
        net_after_live_gas_bps=net_after,
        viability=_viability(net_after),
    )


def _gas_cost_e6(swaps: int, gas_per_swap: int, gas_price_gwei: float, eth_usd: float) -> int:
    return int(round(swaps * gas_per_swap * gas_price_gwei * 1e-9 * eth_usd * 1_000_000))


def _bps_from_e6(value_e6: int, notional_e6: int) -> float:
    if notional_e6 <= 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _viability(net_after_bps: float) -> str:
    if net_after_bps >= 1.0:
        return "healthy"
    if net_after_bps >= 0:
        return "thin"
    return "negative"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _fmt_bps(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.4f} bps"


def _gwei(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.4f} gwei"


def _int_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return str(int(value))


def _error(value: object) -> str:
    if value is None:
        return "error"
    return f"error: {value}"


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Sample live RPC gas prices and apply them to PegGuard economics")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "live_gas_snapshot_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "live_gas_snapshot_report.json")
    parser.add_argument("--timeout-sec", type=float, default=DEFAULT_TIMEOUT_SEC)
    args = parser.parse_args()
    report = compute(args.economic_tests_json, args.timeout_sec)
    write_outputs(report, args.out_md, args.out_json)
    ok = sum(1 for snapshot in report["snapshots"] if snapshot["ok"])
    print(f"live gas snapshots={ok}/{len(report['snapshots'])} rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
