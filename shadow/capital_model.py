from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import constants as C
from .parity import assert_parity

BASE_FEE_BPS = 5.0
DAYS = 365


@dataclass(frozen=True)
class WindowEconomics:
    name: str
    notional_usdc: float
    markout_usdc: float
    extra_usdc: float
    precision: float
    capture: float

    @property
    def base_fee_usdc(self) -> float:
        return self.notional_usdc * BASE_FEE_BPS / 10_000

    @property
    def markout_bps(self) -> float:
        return abs(self.markout_usdc) / self.notional_usdc * 10_000

    @property
    def extra_bps(self) -> float:
        return self.extra_usdc / self.notional_usdc * 10_000

    @property
    def net_static_bps(self) -> float:
        return BASE_FEE_BPS - self.markout_bps

    @property
    def net_pegguard_bps(self) -> float:
        return BASE_FEE_BPS + self.extra_bps - self.markout_bps

    @property
    def net_static_usdc(self) -> float:
        return self.base_fee_usdc - abs(self.markout_usdc)

    @property
    def net_pegguard_usdc(self) -> float:
        return self.base_fee_usdc + self.extra_usdc - abs(self.markout_usdc)


@dataclass(frozen=True)
class CapitalClass:
    name: str
    capital_usdc: float
    turnover_low: float
    turnover_high: float
    range_half_width: str
    rebalance: str
    rule: str


CAPITAL_CLASSES = [
    CapitalClass(
        "micro",
        2_500,
        0.5,
        1.5,
        "3-5%",
        "manual, at most weekly",
        "do not scale; use shadow data and only deploy if fees exceed ops cost",
    ),
    CapitalClass(
        "small",
        10_000,
        2.0,
        5.0,
        "1.5-3%",
        "daily check, rebalance only when out of range",
        "good pilot size; require >90% precision and >8% capture",
    ),
    CapitalClass(
        "focused",
        25_000,
        3.0,
        6.0,
        "1-2%",
        "active range manager",
        "best small-capital fit if p90 oracle staleness stays <=5s",
    ),
    CapitalClass(
        "serious",
        100_000,
        2.0,
        5.0,
        "1-3% ladder",
        "ladder + inventory limits",
        "scale only after multi-day capture >=15% at >=95% precision",
    ),
    CapitalClass(
        "large",
        500_000,
        1.0,
        3.0,
        "2-5% ladder",
        "market-maker process",
        "capacity constrained; route-away and hedging matter more than hook alpha",
    ),
]


def fixture_window(root: Path, name: str, rows_path: str) -> WindowEconomics:
    results = assert_parity(root)
    metrics = results[name]
    rows = json.loads((root / rows_path).read_text(encoding="utf-8"))
    notional = sum(abs(int(row["aq_e6"])) for row in rows) / 1e6
    return WindowEconomics(
        name=f"calibrated {name}",
        notional_usdc=notional,
        markout_usdc=abs(metrics.truth_markout_e6) / 1e6,
        extra_usdc=metrics.extra_e6 / 1e6,
        precision=metrics.precision_bps / 10_000,
        capture=metrics.capture_truth_bps / 10_000,
    )


def live_shadow_window(root: Path, db: Path | None = None) -> WindowEconomics | None:
    if db is None:
        db = root / "shadow" / "shadow.sqlite3"
    if not db.exists():
        return None
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    notional = (conn.execute("SELECT SUM(ABS(aq_e6)) AS n FROM ledger").fetchone()["n"] or 0) / 1e6
    markout = abs((conn.execute("SELECT SUM(truth_mk_e6) AS n FROM truth WHERE valid=1").fetchone()["n"] or 0) / 1e6)
    extra = (conn.execute("SELECT SUM(fresh_extra_e6) AS n FROM ledger").fetchone()["n"] or 0) / 1e6
    truth_extra = (
        conn.execute(
            """
            SELECT SUM(l.fresh_extra_e6) AS n
            FROM ledger l JOIN truth t ON t.ledger_id = l.id
            WHERE t.valid=1
            """
        ).fetchone()["n"]
        or 0
    ) / 1e6
    correct_extra = (
        conn.execute(
            """
            SELECT SUM(l.fresh_extra_e6) AS n
            FROM ledger l JOIN truth t ON t.ledger_id = l.id
            WHERE t.valid=1 AND t.truth_corr=1
            """
        ).fetchone()["n"]
        or 0
    ) / 1e6
    return WindowEconomics(
        name="live shadow",
        notional_usdc=notional,
        markout_usdc=markout,
        extra_usdc=extra,
        precision=correct_extra / truth_extra if truth_extra else 0.0,
        capture=truth_extra / markout if markout else 0.0,
    )


def apr_from_bps(net_bps: float, daily_turnover: float) -> float:
    return net_bps / 10_000 * daily_turnover * DAYS


def annual_dollars(capital: float, net_bps: float, daily_turnover: float) -> float:
    return capital * apr_from_bps(net_bps, daily_turnover)


def turnover_for_apr(net_bps: float, target_apr: float) -> float | None:
    if net_bps <= 0:
        return None
    return target_apr / (net_bps / 10_000 * DAYS)


def markdown(live_db: Path | None = None) -> str:
    root = C.repo_root()
    windows = [
        live_shadow_window(root, live_db),
        fixture_window(root, "calm", "test/fixtures/calm_0530.json"),
        fixture_window(root, "vol", "test/fixtures/vol_0523_hot90m.json"),
    ]
    windows = [window for window in windows if window is not None]

    lines: list[str] = [
        "# Capital Model",
        "",
        "This model converts measured PegGuard economics into LP-capital return.",
        "It does not change hook constants and should not be used as calibration input.",
        "",
        "Core formula:",
        "",
        "```text",
        "net APR = (base_fee_bps + PegGuard_extra_bps - truth_markout_bps)",
        "          / 10_000 * daily_volume_per_active_capital * 365",
        "```",
        "",
        "Uniswap v3/v4 fees accrue only to in-range active liquidity. Capital size",
        "therefore matters through `daily_volume_per_active_capital`, not just the",
        "absolute dollars deposited.",
        "",
        "Capital capacity formula:",
        "",
        "```text",
        "capital_capacity = expected_daily_volume_through_your_range",
        "                   / target_daily_volume_per_active_capital",
        "```",
        "",
        "If the range sees $1,000,000/day and the strategy needs 5x turnover,",
        "capacity for that range is about $200,000 of active capital.",
        "",
        "## Measured Windows",
        "",
        "| Window | Notional | Base fees | Truth markout | Extra | Extra bps | Markout bps | Precision | Capture | Static net bps | PegGuard net bps |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for w in windows:
        lines.append(
            f"| {w.name} | ${w.notional_usdc:,.0f} | ${w.base_fee_usdc:,.0f} | "
            f"${w.markout_usdc:,.0f} | ${w.extra_usdc:,.0f} | {w.extra_bps:.2f} | "
            f"{w.markout_bps:.2f} | {w.precision:.2%} | {w.capture:.2%} | "
            f"{w.net_static_bps:.2f} | {w.net_pegguard_bps:.2f} |"
        )

    lines.extend(
        [
            "",
            "## APR Sensitivity",
            "",
            "| Scenario | Net bps after markout | 1x turnover | 3x turnover | 5x turnover | 10x turnover |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for w in windows:
        lines.append(
            f"| {w.name} | {w.net_pegguard_bps:.2f} | "
            f"{apr_from_bps(w.net_pegguard_bps, 1):.2%} | "
            f"{apr_from_bps(w.net_pegguard_bps, 3):.2%} | "
            f"{apr_from_bps(w.net_pegguard_bps, 5):.2%} | "
            f"{apr_from_bps(w.net_pegguard_bps, 10):.2%} |"
        )

    lines.extend(
        [
            "",
            "## Required Turnover",
            "",
            "| Scenario | 10% APR | 20% APR | 30% APR | Comment |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for w in windows:
        reqs = [turnover_for_apr(w.net_pegguard_bps, apr) for apr in (0.10, 0.20, 0.30)]
        comment = "avoid or hedge; net bps are negative" if reqs[0] is None else "achievable only if active range gets this turnover"
        lines.append(
            f"| {w.name} | "
            f"{_fmt_turnover(reqs[0])} | {_fmt_turnover(reqs[1])} | {_fmt_turnover(reqs[2])} | {comment} |"
        )

    lines.extend(
        [
            "",
            "## Capital Classes",
            "",
            "Dollar results below use the live-shadow net rate because it is the most",
            "conservative current forward-test measurement. The calibrated calm and",
            "volatile rows above show what the same capital looks like under research",
            "windows.",
            "",
            "| Class | Capital | Target daily turnover | Indicative annual net $ | Range half-width | Operating parameter | Gate |",
            "|---|---:|---:|---:|---|---|---|",
        ]
    )
    live = windows[0]
    for c in CAPITAL_CLASSES:
        low = annual_dollars(c.capital_usdc, live.net_pegguard_bps, c.turnover_low)
        high = annual_dollars(c.capital_usdc, live.net_pegguard_bps, c.turnover_high)
        lines.append(
            f"| {c.name} | ${c.capital_usdc:,.0f} | {c.turnover_low:g}-{c.turnover_high:g}x | "
            f"${low:,.0f}-${high:,.0f} | {c.range_half_width} | {c.rebalance} | {c.rule} |"
        )

    lines.extend(
        [
            "",
            "## Good Parameters",
            "",
            "- Precision target: >=95% for scale-up; >=90% is the minimum economic floor.",
            "- Capture target: >=15% before serious capital; >=20% is good.",
            "- Oracle-health target: p90 observed staleness <=5s in calm and materially",
            "  below the 2s volatile guard before relying on volatile-mode economics.",
            "- Active turnover target: small capital needs >=3x daily volume/capital to be",
            "  interesting; below 1x, the hook premium is too small to matter.",
            "- Capacity cap: do not size so large that daily turnover/capital falls below",
            "  2x unless the position is being run as a hedged market-making book.",
            "- Rebalance discipline: narrow ranges create fee density but also inventory",
            "  churn; rebalance only when out of range or when oracle health/capture gates",
            "  say the strategy is live.",
            "",
            "## Practical Conclusion",
            "",
            "For small capital, the best strategy is not a passive wide LP. Use a tight,",
            "active WETH/USDC range, keep capital modest until multi-day shadow reports",
            "show >=15% capture at >=95% precision, and judge return by net fees after",
            "truth markout rather than raw fee income.",
            "",
        ]
    )
    return "\n".join(lines)


def write_output(root: Path, out_md: Path, live_db: Path | None = None) -> str:
    # root is accepted for symmetry with economic_suite; markdown() resolves the
    # canonical repo root so this stays tied to the checked-out project.
    _ = root
    text = markdown(live_db)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(text + "\n", encoding="utf-8")
    return text


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "capital_model.md")
    parser.add_argument(
        "--live-db",
        type=Path,
        default=None,
        help="live-shadow sqlite ledger for the live row (default: shadow/shadow.sqlite3)",
    )
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args()
    text = write_output(root, args.out_md, args.live_db)
    if args.stdout:
        print(text)
    print(f"wrote {args.out_md}")
    return 0


def _fmt_turnover(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}x/day"


if __name__ == "__main__":
    raise SystemExit(main())
