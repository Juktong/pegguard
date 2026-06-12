from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C

HOOK_GAS = 52_699 + 84_925
PYTH_UPDATE_GAS = 90_000


@dataclass(frozen=True)
class ChainScenario:
    chain: str
    label: str
    gas_price_gwei: float
    eth_usd: float
    pyth_update_gas: int
    fixed_oracle_usdc_e6_per_swap: int
    note: str


@dataclass(frozen=True)
class ChainCostRow:
    window: str
    chain: str
    label: str
    swaps: int
    notional_e6: int
    gas_per_swap: int
    gas_price_gwei: float
    fixed_oracle_usdc_e6_per_swap: int
    peg_net_bps: float
    gas_e6: int
    gas_bps: float
    net_after_chain_cost_bps: float
    break_even_gas_gwei: float | None
    viability: str
    note: str


CHAIN_SCENARIOS = [
    ChainScenario("base", "Base low", 0.005, 3_500.0, PYTH_UPDATE_GAS, 0, "low L2 execution-cost assumption"),
    ChainScenario("base", "Base stressed", 0.050, 3_500.0, PYTH_UPDATE_GAS, 0, "10x L2 gas-price stress"),
    ChainScenario("unichain", "Unichain low", 0.005, 3_500.0, PYTH_UPDATE_GAS, 0, "low Unichain testnet/mainnet-style assumption"),
    ChainScenario("unichain", "Unichain stressed", 0.050, 3_500.0, PYTH_UPDATE_GAS, 0, "10x Unichain gas-price stress"),
    ChainScenario("arbitrum", "Arbitrum low", 0.010, 3_500.0, PYTH_UPDATE_GAS, 0, "higher L2 gas assumption"),
    ChainScenario("arbitrum", "Arbitrum stressed", 0.100, 3_500.0, PYTH_UPDATE_GAS, 0, "10x Arbitrum gas-price stress"),
    ChainScenario("ethereum", "Ethereum L1 reference", 5.000, 3_500.0, PYTH_UPDATE_GAS, 0, "L1 reference; expected to be uneconomic for small swaps"),
]


def compute(economic_tests_json: Path) -> dict:
    data = _load_json(economic_tests_json)
    rows: list[ChainCostRow] = []
    for benchmark in data.get("benchmarks", []):
        name = str(benchmark.get("name", ""))
        if name not in {"PegGuard selected", "PegGuard live shadow"}:
            continue
        for scenario in CHAIN_SCENARIOS:
            rows.append(_row(benchmark, scenario))
    return {
        "source": str(economic_tests_json),
        "hook_gas": HOOK_GAS,
        "default_pyth_update_gas": PYTH_UPDATE_GAS,
        "model": (
            "static chain-cost stress; gas assumptions are scenario inputs, not live gas quotes. "
            "Costs are charged per swap against the measured PegGuard benchmark notional."
        ),
        "scenarios": [asdict(item) for item in CHAIN_SCENARIOS],
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Chain Cost Matrix",
        "",
        "This report applies static per-chain gas assumptions to measured PegGuard",
        "benchmark economics. It is a repeatable deployment-cost stress test, not",
        "a live gas oracle or calibration input.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Hook gas: {int(report.get('hook_gas', 0)):,}",
        f"- Default Pyth update gas allowance: {int(report.get('default_pyth_update_gas', 0)):,}",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "## Scenario Inputs",
        "",
        "| Chain | Label | Gas gwei | ETH/USD | Pyth gas | Fixed oracle cost/swap | Note |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for scenario in report.get("scenarios", []):
        lines.append(
            f"| {scenario['chain']} | {scenario['label']} | {float(scenario['gas_price_gwei']):.3f} | "
            f"${float(scenario['eth_usd']):,.0f} | {int(scenario['pyth_update_gas']):,} | "
            f"{_usd(int(scenario['fixed_oracle_usdc_e6_per_swap']))} | {scenario['note']} |"
        )
    lines.extend(
        [
            "",
            "## Results",
            "",
            "| Window | Chain | Scenario | Swaps | Notional | Gas/swap | Gas bps | PegGuard net bps | Net after chain cost | Break-even gas | Viability |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['chain']} | {row['label']} | {int(row['swaps'])} | "
            f"{_usd(int(row['notional_e6']))} | {int(row['gas_per_swap']):,} | "
            f"{float(row['gas_bps']):.4f} | {float(row['peg_net_bps']):.2f} | "
            f"{float(row['net_after_chain_cost_bps']):.2f} | {_gwei(row.get('break_even_gas_gwei'))} | "
            f"{row['viability']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `break-even gas` is the gas price where measured PegGuard net bps would be fully consumed by per-swap chain cost.",
            "- `viability` only covers execution/oracle cost; route-away and live liquidity still require the separate route-away gates.",
            "- L1 rows are reference stress rows and should not be read as a target deployment recommendation.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(benchmark: dict, scenario: ChainScenario) -> ChainCostRow:
    swaps = int(benchmark.get("rows", 0))
    notional_e6 = int(benchmark.get("notional_e6", 0))
    gas_per_swap = HOOK_GAS + int(scenario.pyth_update_gas)
    variable_cost_e6 = _gas_cost_e6(swaps, gas_per_swap, scenario.gas_price_gwei, scenario.eth_usd)
    fixed_cost_e6 = swaps * int(scenario.fixed_oracle_usdc_e6_per_swap)
    gas_e6 = variable_cost_e6 + fixed_cost_e6
    gas_bps = _bps(gas_e6, notional_e6)
    peg_net_bps = float(benchmark.get("net_bps", 0))
    net_after = peg_net_bps - gas_bps
    break_even = _break_even_gwei(peg_net_bps, notional_e6, swaps, gas_per_swap, scenario.eth_usd)
    return ChainCostRow(
        window=str(benchmark.get("window", "")),
        chain=scenario.chain,
        label=scenario.label,
        swaps=swaps,
        notional_e6=notional_e6,
        gas_per_swap=gas_per_swap,
        gas_price_gwei=float(scenario.gas_price_gwei),
        fixed_oracle_usdc_e6_per_swap=int(scenario.fixed_oracle_usdc_e6_per_swap),
        peg_net_bps=peg_net_bps,
        gas_e6=gas_e6,
        gas_bps=gas_bps,
        net_after_chain_cost_bps=net_after,
        break_even_gas_gwei=break_even,
        viability=_viability(net_after),
        note=scenario.note,
    )


def _gas_cost_e6(swaps: int, gas_per_swap: int, gas_price_gwei: float, eth_usd: float) -> int:
    return int(round(swaps * gas_per_swap * gas_price_gwei * 1e-9 * eth_usd * 1_000_000))


def _break_even_gwei(
    peg_net_bps: float,
    notional_e6: int,
    swaps: int,
    gas_per_swap: int,
    eth_usd: float,
) -> float | None:
    if peg_net_bps <= 0 or swaps <= 0 or gas_per_swap <= 0 or eth_usd <= 0:
        return None
    net_usd = (peg_net_bps / 10_000) * (notional_e6 / 1_000_000)
    return net_usd / (swaps * gas_per_swap * eth_usd * 1e-9)


def _bps(value_e6: int, notional_e6: int) -> float:
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


def _gwei(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.3f}"


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Apply static chain gas assumptions to measured PegGuard economics")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "chain_cost_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "chain_cost_report.json")
    args = parser.parse_args()
    report = compute(args.economic_tests_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"chain cost rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
