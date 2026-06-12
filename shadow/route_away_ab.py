from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C


@dataclass(frozen=True)
class Window:
    label: str
    baseline_notional_e6: int
    treatment_notional_e6: int
    treatment_fee_pips: int

    @property
    def total_notional_e6(self) -> int:
        return self.baseline_notional_e6 + self.treatment_notional_e6

    @property
    def treatment_share(self) -> float:
        if self.total_notional_e6 == 0:
            return 0.0
        return self.treatment_notional_e6 / self.total_notional_e6


@dataclass(frozen=True)
class RouteAwayResult:
    pair: str
    baseline: str
    treatment: str
    pre: Window
    post: Window
    expected_post_treatment_e6: int
    routed_away_e6: int
    route_away_rate: float
    fee_delta_bps: float
    elasticity_per_bps: float | None


def load_input(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validation_errors(payload: dict) -> list[str]:
    failures: list[str] = []
    if not str(payload.get("pair", "")).strip():
        failures.append("route-away input requires pair")
    if not str(payload.get("baseline", "")).strip():
        failures.append("route-away input requires baseline")
    if not str(payload.get("treatment", "")).strip():
        failures.append("route-away input requires treatment")
    collection = payload.get("collection", {})
    if _same_pool_label(payload.get("baseline"), payload.get("treatment")) and not _collection_disambiguates_pools(collection):
        failures.append(
            "baseline and treatment must be distinct pools; same PoolManager comparisons require distinct v4 pool ids"
        )

    pre = _optional_window("pre", payload.get("pre"), failures)
    post = _optional_window("post", payload.get("post"), failures)
    for window in tuple(w for w in (pre, post) if w is not None):
        if window.baseline_notional_e6 <= 0:
            failures.append(f"{window.label} baseline_notional_e6 must be > 0")
        if window.treatment_notional_e6 <= 0:
            failures.append(f"{window.label} treatment_notional_e6 must be > 0")
    if pre is not None and post is not None and post.treatment_fee_pips <= pre.treatment_fee_pips:
        failures.append("post treatment_fee_pips must be greater than pre treatment_fee_pips")
    failures.extend(_collection_failures(collection, payload.get("baseline"), payload.get("treatment"), pre, post))
    return failures


def evidence_errors(payload: dict) -> list[str]:
    failures = validation_errors(payload)
    if payload.get("valid") is not True:
        failures.append("controlled route-away evidence requires evaluated result artifact with valid=true")
    collection = payload.get("collection")
    if not isinstance(collection, dict) or not collection:
        failures.append("controlled route-away evidence requires collection metadata")
    if not failures:
        failures.extend(_result_field_failures(payload))
    return failures


def validate_payload(payload: dict) -> None:
    failures = validation_errors(payload)
    if failures:
        raise ValueError("invalid controlled route-away input: " + "; ".join(failures))


def evaluate(payload: dict) -> RouteAwayResult:
    pre = _window("pre", payload["pre"])
    post = _window("post", payload["post"])
    expected_post_treatment = int(post.total_notional_e6 * pre.treatment_share)
    routed_away = max(0, expected_post_treatment - post.treatment_notional_e6)
    route_away_rate = routed_away / expected_post_treatment if expected_post_treatment else 0.0
    fee_delta_bps = (post.treatment_fee_pips - pre.treatment_fee_pips) / 100
    elasticity = route_away_rate / fee_delta_bps if fee_delta_bps > 0 else None
    return RouteAwayResult(
        pair=str(payload.get("pair", "")),
        baseline=str(payload.get("baseline", "")),
        treatment=str(payload.get("treatment", "")),
        pre=pre,
        post=post,
        expected_post_treatment_e6=expected_post_treatment,
        routed_away_e6=routed_away,
        route_away_rate=route_away_rate,
        fee_delta_bps=fee_delta_bps,
        elasticity_per_bps=elasticity,
    )


def markdown(result: RouteAwayResult) -> str:
    lines = [
        "# Controlled Route-Away Experiment",
        "",
        "This report requires a live PegGuard-vs-baseline routing setup. It is the",
        "measurement that the same-swap shadow replay cannot provide.",
        "",
        f"- Pair: {result.pair or 'n/a'}",
        f"- Baseline: `{result.baseline or 'n/a'}`",
        f"- Treatment: `{result.treatment or 'n/a'}`",
        f"- Fee delta: {result.fee_delta_bps:.2f} bps",
        f"- Expected post-treatment notional: {_usd(result.expected_post_treatment_e6)}",
        f"- Observed post-treatment notional: {_usd(result.post.treatment_notional_e6)}",
        f"- Routed-away notional: {_usd(result.routed_away_e6)}",
        f"- Route-away rate: {result.route_away_rate:.2%}",
        f"- Elasticity per added bps: {_float_or_na(result.elasticity_per_bps)}",
        "",
        "## Windows",
        "",
        "| Window | Baseline notional | Treatment notional | Treatment share | Treatment fee |",
        "|---|---:|---:|---:|---:|",
    ]
    for window in (result.pre, result.post):
        lines.append(
            f"| {window.label} | {_usd(window.baseline_notional_e6)} | {_usd(window.treatment_notional_e6)} | "
            f"{window.treatment_share:.2%} | {window.treatment_fee_pips / 100:.2f} bps |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is a controlled proxy, not an oracle replay metric.",
            "- `expected_post_treatment` holds treatment share constant from the pre window and applies it to post-window total same-pair volume.",
            "- Positive routed-away notional means treatment share fell after the fee change; zero means no measurable share loss under this simple control.",
            "- Use equal-length windows with comparable liquidity incentives and no major one-sided campaigns.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(result: RouteAwayResult, out_md: Path, out_json: Path, payload: dict | None = None) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(result), encoding="utf-8")
    output = asdict(result)
    if payload and isinstance(payload.get("collection"), dict):
        output["collection"] = payload["collection"]
        output["valid"] = True
    out_json.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")


def invalid_markdown(payload: dict, errors: list[str]) -> str:
    lines = [
        "# Controlled Route-Away Experiment",
        "",
        "Status: invalid input. This artifact is not route-away evidence and does",
        "not satisfy the economic completion gate.",
        "",
        "## Errors",
        "",
    ]
    lines.extend(f"- {error}" for error in errors)
    lines.extend(
        [
            "",
            "## Required Shape",
            "",
            "- Economic completion requires an evaluated result artifact with `valid: true`.",
            "- Positive baseline and treatment notional in both pre and post windows.",
            "- Post treatment fee greater than pre treatment fee.",
            "- Baseline and treatment must be distinct pools; if both are v4 pools behind one PoolManager, collection metadata must include distinct pool ids.",
            "- Economic completion requires collection metadata: matching baseline/treatment windows, equal pre/post length, non-overlap, nonzero swaps/notional, and stable pool identities across pre/post.",
            "- Top-level pre/post notionals must match collection `quote_notional_e6` for the same window and side.",
            "- Evaluated result fields must re-compute from the pre/post windows: `expected_post_treatment_e6`, `routed_away_e6`, `route_away_rate`, `fee_delta_bps`, and `elasticity_per_bps`.",
            "",
            "## Submitted Summary",
            "",
            f"- Pair: {payload.get('pair', 'n/a') or 'n/a'}",
            f"- Baseline: `{payload.get('baseline', 'n/a') or 'n/a'}`",
            f"- Treatment: `{payload.get('treatment', 'n/a') or 'n/a'}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_invalid_outputs(payload: dict, errors: list[str], out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(invalid_markdown(payload, errors), encoding="utf-8")
    out_json.write_text(
        json.dumps({"valid": False, "errors": errors, "input": payload}, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _window(label: str, data: dict) -> Window:
    return Window(
        label=label,
        baseline_notional_e6=int(data["baseline_notional_e6"]),
        treatment_notional_e6=int(data["treatment_notional_e6"]),
        treatment_fee_pips=int(data["treatment_fee_pips"]),
    )


def _optional_window(label: str, data: object, failures: list[str]) -> Window | None:
    if not isinstance(data, dict):
        failures.append(f"{label} window missing")
        return None
    try:
        return _window(label, data)
    except (KeyError, TypeError, ValueError) as exc:
        failures.append(f"{label} window invalid: {exc}")
        return None


def _collection_failures(
    collection: object,
    baseline: object = None,
    treatment: object = None,
    pre: Window | None = None,
    post: Window | None = None,
) -> list[str]:
    if not isinstance(collection, dict) or not collection:
        return []
    failures: list[str] = []
    windows = []
    notionals: dict[str, int] = {}
    identities = {}
    for key in ("pre_baseline", "pre_treatment", "post_baseline", "post_treatment"):
        row = collection.get(key)
        if not isinstance(row, dict):
            failures.append(f"collection.{key} missing")
            continue
        start = _optional_int(row.get("start_block"))
        end = _optional_int(row.get("end_block"))
        swaps = _optional_int(row.get("swaps"))
        notional = _optional_int(row.get("quote_notional_e6"))
        if start is None or end is None or start > end:
            failures.append(f"collection.{key} block range invalid")
        if swaps is None or swaps <= 0:
            failures.append(f"collection.{key} swaps must be > 0")
        if notional is None or notional <= 0:
            failures.append(f"collection.{key} quote_notional_e6 must be > 0")
        elif notional is not None:
            notionals[key] = notional
        windows.append((key, start, end))
        try:
            identity = _collection_pool_identity(row)
        except ValueError as exc:
            failures.append(f"collection.{key} pool_id invalid: {exc}")
            identity = None
        if identity is not None:
            identities[key] = identity

    ranges = {key: (start, end) for key, start, end in windows if start is not None and end is not None and start <= end}
    if {"pre_baseline", "pre_treatment", "post_baseline", "post_treatment"}.issubset(ranges):
        if ranges["pre_baseline"] != ranges["pre_treatment"]:
            failures.append("collection pre baseline/treatment windows must match")
        if ranges["post_baseline"] != ranges["post_treatment"]:
            failures.append("collection post baseline/treatment windows must match")
        pre_start, pre_end = ranges["pre_baseline"]
        post_start, post_end = ranges["post_baseline"]
        if pre_end >= post_start:
            failures.append("collection pre window must end before post window starts")
        if pre_end - pre_start != post_end - post_start:
            failures.append("collection pre/post windows must have equal length")
    if {"pre_baseline", "pre_treatment"}.issubset(identities) and not _collection_identities_distinct(
        identities["pre_baseline"], identities["pre_treatment"]
    ):
        failures.append("collection pre baseline/treatment pools must be distinct")
    if {"post_baseline", "post_treatment"}.issubset(identities) and not _collection_identities_distinct(
        identities["post_baseline"], identities["post_treatment"]
    ):
        failures.append("collection post baseline/treatment pools must be distinct")
    if {"pre_baseline", "post_baseline"}.issubset(identities) and identities["pre_baseline"] != identities["post_baseline"]:
        failures.append("collection baseline pool identity must match across pre/post windows")
    if {"pre_treatment", "post_treatment"}.issubset(identities) and identities["pre_treatment"] != identities["post_treatment"]:
        failures.append("collection treatment pool identity must match across pre/post windows")
    if {"pre_baseline", "post_baseline"}.issubset(identities) and _normalize_pool_label(baseline) != identities["pre_baseline"][1]:
        failures.append("collection baseline pool must match top-level baseline")
    if {"pre_treatment", "post_treatment"}.issubset(identities) and _normalize_pool_label(treatment) != identities["pre_treatment"][1]:
        failures.append("collection treatment pool must match top-level treatment")
    failures.extend(_collection_notional_failures(notionals, pre, post))
    return failures


def _collection_notional_failures(notionals: dict[str, int], pre: Window | None, post: Window | None) -> list[str]:
    expected: dict[str, int] = {}
    if pre is not None:
        expected["pre_baseline"] = pre.baseline_notional_e6
        expected["pre_treatment"] = pre.treatment_notional_e6
    if post is not None:
        expected["post_baseline"] = post.baseline_notional_e6
        expected["post_treatment"] = post.treatment_notional_e6

    failures = []
    for key, top_level_notional in expected.items():
        collected_notional = notionals.get(key)
        if collected_notional is not None and collected_notional != top_level_notional:
            failures.append(
                f"collection.{key} quote_notional_e6 must match top-level {key.replace('_', ' ')} notional"
            )
    return failures


def _result_field_failures(payload: dict) -> list[str]:
    result = evaluate(payload)
    failures: list[str] = []
    int_fields = {
        "expected_post_treatment_e6": result.expected_post_treatment_e6,
        "routed_away_e6": result.routed_away_e6,
    }
    float_fields = {
        "route_away_rate": result.route_away_rate,
        "fee_delta_bps": result.fee_delta_bps,
        "elasticity_per_bps": result.elasticity_per_bps,
    }
    for field, expected in int_fields.items():
        observed = _optional_int(payload.get(field))
        if observed is None or observed != expected:
            failures.append(f"route-away result {field} must match evaluated pre/post windows")
    for field, expected in float_fields.items():
        if not _optional_float_matches(payload.get(field), expected):
            failures.append(f"route-away result {field} must match evaluated pre/post windows")
    return failures


def _optional_float_matches(value: object, expected: float | None) -> bool:
    if value is None or expected is None:
        return value is None and expected is None
    try:
        observed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return abs(observed - expected) <= 1e-12


def _optional_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _same_pool_label(left: object, right: object) -> bool:
    return str(left or "").strip().lower() == str(right or "").strip().lower() and bool(str(left or "").strip())


def _normalize_pool_label(value: object) -> str:
    return str(value or "").strip().lower()


def _collection_disambiguates_pools(collection: object) -> bool:
    if not isinstance(collection, dict):
        return False
    required = ("pre_baseline", "pre_treatment", "post_baseline", "post_treatment")
    identities = {}
    for key in required:
        row = collection.get(key)
        if not isinstance(row, dict):
            return False
        try:
            identity = _collection_pool_identity(row)
        except ValueError:
            return False
        if identity is None:
            return False
        identities[key] = identity
    return (
        _collection_identities_distinct(identities["pre_baseline"], identities["pre_treatment"])
        and _collection_identities_distinct(identities["post_baseline"], identities["post_treatment"])
        and identities["pre_baseline"] == identities["post_baseline"]
        and identities["pre_treatment"] == identities["post_treatment"]
    )


def _collection_pool_identity(row: dict) -> tuple[str, str, str | None] | None:
    pool = str(row.get("pool", "")).strip().lower()
    kind = str(row.get("kind", "v3")).strip().lower()
    if not pool:
        return None
    pool_id = _normalize_pool_id(row.get("pool_id")) if kind == "v4" else None
    return kind, pool, pool_id


def _collection_identities_distinct(
    left: tuple[str, str, str | None], right: tuple[str, str, str | None]
) -> bool:
    if left[1] != right[1]:
        return True
    if left[0] == right[0] == "v4" and left[2] and right[2] and left[2] != right[2]:
        return True
    return False


def _normalize_pool_id(value: object) -> str | None:
    if value is None:
        return None
    clean = str(value).strip().lower()
    if not clean:
        return None
    if clean.startswith("0x"):
        clean = clean[2:]
    if len(clean) > 64:
        raise ValueError("v4 pool id is too long")
    if any(char not in "0123456789abcdef" for char in clean):
        raise ValueError("v4 pool id must be hex bytes32")
    return clean.rjust(64, "0")


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _float_or_na(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Evaluate controlled PegGuard route-away elasticity")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_away_ab.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_away_ab.json")
    args = parser.parse_args()
    payload = load_input(args.input)
    errors = validation_errors(payload)
    if errors:
        write_invalid_outputs(payload, errors, args.out_md, args.out_json)
        print("route_away=invalid")
        print(f"wrote {args.out_md}")
        print(f"wrote {args.out_json}")
        return 2
    result = evaluate(payload)
    write_outputs(result, args.out_md, args.out_json, payload)
    print(f"route_away={result.route_away_rate:.2%} elasticity={_float_or_na(result.elasticity_per_bps)}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
