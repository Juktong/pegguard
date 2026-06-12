from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS

COMMON_TIERS_PIPS = (100, 500, 3_000, 10_000)


@dataclass(frozen=True)
class TargetFeeRow:
    window: str
    target: str
    required_base_pips: int
    current_base_pips: int
    nearest_tier_pips: int
    tier_volume_share: float | None
    high_fee_volume_share: float | None
    viability: str


def compute(base_fee_json: Path, route_proxy_json: Path) -> dict:
    base_fee = _load_json(base_fee_json)
    route_proxy = _load_json(route_proxy_json)
    tier_shares = _tier_shares(route_proxy)
    rows = []
    for item in base_fee.get("rows", []):
        rows.extend(_rows_for_window(item, tier_shares, route_proxy))
    return {
        "base_fee_source": str(base_fee_json),
        "route_proxy_source": str(route_proxy_json),
        "route_pair": route_proxy.get("pair", "n/a"),
        "route_total_notional_e6": int(route_proxy.get("total_notional_e6", 0)),
        "high_fee_volume_share": float(route_proxy.get("high_fee_volume_share", 0)),
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Target Fee Viability",
        "",
        "This report maps required base fees from `base_fee_report` to common",
        "Uniswap fee tiers and compares them with observed same-pair fee-tier flow.",
        "It is routeability context, not calibration.",
        "",
        f"- Route pair: {report.get('route_pair', 'n/a')}",
        f"- Route proxy notional: {_usd(int(report.get('route_total_notional_e6', 0)))}",
        f"- 30 bps plus proxy volume share: {float(report.get('high_fee_volume_share', 0)):.2%}",
        "",
        "| Window | Target | Required base | Nearest common tier | Tier volume share | High-fee share | Viability |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['target']} | {_pips(int(row['required_base_pips']))} | "
            f"{_pips(int(row['nearest_tier_pips']))} | {_pct(row.get('tier_volume_share'))} | "
            f"{_pct(row.get('high_fee_volume_share'))} | {row['viability']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `core` means the required fee maps to the 5 bps tier or below, where current WETH/USDC proxy volume is concentrated.",
            "- `thin` means the target maps to 30 bps; proxy flow exists but is a small minority.",
            "- `high risk` means the target maps above 30 bps and needs controlled route-away evidence before being treated as viable.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _rows_for_window(item: dict, tier_shares: dict[int, float], route_proxy: dict) -> list[TargetFeeRow]:
    targets = [
        ("0 bps net", int(item.get("required_base_pips_zero", 0))),
        ("1 bps net", int(item.get("required_base_pips_1bps", 0))),
        ("5 bps net", int(item.get("required_base_pips_5bps", 0))),
    ]
    return [
        TargetFeeRow(
            window=str(item.get("window", "")),
            target=label,
            required_base_pips=required,
            current_base_pips=BASE_FEE_PIPS,
            nearest_tier_pips=_nearest_tier(required),
            tier_volume_share=tier_shares.get(_nearest_tier(required)),
            high_fee_volume_share=float(route_proxy.get("high_fee_volume_share", 0)),
            viability=_viability(_nearest_tier(required)),
        )
        for label, required in targets
    ]


def _tier_shares(route_proxy: dict) -> dict[int, float]:
    total = int(route_proxy.get("total_notional_e6", 0))
    if total <= 0:
        return {}
    return {int(row.get("fee_pips", 0)): int(row.get("notional_e6", 0)) / total for row in route_proxy.get("tiers", [])}


def _nearest_tier(required_pips: int) -> int:
    for tier in COMMON_TIERS_PIPS:
        if required_pips <= tier:
            return tier
    return COMMON_TIERS_PIPS[-1]


def _viability(tier_pips: int) -> str:
    if tier_pips <= 500:
        return "core"
    if tier_pips <= 3_000:
        return "thin"
    return "high risk"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _usd(value_e6: int) -> str:
    return f"${value_e6 / 1_000_000:,.2f}"


def _pips(value: int) -> str:
    return f"{value / 100:.2f} bps"


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Map required PegGuard base fees to observed fee-tier routeability")
    parser.add_argument("--base-fee-json", type=Path, default=root / "docs" / "base_fee_report.json")
    parser.add_argument("--route-proxy-json", type=Path, default=root / "docs" / "route_away_proxy.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "target_fee_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "target_fee_report.json")
    args = parser.parse_args()
    report = compute(args.base_fee_json, args.route_proxy_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"target fee viability rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
