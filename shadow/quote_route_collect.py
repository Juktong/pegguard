from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Sequence

from . import constants as C

QUOTE_SIG = "quoteExactInputSingle((address,address,uint256,uint24,uint160))(uint256,uint160,uint32,uint256)"
CAST_TIMEOUT_SEC = 30


@dataclass(frozen=True)
class QuoteRow:
    amount_in_raw: int
    fee_pips: int
    block_tag: str
    amount_out_raw: int | None
    sqrt_price_x96_after: int | None
    initialized_ticks_crossed: int | None
    gas_estimate: int | None
    rank: int | None
    cost_bps_vs_best: float | None
    status: str
    error: str


def compute(
    rpc_http: str,
    quoter: str,
    token_in: str,
    token_out: str,
    token_in_decimals: int,
    token_out_decimals: int,
    fee_tiers: Sequence[int],
    amount_ins: Sequence[int],
    block_tag: str = "latest",
    chain: str = "base",
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict:
    runner = runner or subprocess.run
    rows: list[QuoteRow] = []
    for amount in amount_ins:
        amount_rows = [
            _quote_row(rpc_http, quoter, token_in, token_out, fee, amount, block_tag, runner)
            for fee in fee_tiers
        ]
        rows.extend(_rank_rows(amount_rows))
    return {
        "chain": chain,
        "quoter": quoter,
        "token_in": token_in,
        "token_out": token_out,
        "token_in_decimals": token_in_decimals,
        "token_out_decimals": token_out_decimals,
        "fee_tiers": list(fee_tiers),
        "amount_ins": list(amount_ins),
        "block_tag": block_tag,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "quote_signature": QUOTE_SIG,
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Quote Route Measurements",
        "",
        "This report uses real `eth_call` quotes against a Uniswap v3 QuoterV2-style",
        "contract. It is routeability evidence, not route-away elasticity: it shows",
        "which fee tier quoted best for the supplied exact-input amounts.",
        "",
        f"- Chain: `{report.get('chain', 'n/a')}`",
        f"- Quoter: `{report.get('quoter', 'n/a')}`",
        f"- Token in/out: `{report.get('token_in', 'n/a')}` -> `{report.get('token_out', 'n/a')}`",
        f"- Block tag: `{report.get('block_tag', 'latest')}`",
        "",
        "| Amount in raw | Fee tier | Amount out raw | Rank | Cost vs best | Gas estimate | Status |",
        "|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {int(row['amount_in_raw'])} | {int(row['fee_pips']) / 100:.2f} bps | "
            f"{_int_or_na(row.get('amount_out_raw'))} | {_int_or_na(row.get('rank'))} | "
            f"{_bps_or_na(row.get('cost_bps_vs_best'))} | {_int_or_na(row.get('gas_estimate'))} | "
            f"{row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `cost vs best` is the output shortfall relative to the best quoted fee tier for the same exact-input amount.",
            "- A quote table is not a controlled PegGuard A/B; it does not observe whether order flow routes away after dynamic premium is applied.",
            "- Failed rows remain in the table so missing pools or bad calldata are visible.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def command(
    rpc_http: str,
    quoter: str,
    token_in: str,
    token_out: str,
    amount_in: int,
    fee_pips: int,
    block_tag: str,
) -> list[str]:
    return [
        "cast",
        "call",
        quoter,
        QUOTE_SIG,
        f"({token_in},{token_out},{amount_in},{fee_pips},0)",
        "--rpc-url",
        rpc_http,
        "--block",
        block_tag,
    ]


def _quote_row(
    rpc_http: str,
    quoter: str,
    token_in: str,
    token_out: str,
    fee_pips: int,
    amount_in: int,
    block_tag: str,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> QuoteRow:
    cmd = command(rpc_http, quoter, token_in, token_out, amount_in, fee_pips, block_tag)
    try:
        result = runner(cmd, check=False, capture_output=True, text=True, timeout=CAST_TIMEOUT_SEC)
    except Exception as exc:  # pragma: no cover - defensive around subprocess/runtime failures
        return _failed_row(amount_in, fee_pips, block_tag, f"{type(exc).__name__}: {exc}")

    if result.returncode != 0:
        error = (result.stderr or result.stdout or f"cast exited {result.returncode}").strip()
        return _failed_row(amount_in, fee_pips, block_tag, error)

    values = _parse_uints(result.stdout)
    if len(values) < 4:
        return _failed_row(amount_in, fee_pips, block_tag, f"could not parse quote output: {result.stdout.strip()}")

    return QuoteRow(
        amount_in_raw=amount_in,
        fee_pips=fee_pips,
        block_tag=block_tag,
        amount_out_raw=values[0],
        sqrt_price_x96_after=values[1],
        initialized_ticks_crossed=values[2],
        gas_estimate=values[3],
        rank=None,
        cost_bps_vs_best=None,
        status="quoted",
        error="",
    )


def _rank_rows(rows: list[QuoteRow]) -> list[QuoteRow]:
    quoted = [row for row in rows if row.amount_out_raw is not None and row.amount_out_raw > 0]
    ranked = {
        row.fee_pips: rank
        for rank, row in enumerate(sorted(quoted, key=lambda item: item.amount_out_raw or 0, reverse=True), start=1)
    }
    best = max((row.amount_out_raw or 0 for row in quoted), default=0)
    output: list[QuoteRow] = []
    for row in rows:
        if row.amount_out_raw is None or best == 0:
            output.append(row)
            continue
        cost = (best - row.amount_out_raw) / best * 10_000
        output.append(
            QuoteRow(
                amount_in_raw=row.amount_in_raw,
                fee_pips=row.fee_pips,
                block_tag=row.block_tag,
                amount_out_raw=row.amount_out_raw,
                sqrt_price_x96_after=row.sqrt_price_x96_after,
                initialized_ticks_crossed=row.initialized_ticks_crossed,
                gas_estimate=row.gas_estimate,
                rank=ranked.get(row.fee_pips),
                cost_bps_vs_best=cost,
                status=row.status,
                error=row.error,
            )
        )
    return output


def _failed_row(amount_in: int, fee_pips: int, block_tag: str, error: str) -> QuoteRow:
    return QuoteRow(
        amount_in_raw=amount_in,
        fee_pips=fee_pips,
        block_tag=block_tag,
        amount_out_raw=None,
        sqrt_price_x96_after=None,
        initialized_ticks_crossed=None,
        gas_estimate=None,
        rank=None,
        cost_bps_vs_best=None,
        status="failed",
        error=error[:300],
    )


def _parse_uints(text: str) -> list[int]:
    values: list[int] = []
    for line in text.splitlines():
        match = re.match(r"\s*(\d+)\b", line)
        if match:
            values.append(int(match.group(1)))
    if values:
        return values
    return [int(value) for value in re.findall(r"\b\d+\b", text)]


def _parse_int_list(text: str) -> list[int]:
    values = [item.strip() for item in text.replace(";", ",").split(",") if item.strip()]
    if not values:
        raise ValueError("expected at least one integer")
    return [int(value, 0) for value in values]


def _int_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return str(int(value))


def _bps_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.4f} bps"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Collect real QuoterV2 route quotes")
    parser.add_argument("--rpc-http", required=True)
    parser.add_argument("--quoter", required=True)
    parser.add_argument("--token-in", required=True)
    parser.add_argument("--token-out", required=True)
    parser.add_argument("--token-in-decimals", type=int, required=True)
    parser.add_argument("--token-out-decimals", type=int, required=True)
    parser.add_argument("--fee-tiers", required=True, help="comma-separated fee tiers in pips, e.g. 100,500,3000")
    parser.add_argument("--amount-ins", required=True, help="comma-separated raw exact-input amounts")
    parser.add_argument("--block-tag", default="latest")
    parser.add_argument("--chain", default="base")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "quote_route_quotes.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "quote_route_quotes.json")
    args = parser.parse_args()

    report = compute(
        rpc_http=args.rpc_http,
        quoter=args.quoter,
        token_in=args.token_in,
        token_out=args.token_out,
        token_in_decimals=args.token_in_decimals,
        token_out_decimals=args.token_out_decimals,
        fee_tiers=_parse_int_list(args.fee_tiers),
        amount_ins=_parse_int_list(args.amount_ins),
        block_tag=args.block_tag,
        chain=args.chain,
    )
    write_outputs(report, args.out_md, args.out_json)
    failures = sum(1 for row in report["rows"] if row["status"] != "quoted")
    print(f"quote rows={len(report['rows'])}; failures={failures}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
