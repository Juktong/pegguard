from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C


RANGE_POLICIES = ("static +/-1%", "static +/-3%", "static +/-5%")
CAPITALS_E6 = (2_500_000_000, 10_000_000_000, 25_000_000_000, 100_000_000_000)
BASE_INVENTORY_CAPITAL_E6 = 10_000_000_000


@dataclass(frozen=True)
class PositionShadowRow:
    window: str
    range_policy: str
    capital_e6: int
    depth_band_bps: int
    depth_share: float | None
    duration_hours: float | None
    active_coverage: float | None
    pro_rata_base_e6: int | None
    pro_rata_extra_e6: int | None
    pro_rata_markout_e6: int | None
    pro_rata_net_e6: int | None
    inventory_il_e6: int | None
    inventory_il_bps: float | None
    combined_net_e6: int | None
    combined_net_bps: float | None
    status: str


def compute(liquidity_share_json: Path, inventory_report_json: Path) -> dict:
    liquidity_share = _load_json(liquidity_share_json)
    inventory_report = _load_json(inventory_report_json)
    base_inventory_capital_e6 = int(inventory_report.get("capital_e6", BASE_INVENTORY_CAPITAL_E6))
    inventory_by_key = {
        (str(row.get("window", "")), str(row.get("policy", ""))): row
        for row in inventory_report.get("windows", [])
    }
    rows = [
        asdict(row)
        for row in _rows(
            liquidity_share,
            inventory_by_key,
            base_inventory_capital_e6,
        )
    ]
    combined_values = [int(row["combined_net_e6"]) for row in rows if row.get("combined_net_e6") is not None]
    return {
        "model": "depth-share pro-rata PegGuard economics plus static LP inventory IL",
        "liquidity_share_source": str(liquidity_share_json),
        "inventory_source": str(inventory_report_json),
        "base_inventory_capital_e6": base_inventory_capital_e6,
        "range_policies": list(RANGE_POLICIES),
        "capital_e6": list(CAPITALS_E6),
        "rows": rows,
        "combined_rows": len(combined_values),
        "provisional_rows": len(rows) - len(combined_values),
        "worst_combined_net_e6": min(combined_values) if combined_values else None,
        "best_combined_net_e6": max(combined_values) if combined_values else None,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Position-Level LP Shadow Economics",
        "",
        "This report composes the existing economics into a position-level view:",
        "pro-rata PegGuard fee/markout economics from active-depth share plus",
        "static concentrated-LP inventory IL from the real fixture price paths.",
        "",
        "It is a shadow sizing model, not exact v4 position ownership. Calm and",
        "volatile rows include combined inventory and pro-rata economics. Live",
        "shadow rows include combined economics when the inventory report is",
        "generated from a live shadow database.",
        "",
        f"- Combined rows: {int(report.get('combined_rows', 0))}",
        f"- Provisional rows: {int(report.get('provisional_rows', 0))}",
        f"- Worst combined net: {_usd_or_na(report.get('worst_combined_net_e6'))}",
        f"- Best combined net: {_usd_or_na(report.get('best_combined_net_e6'))}",
        "",
        "| Window | Range | Capital | Depth share | Active coverage | Pro-rata net | Inventory IL | Combined net | Combined bps | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['range_policy']} | {_usd(int(row['capital_e6']))} | "
            f"{_pct_or_na(row.get('depth_share'))} | {_pct_or_na(row.get('active_coverage'))} | "
            f"{_usd_or_na(row.get('pro_rata_net_e6'))} | {_usd_or_na(row.get('inventory_il_e6'))} | "
            f"{_usd_or_na(row.get('combined_net_e6'))} | {_bps_or_na(row.get('combined_net_bps'))} | "
            f"{row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `combined_net = pro_rata_net + inventory_il` for calm and volatile fixture rows.",
            "- Live shadow rows use the same formula when live inventory rows are present.",
            "- Inventory IL is scaled linearly from the $10k inventory report for the listed capital sizes.",
            "- This report does not model route elasticity, exact v4 liquidity ownership, or active rebalancing.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _rows(
    liquidity_share: dict,
    inventory_by_key: dict[tuple[str, str], dict],
    base_inventory_capital_e6: int,
) -> list[PositionShadowRow]:
    rows = []
    for share_row in liquidity_share.get("rows", []):
        window = str(share_row.get("window", ""))
        capital_e6 = int(share_row.get("capital_e6", 0))
        if capital_e6 not in CAPITALS_E6:
            continue
        for policy in RANGE_POLICIES:
            rows.append(_row(window, policy, capital_e6, share_row, inventory_by_key, base_inventory_capital_e6))
    return rows


def _row(
    window: str,
    policy: str,
    capital_e6: int,
    share_row: dict,
    inventory_by_key: dict[tuple[str, str], dict],
    base_inventory_capital_e6: int,
) -> PositionShadowRow:
    pro_rata_net = int(share_row.get("pro_rata_net_e6", 0))
    inventory_row = inventory_by_key.get((window, policy))
    inventory_il = None
    inventory_il_bps = None
    active_coverage = None
    combined_net = None
    combined_net_bps = None
    status = "pro-rata only; inventory path unavailable"
    if inventory_row is not None and base_inventory_capital_e6 > 0:
        inventory_il = _scale_e6(int(inventory_row.get("inventory_il_e6", 0)), capital_e6, base_inventory_capital_e6)
        inventory_il_bps = (inventory_il / capital_e6) * 10_000 if capital_e6 else 0.0
        active_coverage = float(inventory_row.get("active_coverage", 0))
        combined_net = pro_rata_net + inventory_il
        combined_net_bps = (combined_net / capital_e6) * 10_000 if capital_e6 else 0.0
        status = "net positive" if combined_net >= 0 else "net negative"
    return PositionShadowRow(
        window=window,
        range_policy=policy,
        capital_e6=capital_e6,
        depth_band_bps=int(share_row.get("depth_band_bps", 0)),
        depth_share=_maybe_float(share_row.get("depth_share")),
        duration_hours=_maybe_float(share_row.get("duration_hours")),
        active_coverage=active_coverage,
        pro_rata_base_e6=_maybe_int(share_row.get("pro_rata_base_e6")),
        pro_rata_extra_e6=_maybe_int(share_row.get("pro_rata_extra_e6")),
        pro_rata_markout_e6=_maybe_int(share_row.get("pro_rata_markout_e6")),
        pro_rata_net_e6=pro_rata_net,
        inventory_il_e6=inventory_il,
        inventory_il_bps=inventory_il_bps,
        combined_net_e6=combined_net,
        combined_net_bps=combined_net_bps,
        status=status,
    )


def _scale_e6(value_e6: int, capital_e6: int, base_capital_e6: int) -> int:
    sign = -1 if value_e6 < 0 else 1
    numerator = abs(value_e6) * capital_e6
    return sign * ((numerator + base_capital_e6 // 2) // base_capital_e6)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _maybe_int(value: object) -> int | None:
    return None if value is None else int(value)


def _maybe_float(value: object) -> float | None:
    return None if value is None else float(value)


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _usd_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return _usd(int(value))


def _pct_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def _bps_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Compose pro-rata LP economics with inventory IL by position size")
    parser.add_argument("--liquidity-share-json", type=Path, default=root / "docs" / "liquidity_share_report.json")
    parser.add_argument("--inventory-report-json", type=Path, default=root / "docs" / "inventory_report.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "position_shadow_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "position_shadow_report.json")
    args = parser.parse_args()
    report = compute(args.liquidity_share_json, args.inventory_report_json)
    write_outputs(report, args.out_md, args.out_json)
    print(
        "position shadow report: "
        f"rows={len(report['rows'])} combined={report['combined_rows']} provisional={report['provisional_rows']}"
    )
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
