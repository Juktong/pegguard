from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import constants as C
from .real_position_report import (
    DEFAULT_POSITION_ID,
    DEFAULT_POSITION_URL,
    build_payload_from_env,
    compute,
    write_input_from_payload,
    write_outputs,
    write_template,
)


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(
        description="Materialize audited real-position economics into docs/real_position_input.json"
    )
    parser.add_argument("--chain")
    parser.add_argument("--position-id")
    parser.add_argument("--pool-pair")
    parser.add_argument("--capital-e6", type=int)
    parser.add_argument("--position-value-e6", type=int)
    parser.add_argument("--hodl-value-e6", type=int)
    parser.add_argument("--fees-earned-e6", type=int)
    parser.add_argument("--gas-cost-e6", type=int)
    parser.add_argument("--owner")
    parser.add_argument("--block-number", type=int)
    parser.add_argument("--collected-at")
    parser.add_argument("--token0")
    parser.add_argument("--token1")
    parser.add_argument("--fee-pips", type=int)
    parser.add_argument("--tick-lower", type=int)
    parser.add_argument("--tick-upper", type=int)
    parser.add_argument("--current-tick", type=int)
    parser.add_argument("--liquidity")
    parser.add_argument("--in-range", choices=["true", "false", "1", "0", "yes", "no"])
    parser.add_argument("--source-url")
    parser.add_argument("--out-input", type=Path, default=root / "docs" / "real_position_input.json")
    parser.add_argument("--template-json", type=Path, default=root / "docs" / "real_position_input_template.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "real_position_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "real_position_report.json")
    args = parser.parse_args()

    payload = build_payload_from_env()
    _overlay_args(payload, args)
    payload.setdefault("source_url", DEFAULT_POSITION_URL)
    payload.setdefault("position_id", DEFAULT_POSITION_ID)
    payload.setdefault("gas_cost_e6", 0)

    missing = [field for field in ("chain", "position_id", "pool_pair", "capital_e6", "position_value_e6", "hodl_value_e6", "fees_earned_e6") if payload.get(field) in (None, "")]
    if missing:
        print("missing required real-position fields: " + ", ".join(missing))
        print("no input file written")
        return 2

    write_template(args.template_json)
    write_input_from_payload(payload, args.out_input)
    report = compute(root, args.out_input, args.template_json)
    write_outputs(report, args.out_md, args.out_json)
    print(json.dumps({"status": report["status"], "input": str(args.out_input), "missing": report["missing_fields"]}, sort_keys=True))
    print(f"wrote {args.out_input}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


def _overlay_args(payload: dict, args: argparse.Namespace) -> None:
    fields = {
        "chain": args.chain,
        "position_id": args.position_id,
        "pool_pair": args.pool_pair,
        "capital_e6": args.capital_e6,
        "position_value_e6": args.position_value_e6,
        "hodl_value_e6": args.hodl_value_e6,
        "fees_earned_e6": args.fees_earned_e6,
        "gas_cost_e6": args.gas_cost_e6,
        "owner": args.owner,
        "block_number": args.block_number,
        "collected_at": args.collected_at,
        "token0": args.token0,
        "token1": args.token1,
        "fee_pips": args.fee_pips,
        "tick_lower": args.tick_lower,
        "tick_upper": args.tick_upper,
        "current_tick": args.current_tick,
        "liquidity": args.liquidity,
        "source_url": args.source_url,
    }
    for key, value in fields.items():
        if value is not None:
            payload[key] = value
    if args.in_range is not None:
        payload["in_range"] = args.in_range.lower() in {"true", "1", "yes"}


if __name__ == "__main__":
    raise SystemExit(main())
