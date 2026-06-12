from __future__ import annotations

import argparse
import json
import os
import shlex
import tomllib
from pathlib import Path
from typing import Mapping

from . import constants as C
from .route_away_ab import validate_payload as validate_route_away_payload
from .route_away_collect import _expected_chain_id, _normalize_pool_id, validate_distinct_pool_identities
from .route_away_window_plan import compute as compute_route_window_plan


V4_SWAP_TOPIC0 = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"

REQUIRED_INPUTS = (
    (
        "rpc_url",
        ("CHAIN_RPC_WSS", "BASE_RPC_WSS", "CHAIN_RPC_HTTP", "BASE_RPC_HTTP", "RPC_HTTP"),
        "WebSocket or HTTP RPC endpoint for historical collection on the controlled chain.",
    ),
    ("pair", ("ROUTE_AWAY_PAIR", "PAIR"), "Token pair label, e.g. WETH/USDC."),
    ("baseline_pool", ("BASELINE_POOL",), "Comparable baseline pool or route address."),
    ("treatment_pool", ("TREATMENT_POOL", "POOL_MANAGER"), "PegGuard treatment pool, or v4 PoolManager address."),
    ("treatment_pool_id", ("PEGGUARD_POOL_ID", "TREATMENT_POOL_ID"), "v4 PegGuard pool id."),
    ("pre_start_block", ("PRE_START", "PRE_START_BLOCK"), "Pre-window start block."),
    ("pre_end_block", ("PRE_END", "PRE_END_BLOCK"), "Pre-window end block."),
    ("post_start_block", ("POST_START", "POST_START_BLOCK"), "Post-window start block."),
    ("post_end_block", ("POST_END", "POST_END_BLOCK"), "Post-window end block."),
    ("post_treatment_fee_pips", ("VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS", "POST_TREATMENT_FEE_PIPS"), "VWAP effective PegGuard fee in pips."),
    ("quote_token_index", ("QUOTE_TOKEN_INDEX",), "Quote token event amount index, 0 or 1."),
)

DEFAULTS = {
    "chain": "base",
    "baseline_kind": "v3",
    "treatment_kind": "v4",
    "pre_treatment_fee_pips": "500",
    "quote_decimals": "6",
    "chunk_blocks": "5000",
}

OPTIONAL_INPUTS = (
    ("chain", ("ROUTE_AWAY_CHAIN", "CHAIN"), "Chain label for the report."),
    ("baseline_kind", ("BASELINE_KIND",), "Baseline pool kind: v3 or v4."),
    ("treatment_kind", ("TREATMENT_KIND",), "Treatment pool kind: v3 or v4."),
    ("baseline_pool_id", ("BASELINE_POOL_ID",), "Baseline pool id when baseline_kind=v4."),
    ("chain_id", ("ROUTE_AWAY_CHAIN_ID", "CHAIN_ID"), "Numeric chain id used to sanity-check the selected chain label."),
    ("fee_change_block", ("FEE_CHANGE_BLOCK", "ROUTE_AWAY_FEE_CHANGE_BLOCK"), "Fee-change block used to derive equal pre/post collection windows."),
    ("pre_treatment_fee_pips", ("PRE_TREATMENT_FEE_PIPS",), "Pre-window treatment fee in pips."),
    ("quote_decimals", ("QUOTE_DECIMALS",), "Quote token decimals."),
    ("chunk_blocks", ("ROUTE_AWAY_CHUNK_BLOCKS", "CHUNK_BLOCKS"), "eth_getLogs block chunk size."),
)

SECRET_KEYS = {"rpc_url"}


def compute(
    root: Path,
    env: Mapping[str, str] | None = None,
    route_input_path: Path | None = None,
    route_ab_path: Path | None = None,
    route_sizing_path: Path | None = None,
) -> dict:
    dotenv_loaded = False
    if env is None:
        dotenv = _load_dotenv(root / ".env")
        dotenv_loaded = bool(dotenv)
        merged_env = dict(dotenv)
        merged_env.update(os.environ)
        env = merged_env
    route_input_path = route_input_path or root / "docs" / "route_away_ab_input.json"
    route_ab_path = route_ab_path or root / "docs" / "route_away_ab.json"
    route_sizing_path = route_sizing_path or root / "docs" / "route_ab_sizing_report.json"

    project_defaults = _project_defaults(root)
    values = _collect_values(env, project_defaults)
    _apply_window_plan_defaults(root, values, route_sizing_path)
    _suppress_unsafe_implicit_treatment_context(values)
    required = [_input_row(key, names, description, values, required=True) for key, names, description in REQUIRED_INPUTS]
    _apply_derivable_post_fee(required, values)
    optional = [_input_row(key, names, description, values, required=False) for key, names, description in OPTIONAL_INPUTS]
    validations = _validations(values)
    artifacts = _artifact_rows(root, route_input_path, route_ab_path)
    deployment_hints = _deployment_hints(root)
    route_ab = _load_json(route_ab_path)
    route_input = _load_json(route_input_path)
    sizing_recommendations = _sizing_recommendations(_load_json(route_sizing_path))
    collection_packets = _collection_packets(sizing_recommendations, values)
    controlled_complete = _route_ab_complete(route_ab)
    route_input_ready = _route_input_ready(route_input)
    ready_to_collect = all(row["resolved"] for row in required) and all(row["passed"] for row in validations)
    command = _command(values)
    missing = [row["key"] for row in required if not row["resolved"]]
    failed = [row["name"] for row in validations if not row["passed"]]
    unblock_plan = _unblock_plan(values, missing, failed, route_input_ready, controlled_complete)
    collection_plan = _collection_plan(values, missing, failed, ready_to_collect, controlled_complete)

    if controlled_complete:
        status = "complete"
    elif ready_to_collect:
        status = "ready to collect"
    else:
        status = "missing inputs"

    return {
        "status": status,
        "ready_to_collect": ready_to_collect,
        "controlled_result_complete": controlled_complete,
        "route_input_ready": route_input_ready,
        "dotenv_loaded": dotenv_loaded,
        "project_defaults": project_defaults,
        "missing_inputs": missing,
        "failed_validations": failed,
        "required_inputs": required,
        "optional_inputs": optional,
        "validations": validations,
        "artifacts": artifacts,
        "deployment_hints": deployment_hints,
        "sizing_recommendations": sizing_recommendations,
        "collection_packets": collection_packets,
        "unblock_plan": unblock_plan,
        "collection_plan": collection_plan,
        "command": command,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Controlled Route-Away Readiness",
        "",
        "This is a preflight for the real PegGuard-vs-baseline route-away experiment.",
        "It does not count as route-away evidence; the completion gate still requires",
        "nonzero pre/post baseline and treatment notional in `docs/route_away_ab.json`.",
        "",
        f"- Status: {report['status']}",
        f"- Ready to collect: {'yes' if report['ready_to_collect'] else 'no'}",
        f"- Controlled result complete: {'yes' if report['controlled_result_complete'] else 'no'}",
        f"- Existing input ready: {'yes' if report['route_input_ready'] else 'no'}",
        f"- Project `.env` loaded: {'yes' if report.get('dotenv_loaded') else 'no'}",
        "",
        "## Required Inputs",
        "",
        "| Input | Env names | Resolved | Value | Value source | Notes |",
        "|---|---|---:|---|---|---|",
    ]
    for row in report["required_inputs"]:
        lines.append(
            f"| `{row['key']}` | `{', '.join(row['env_names'])}` | {'yes' if row['resolved'] else 'no'} | "
            f"{row['display_value'] or 'missing'} | {row['source']} | {row['description']} |"
        )

    lines.extend(
        [
            "",
            "## Optional Inputs And Defaults",
            "",
            "| Input | Env names | Value | Value source | Notes |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report["optional_inputs"]:
        source = row["source"] if row["resolved"] else f"default `{row['default']}`"
        lines.append(
            f"| `{row['key']}` | `{', '.join(row['env_names'])}` | {row['display_value'] or 'missing'} | "
            f"{source} | {row['description']} |"
        )

    lines.extend(
        [
            "",
            "## Validations",
            "",
            "| Check | Passed | Details |",
            "|---|---:|---|",
        ]
    )
    for row in report["validations"]:
        lines.append(f"| {row['name']} | {'yes' if row['passed'] else 'no'} | {row['details']} |")

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "| Artifact | Present | Notes |",
            "|---|---:|---|",
        ]
    )
    for row in report["artifacts"]:
        lines.append(f"| `{row['path']}` | {'yes' if row['present'] else 'no'} | {row['notes']} |")

    if report.get("deployment_hints"):
        lines.extend(
            [
                "",
                "## Deployment Hints",
                "",
                "These hints come from local broadcast artifacts. They are useful for",
                "operator setup, but they do not count as controlled route-away evidence",
                "unless the route-away collector produces nonzero pre/post baseline and",
                "treatment notional.",
                "",
                "| Source | Chain | Hook | PoolManager | Pool ids | Treatment swaps | Counts for gate | Notes |",
                "|---|---:|---|---|---|---:|---:|---|",
            ]
        )
        for row in report["deployment_hints"]:
            lines.append(
                f"| `{row['source']}` | {row['chain']} | `{row['hook']}` | `{row['pool_manager']}` | "
                f"{', '.join(f'`{pool_id}`' for pool_id in row['pool_ids']) or 'none'} | "
                f"{row['treatment_swaps']} | {'yes' if row['counts_for_gate'] else 'no'} | {row['notes']} |"
            )
        lines.append("")
        for row in report["deployment_hints"]:
            suggestions = row.get("suggested_env", {})
            if not suggestions:
                continue
            lines.extend(
                [
                    f"Suggested non-gating env from `{row['source']}`:",
                    "",
                    "```sh",
                    *[f"export {key}={shlex.quote(str(value))}" for key, value in suggestions.items()],
                    "```",
                    "",
                ]
            )

    if report.get("unblock_plan"):
        lines.extend(
            [
                "",
                "## Unblock Plan",
                "",
                "| Blocker | Action | Evidence Required |",
                "|---|---|---|",
            ]
        )
        for row in report["unblock_plan"]:
            lines.append(f"| {row['blocker']} | {row['action']} | {row['evidence']} |")

    if report.get("sizing_recommendations"):
        lines.extend(
            [
                "",
                "## A/B Sizing Recommendations",
                "",
                "These rows come from `docs/route_ab_sizing_report.md`. They do not count as",
                "controlled route-away evidence; they only identify measurable starting points.",
                "",
                "| Pair | Chain | Treatment share | Baseline pool | Quote | MDE route-away | Target hours |",
                "|---|---|---:|---|---|---:|---:|",
            ]
        )
        for row in report["sizing_recommendations"]:
            lines.append(
                f"| {row['pair']} | {row['chain']} | {float(row['pre_treatment_share']):.2%} | "
                f"`{row['baseline_pool']}` | index {row['quote_token_index']}, decimals {row['quote_decimals']} | "
                f"{_rate(row.get('mde_route_away_rate'))} | {_hours(row.get('hours_for_target_treatment_notional'))} |"
            )
        lines.extend(["", "Suggested explicit env starting points:", ""])
        for row in report["sizing_recommendations"]:
            lines.extend(
                [
                    f"For {row['pair']}:",
                    "",
                    "```sh",
                    *[f"export {key}={shlex.quote(str(value))}" for key, value in row["suggested_env"].items()],
                    "```",
                    "",
                ]
            )

    if report.get("collection_packets"):
        lines.extend(
            [
                "",
                "## Collection Input Packets",
                "",
                "These packets are non-gating operator starting points. Replace every",
                "`TODO_*` value with a real deployed PegGuard pool, equal-length pre/post",
                "windows, and the measured post-window VWAP fee before running collection.",
                "",
                "| Pair | Chain | Baseline pool | Missing fields |",
                "|---|---|---|---|",
            ]
        )
        for packet in report["collection_packets"]:
            lines.append(
                f"| {packet['pair']} | {packet['chain']} | `{packet['baseline_pool']}` | "
                f"{', '.join(f'`{item}`' for item in packet['missing_fields'])} |"
            )
        lines.append("")
        for packet in report["collection_packets"]:
            lines.extend(
                [
                    f"For {packet['pair']}:",
                    "",
                    "```sh",
                    *[f"export {key}={shlex.quote(str(value))}" for key, value in packet["env"].items()],
                    "```",
                    "",
                    "Command template omitted because this packet still contains `TODO_*` placeholders.",
                    "Replace the missing fields, regenerate readiness, and use the `## Command` section once it passes.",
                    "",
                ]
            )

    if report.get("collection_plan"):
        plan = report["collection_plan"]
        lines.extend(
            [
                "",
                "## Collection Plan",
                "",
                f"- Plan status: {plan['status']}",
                f"- Target chain: {plan['chain']}",
                f"- Pair: {plan['pair']}",
                f"- Baseline: `{plan['baseline']}` ({plan['baseline_kind']})",
                f"- Treatment: `{plan['treatment']}` ({plan['treatment_kind']})",
                f"- Treatment pool id: `{plan['treatment_pool_id']}`",
                f"- Pre window: {plan['pre_window']}",
                f"- Post window: {plan['post_window']}",
                f"- Treatment fee delta: {plan['fee_delta']}",
                f"- Quote token: index {plan['quote_token_index']}, decimals {plan['quote_decimals']}",
                "",
            ]
        )
        if plan["missing_inputs"]:
            lines.append(f"- Missing inputs before collection: {', '.join(f'`{item}`' for item in plan['missing_inputs'])}")
        if plan["failed_validations"]:
            lines.append(f"- Failed validations before collection: {', '.join(f'`{item}`' for item in plan['failed_validations'])}")
        if plan["warnings"]:
            lines.extend(f"- Warning: {warning}" for warning in plan["warnings"])
        lines.append("")

    lines.extend(["", "## Command", ""])
    if report.get("ready_to_collect"):
        lines.extend(
            [
                "Required inputs and setup validations are satisfied. Run:",
                "",
                "```sh",
                report["command"],
                "```",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "No collector command is printed because readiness validations have not passed.",
                "This prevents accidentally running a mixed-network or placeholder route-away scan.",
                "Fix the missing inputs and failed validations above, then regenerate this report.",
                "",
            ]
        )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _collect_values(env: Mapping[str, str], project_defaults: Mapping[str, dict]) -> dict[str, dict]:
    values: dict[str, dict] = {}
    for key, names, _description in REQUIRED_INPUTS + OPTIONAL_INPUTS:
        name, value = _first_env(env, names)
        project_default = project_defaults.get(key, {})
        default = DEFAULTS.get(key)
        if value is not None:
            resolved = value
            source = name
        elif project_default.get("value") is not None:
            resolved = str(project_default["value"])
            source = str(project_default["source"])
        else:
            resolved = default
            source = "default" if default is not None else None
        values[key] = {
            "env_name": name,
            "env_names": list(names),
            "value": resolved,
            "present": value is not None,
            "resolved": resolved is not None,
            "source": source,
            "default": default,
            "project_default": project_default.get("value"),
        }
    return values


def _apply_window_plan_defaults(root: Path, values: dict[str, dict], route_sizing_path: Path) -> None:
    fee_change_block = _int_value(values, "fee_change_block")
    if fee_change_block is None:
        return
    if all(values[key]["present"] for key in ("pre_start_block", "pre_end_block", "post_start_block", "post_end_block")):
        return

    report = compute_route_window_plan(
        route_sizing_path,
        [root / "docs" / "route_away_proxy.json", root / "docs" / "route_away_proxy_weth_usdt.json"],
        fee_change_block=fee_change_block,
    )
    pair = str(values["pair"]["value"] or "")
    rows = report.get("rows", [])
    row = next((item for item in rows if str(item.get("pair", "")) == pair), rows[0] if rows else {})
    source = "derived from FEE_CHANGE_BLOCK via route_away_window_plan"
    for key, field in (
        ("pre_start_block", "pre_start_block"),
        ("pre_end_block", "pre_end_block"),
        ("post_start_block", "post_start_block"),
        ("post_end_block", "post_end_block"),
    ):
        if values[key]["present"]:
            continue
        value = row.get(field)
        if value is None:
            continue
        values[key]["value"] = str(value)
        values[key]["resolved"] = True
        values[key]["source"] = source


def _input_row(key: str, names: tuple[str, ...], description: str, values: dict[str, dict], required: bool) -> dict:
    value = values[key]
    display = _display_value(key, value["value"]) if value["value"] is not None else ""
    if value.get("unsafe_value") is not None:
        display = "ignored " + _display_value(key, value["unsafe_value"])
        description += " Ignored until the route-away chain, pair, baseline pool, and RPC are explicit for the same network."
    return {
        "key": key,
        "env_names": list(names),
        "required": required,
        "present": bool(value["present"]),
        "resolved": bool(value["resolved"]),
        "source": value["source"] or "missing",
        "default": value["default"],
        "display_value": display,
        "description": description,
    }


def _suppress_unsafe_implicit_treatment_context(values: dict[str, dict]) -> None:
    implicit_route_fields = [
        f"{key} from {values[key]['source'] or 'missing'}"
        for key in ("rpc_url", "chain", "pair", "baseline_pool")
        if not values[key]["present"] and values[key]["resolved"]
    ]
    if not implicit_route_fields:
        return

    reason = "cannot pair explicit treatment env with implicit route context: " + ", ".join(implicit_route_fields)
    for key in ("treatment_pool", "treatment_pool_id"):
        if not values[key]["present"]:
            continue
        values[key]["unsafe_value"] = values[key]["value"]
        values[key]["unsafe_source"] = values[key]["source"]
        values[key]["unsafe_reason"] = reason
        values[key]["value"] = None
        values[key]["resolved"] = False
        values[key]["source"] = "unsafe mixed/default context"


def _apply_derivable_post_fee(required: list[dict], values: dict[str, dict]) -> None:
    if not _can_derive_post_fee(values):
        return
    for row in required:
        if row["key"] != "post_treatment_fee_pips":
            continue
        row["resolved"] = True
        row["source"] = "v4 Swap logs during collection"
        row["display_value"] = "derive from v4 logs"
        row["description"] += " Omit this for v4 treatment collection to derive it from Swap log fee fields."


def _validations(values: dict[str, dict]) -> list[dict]:
    rows: list[dict] = []
    pre_start = _int_value(values, "pre_start_block")
    pre_end = _int_value(values, "pre_end_block")
    post_start = _int_value(values, "post_start_block")
    post_end = _int_value(values, "post_end_block")
    pre_len = None if pre_start is None or pre_end is None or pre_end < pre_start else pre_end - pre_start + 1
    post_len = None if post_start is None or post_end is None or post_end < post_start else post_end - post_start + 1
    pre_fee = _int_value(values, "pre_treatment_fee_pips")
    post_fee = _int_value(values, "post_treatment_fee_pips")
    quote_index = _int_value(values, "quote_token_index")
    quote_decimals = _int_value(values, "quote_decimals")
    baseline_kind = str(values["baseline_kind"]["value"] or "")
    treatment_kind = str(values["treatment_kind"]["value"] or "")
    baseline_pool_id = values["baseline_pool_id"]["value"]
    treatment_pool_id = values["treatment_pool_id"]["value"]

    rows.append(_network_context_validation(values))
    rows.append(_chain_id_validation(values))
    rows.append(_validation("pre window ordered", pre_start is not None and pre_end is not None and pre_start <= pre_end, _range_details(pre_start, pre_end)))
    rows.append(_validation("post window ordered", post_start is not None and post_end is not None and post_start <= post_end, _range_details(post_start, post_end)))
    rows.append(
        _validation(
            "windows non-overlapping",
            pre_end is not None and post_start is not None and pre_end < post_start,
            f"pre_end={_na(pre_end)}, post_start={_na(post_start)}",
        )
    )
    rows.append(
        _validation(
            "windows equal length",
            pre_len is not None and post_len is not None and pre_len == post_len,
            f"pre_blocks={_na(pre_len)}, post_blocks={_na(post_len)}",
        )
    )
    rows.append(
        _validation(
            "positive fee delta",
            (
                pre_fee is not None
                and (
                    (post_fee is not None and post_fee > pre_fee)
                    or (post_fee is None and _can_derive_post_fee(values))
                )
            ),
            (
                "post fee derived from v4 Swap logs; collector validates post > pre"
                if post_fee is None and _can_derive_post_fee(values)
                else f"pre={_na(pre_fee)} pips, post={_na(post_fee)} pips"
            ),
        )
    )
    rows.append(
        _validation(
            "quote token index valid",
            quote_index in (0, 1),
            f"quote_token_index={_na(quote_index)}",
        )
    )
    rows.append(
        _validation(
            "quote decimals valid",
            quote_decimals is not None and quote_decimals > 0,
            f"quote_decimals={_na(quote_decimals)}",
        )
    )
    rows.append(
        _validation(
            "pool kinds valid",
            baseline_kind in ("v3", "v4") and treatment_kind in ("v3", "v4"),
            f"baseline={baseline_kind or 'n/a'}, treatment={treatment_kind or 'n/a'}",
        )
    )
    rows.append(
        _validation(
            "v4 pool ids present",
            (baseline_kind != "v4" or bool(baseline_pool_id)) and (treatment_kind != "v4" or bool(treatment_pool_id)),
            f"baseline_pool_id={'set' if baseline_pool_id else 'missing'}, treatment_pool_id={'set' if treatment_pool_id else 'missing'}",
        )
    )
    rows.append(_pool_id_format_validation(baseline_kind, treatment_kind, baseline_pool_id, treatment_pool_id))
    rows.append(_pool_identity_validation(values, baseline_kind, treatment_kind, baseline_pool_id, treatment_pool_id))
    return rows


def _pool_id_format_validation(
    baseline_kind: str,
    treatment_kind: str,
    baseline_pool_id: object,
    treatment_pool_id: object,
) -> dict:
    failures = []
    for label, kind, pool_id in (
        ("baseline", baseline_kind, baseline_pool_id),
        ("treatment", treatment_kind, treatment_pool_id),
    ):
        if kind != "v4" or not pool_id:
            continue
        try:
            _normalize_pool_id(str(pool_id))
        except ValueError as exc:
            failures.append(f"{label}: {exc}")
    if failures:
        return _validation("v4 pool ids valid", False, "; ".join(failures))
    if (baseline_kind == "v4" and baseline_pool_id) or (treatment_kind == "v4" and treatment_pool_id):
        return _validation("v4 pool ids valid", True, "set v4 pool ids are hex bytes32-compatible")
    return _validation("v4 pool ids valid", True, "pending until v4 pool ids are present")


def _pool_identity_validation(
    values: dict[str, dict],
    baseline_kind: str,
    treatment_kind: str,
    baseline_pool_id: object,
    treatment_pool_id: object,
) -> dict:
    baseline_pool = str(values["baseline_pool"]["value"] or "")
    treatment_pool = str(values["treatment_pool"]["value"] or "")
    if not baseline_pool or not treatment_pool:
        return _validation(
            "baseline/treatment pool identities distinct",
            True,
            "pending until baseline and treatment pools are set",
        )
    if baseline_kind not in ("v3", "v4") or treatment_kind not in ("v3", "v4"):
        return _validation(
            "baseline/treatment pool identities distinct",
            True,
            "pending until pool kinds are valid",
        )
    if (baseline_kind == "v4" and not baseline_pool_id) or (treatment_kind == "v4" and not treatment_pool_id):
        return _validation(
            "baseline/treatment pool identities distinct",
            True,
            "pending until v4 pool ids are present",
        )
    try:
        validate_distinct_pool_identities(
            baseline_pool,
            treatment_pool,
            baseline_kind,
            treatment_kind,
            str(baseline_pool_id) if baseline_pool_id else None,
            str(treatment_pool_id) if treatment_pool_id else None,
        )
    except ValueError as exc:
        return _validation("baseline/treatment pool identities distinct", False, str(exc))
    if baseline_pool.strip().lower() == treatment_pool.strip().lower():
        details = "same PoolManager with distinct v4 pool ids"
    else:
        details = "baseline and treatment addresses differ"
    return _validation("baseline/treatment pool identities distinct", True, details)


def _network_context_validation(values: dict[str, dict]) -> dict:
    if not values["treatment_pool"]["present"]:
        return _validation("controlled network context explicit", True, "treatment pool not set")
    implicit = [
        f"{key} from {values[key]['source'] or 'missing'}"
        for key in ("rpc_url", "chain", "pair", "baseline_pool")
        if not values[key]["present"]
    ]
    return _validation(
        "controlled network context explicit",
        not implicit,
        "all network fields explicit" if not implicit else "implicit " + ", ".join(implicit),
    )


def _chain_id_validation(values: dict[str, dict]) -> dict:
    raw_chain_id = values["chain_id"]["value"]
    chain = str(values["chain"]["value"] or "")
    expected = _expected_chain_id(chain) if chain else None
    if raw_chain_id in (None, ""):
        return _validation("chain id matches selected chain", True, "no explicit chain id provided")
    try:
        actual = int(str(raw_chain_id), 0)
    except ValueError:
        return _validation(
            "chain id matches selected chain",
            False,
            f"chain_id={raw_chain_id} is not an integer; selected chain={chain or 'missing'}",
        )
    if expected is None:
        return _validation(
            "chain id matches selected chain",
            True,
            f"chain_id={actual}; selected chain={chain or 'missing'} has no known numeric mapping",
        )
    return _validation(
        "chain id matches selected chain",
        actual == expected,
        f"chain_id={actual}, selected chain={chain}, expected={expected}",
    )


def _can_derive_post_fee(values: dict[str, dict]) -> bool:
    return str(values["treatment_kind"]["value"] or "") == "v4" and bool(values["treatment_pool_id"]["value"])


def _artifact_rows(root: Path, route_input_path: Path, route_ab_path: Path) -> list[dict]:
    artifacts = [
        (root / "shadow" / "route_away_collect.py", "collector implementation"),
        (root / "shadow" / "route_away_ab.py", "controlled experiment evaluator"),
        (root / "docs" / "route_away_experiment.md", "operator instructions"),
        (root / "docs" / "route_away_ab_template.json", "manual input template"),
        (root / "docs" / "route_away_collector_smoke.json", "non-gating v4 log decoder smoke"),
        (root / "docs" / "route_away_window_plan.json", "non-gating equal-window block planner"),
        (root / "docs" / "route_away_rpc_preflight.json", "non-gating RPC chain/code preflight"),
        (root / "docs" / "route_ab_sizing_report.json", "controlled A/B sizing recommendations"),
        (route_input_path, "collected pre/post input"),
        (route_ab_path, "evaluated route-away result"),
    ]
    return [
        {"path": _rel(root, path), "present": path.exists(), "notes": notes}
        for path, notes in artifacts
    ]


def _deployment_hints(root: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted((root / "broadcast" / "TestnetExercise.s.sol").glob("*/run-latest.json")):
        payload = _load_json(path)
        if not payload:
            continue
        transactions = payload.get("transactions", [])
        receipts = payload.get("receipts", [])
        hook = _first_transaction_address(transactions, "PegGuardHook")
        pool_manager = _first_constructor_arg(transactions, "PegGuardHook", 0)
        pool_ids = sorted(
            {
                str(log.get("topics", ["", ""])[1])
                for receipt in receipts
                for log in receipt.get("logs", [])
                if len(log.get("topics", [])) > 1 and str(log.get("topics", [""])[0]).lower() == V4_SWAP_TOPIC0
            }
        )
        treatment_swaps = sum(
            1
            for receipt in receipts
            for log in receipt.get("logs", [])
            if log.get("topics") and str(log["topics"][0]).lower() == V4_SWAP_TOPIC0
        )
        if not hook and not pool_ids and treatment_swaps == 0:
            continue
        rows.append(
            {
                "source": _rel(root, path),
                "chain": int(payload.get("chain", 0) or 0),
                "hook": hook or "n/a",
                "pool_manager": pool_manager or "n/a",
                "pool_ids": pool_ids,
                "treatment_swaps": treatment_swaps,
                "counts_for_gate": False,
                "notes": "testnet hook smoke only; missing comparable baseline pool and explicit pre/post fee-change windows",
                "suggested_env": _deployment_env_hint(payload.get("chain"), pool_manager, pool_ids),
            }
        )
    return rows


def _deployment_env_hint(chain: object, pool_manager: str | None, pool_ids: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    if chain not in (None, "", 0):
        values["ROUTE_AWAY_CHAIN"] = f"chain-{chain}"
    if pool_manager:
        values["POOL_MANAGER"] = pool_manager
        values["TREATMENT_POOL"] = pool_manager
    if pool_ids:
        values["TREATMENT_POOL_ID"] = pool_ids[0]
        values["PEGGUARD_POOL_ID"] = pool_ids[0]
    values["TREATMENT_KIND"] = "v4"
    return values


def _sizing_recommendations(sizing_report: dict) -> list[dict]:
    rows: list[dict] = []
    for row in sizing_report.get("recommendations", [])[:3]:
        chain = str(row.get("chain", ""))
        pair = str(row.get("pair", ""))
        baseline_pool = str(row.get("baseline_pool", ""))
        quote_index = row.get("quote_token_index")
        quote_decimals = row.get("quote_decimals")
        if not chain or not pair or not baseline_pool:
            continue
        suggested_env = {
            "ROUTE_AWAY_CHAIN": chain,
            "ROUTE_AWAY_PAIR": pair,
            "BASELINE_POOL": baseline_pool,
            "BASELINE_KIND": "v3",
            "TREATMENT_KIND": "v4",
            "QUOTE_TOKEN_INDEX": _na(quote_index),
            "QUOTE_DECIMALS": _na(quote_decimals),
        }
        rows.append(
            {
                "pair": pair,
                "chain": chain,
                "baseline_pool": baseline_pool,
                "quote_token_index": _na(quote_index),
                "quote_decimals": _na(quote_decimals),
                "pre_treatment_share": float(row.get("pre_treatment_share", 0)),
                "mde_route_away_rate": row.get("mde_route_away_rate"),
                "hours_for_target_treatment_notional": row.get("hours_for_target_treatment_notional"),
                "suggested_env": suggested_env,
            }
        )
    return rows


def _collection_packets(sizing_recommendations: list[dict], values: dict[str, dict]) -> list[dict]:
    packets: list[dict] = []
    pre_fee = str(values["pre_treatment_fee_pips"]["value"] or DEFAULTS["pre_treatment_fee_pips"])
    for row in sizing_recommendations:
        env = {
            "CHAIN_RPC_HTTP": "TODO_CHAIN_RPC_HTTP",
            "ROUTE_AWAY_CHAIN": row["chain"],
            "ROUTE_AWAY_PAIR": row["pair"],
            "BASELINE_POOL": row["baseline_pool"],
            "BASELINE_KIND": "v3",
            "TREATMENT_POOL": "TODO_POOL_MANAGER_OR_TREATMENT_POOL",
            "TREATMENT_KIND": "v4",
            "PEGGUARD_POOL_ID": "TODO_V4_POOL_ID",
            "PRE_START": "TODO_PRE_START_BLOCK",
            "PRE_END": "TODO_PRE_END_BLOCK",
            "POST_START": "TODO_POST_START_BLOCK",
            "POST_END": "TODO_POST_END_BLOCK",
            "PRE_TREATMENT_FEE_PIPS": pre_fee,
            "VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS": "TODO_POST_VWAP_FEE_PIPS",
            "QUOTE_TOKEN_INDEX": row["quote_token_index"],
            "QUOTE_DECIMALS": row["quote_decimals"],
        }
        packets.append(
            {
                "pair": row["pair"],
                "chain": row["chain"],
                "baseline_pool": row["baseline_pool"],
                "missing_fields": [
                    "TREATMENT_POOL",
                    "PEGGUARD_POOL_ID",
                    "PRE_START",
                    "PRE_END",
                    "POST_START",
                    "POST_END",
                    "VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS",
                ],
                "env": env,
                "command": _packet_command(),
            }
        )
    return packets


def _packet_command() -> str:
    return "\n".join(
        [
            "python3 -m shadow.route_away_collect \\",
            '  --rpc-http "$CHAIN_RPC_HTTP" \\',
            '  --chain "$ROUTE_AWAY_CHAIN" \\',
            '  --pair "$ROUTE_AWAY_PAIR" \\',
            '  --baseline-pool "$BASELINE_POOL" \\',
            '  --baseline-kind "$BASELINE_KIND" \\',
            '  --treatment-pool "$TREATMENT_POOL" \\',
            '  --treatment-kind "$TREATMENT_KIND" \\',
            '  --treatment-pool-id "$PEGGUARD_POOL_ID" \\',
            '  --pre-start-block "$PRE_START" \\',
            '  --pre-end-block "$PRE_END" \\',
            '  --post-start-block "$POST_START" \\',
            '  --post-end-block "$POST_END" \\',
            '  --pre-treatment-fee-pips "$PRE_TREATMENT_FEE_PIPS" \\',
            '  --post-treatment-fee-pips "$VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS" \\',
            '  --quote-token-index "$QUOTE_TOKEN_INDEX" \\',
            '  --quote-decimals "$QUOTE_DECIMALS" \\',
            "  --out-input docs/route_away_ab_input.json \\",
            "  --out-md docs/route_away_ab.md \\",
            "  --out-json docs/route_away_ab.json",
        ]
    )


def _first_transaction_address(transactions: list[dict], contract_name: str) -> str | None:
    for tx in transactions:
        if tx.get("contractName") == contract_name and tx.get("contractAddress"):
            return str(tx["contractAddress"])
    return None


def _first_constructor_arg(transactions: list[dict], contract_name: str, index: int) -> str | None:
    for tx in transactions:
        if tx.get("contractName") != contract_name:
            continue
        args = tx.get("arguments")
        if isinstance(args, list) and len(args) > index:
            return str(args[index])
    return None


def _unblock_plan(
    values: dict[str, dict],
    missing: list[str],
    failed: list[str],
    route_input_ready: bool,
    controlled_complete: bool,
) -> list[dict]:
    if controlled_complete:
        return []
    rows: list[dict] = []
    if "treatment_pool_id" in missing or "v4 pool ids present" in failed:
        rows.append(
            {
                "blocker": "PegGuard v4 treatment pool id missing",
                "action": "Deploy or identify the PegGuard treatment pool on the same chain and pair as the baseline, then set `PEGGUARD_POOL_ID` or `TREATMENT_POOL_ID`.",
                "evidence": "A v4 PoolId from PoolManager Initialize/PoolKey.toId, plus the matching PoolManager address in `TREATMENT_POOL` or `POOL_MANAGER`.",
            }
        )
    if any(key in missing for key in ("pre_start_block", "pre_end_block", "post_start_block", "post_end_block")) or any(
        name in failed for name in ("pre window ordered", "post window ordered", "windows non-overlapping", "windows equal length")
    ):
        rows.append(
            {
                "blocker": "Controlled pre/post windows missing",
                "action": "Choose non-overlapping, equal-policy windows on the treatment chain: pre before PegGuard premium is enabled, post after it is enabled.",
                "evidence": "`PRE_START`, `PRE_END`, `POST_START`, and `POST_END` with nonzero swaps in both baseline and treatment pools.",
            }
        )
    if "post_treatment_fee_pips" in missing or "positive fee delta" in failed:
        rows.append(
            {
                "blocker": "Post treatment fee missing",
                "action": "Compute the volume-weighted effective PegGuard fee for the post window, including base fee plus charged dynamic premium.",
                "evidence": "`VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS` or `POST_TREATMENT_FEE_PIPS` greater than the pre treatment fee.",
            }
        )
    if not route_input_ready:
        rows.append(
            {
                "blocker": "Collected route-away input missing",
                "action": "Run the generated `shadow.route_away_collect` command after the fields above are set.",
                "evidence": "`docs/route_away_ab_input.json` and `docs/route_away_ab.json` with nonzero pre/post baseline and treatment notional.",
            }
        )
    unsafe_reason = _unsafe_treatment_reason(values)
    if unsafe_reason or (
        values["chain"]["source"] == "docs/route_away_proxy.json" and values["treatment_pool"]["source"] in {"POOL_MANAGER", "TREATMENT_POOL"}
    ):
        rows.append(
            {
                "blocker": "Chain context must be checked before collection",
                "action": "Confirm the route proxy chain, baseline pool, PoolManager, PegGuard pool id, and block windows all refer to the same network.",
                "evidence": unsafe_reason
                or "Readiness inputs should resolve from the same deployment environment, not from mixed proxy defaults and testnet deployer values.",
            }
        )
    return rows


def _collection_plan(
    values: dict[str, dict],
    missing: list[str],
    failed: list[str],
    ready_to_collect: bool,
    controlled_complete: bool,
) -> dict:
    pre_start = _int_value(values, "pre_start_block")
    pre_end = _int_value(values, "pre_end_block")
    post_start = _int_value(values, "post_start_block")
    post_end = _int_value(values, "post_end_block")
    pre_fee = _int_value(values, "pre_treatment_fee_pips")
    post_fee = _int_value(values, "post_treatment_fee_pips")
    warnings: list[str] = []

    implicit_network_fields = [
        key
        for key in ("rpc_url", "chain", "pair", "baseline_pool")
        if not values[key]["present"] and values[key]["resolved"]
    ]
    if implicit_network_fields:
        warnings.append(
            "network context uses project defaults for "
            + ", ".join(implicit_network_fields)
            + "; set explicit env values before collecting controlled evidence"
        )
    unsafe_reason = _unsafe_treatment_reason(values)
    if unsafe_reason:
        warnings.append(unsafe_reason)
    if values["treatment_pool_id"]["source"] in {"default", None, "missing"}:
        warnings.append("v4 treatment pool id must come from the deployed PegGuard pool, not a placeholder")
    if values["baseline_pool"]["source"] == "docs/route_away_proxy.json 5bps tier":
        warnings.append("baseline pool is inferred from proxy context; confirm it is on the same chain as the treatment pool")

    if controlled_complete:
        status = "complete; controlled route-away artifact already satisfies the gate"
    elif ready_to_collect:
        status = "ready to collect; run the generated command"
    else:
        status = "not ready; fill missing inputs and clear failed validations"

    return {
        "status": status,
        "chain": _display_or_missing("chain", values["chain"]["value"]),
        "pair": _display_or_missing("pair", values["pair"]["value"]),
        "baseline": _display_or_missing("baseline_pool", values["baseline_pool"]["value"]),
        "baseline_kind": str(values["baseline_kind"]["value"] or "missing"),
        "treatment": _display_or_missing("treatment_pool", values["treatment_pool"]["value"]),
        "treatment_kind": str(values["treatment_kind"]["value"] or "missing"),
        "treatment_pool_id": _display_or_missing("treatment_pool_id", values["treatment_pool_id"]["value"]),
        "pre_window": _format_window(pre_start, pre_end),
        "post_window": _format_window(post_start, post_end),
        "fee_delta": "derived from v4 Swap logs during collection" if post_fee is None and _can_derive_post_fee(values) else _format_fee_delta(pre_fee, post_fee),
        "quote_token_index": _na(_int_value(values, "quote_token_index")),
        "quote_decimals": _na(_int_value(values, "quote_decimals")),
        "missing_inputs": missing,
        "failed_validations": failed,
        "warnings": warnings,
    }


def _unsafe_treatment_reason(values: dict[str, dict]) -> str:
    reasons = [str(values[key].get("unsafe_reason", "")) for key in ("treatment_pool", "treatment_pool_id")]
    return next((reason for reason in reasons if reason), "")


def _project_defaults(root: Path) -> dict[str, dict]:
    defaults: dict[str, dict] = {}
    route_proxy = _load_json(root / "docs" / "route_away_proxy.json")
    if route_proxy:
        _set_default(defaults, "chain", route_proxy.get("chain"), "docs/route_away_proxy.json")
        _set_default(defaults, "pair", route_proxy.get("pair"), "docs/route_away_proxy.json")
        _set_default(defaults, "quote_token_index", route_proxy.get("quote_token_index"), "docs/route_away_proxy.json")
        _set_default(defaults, "quote_decimals", route_proxy.get("quote_decimals"), "docs/route_away_proxy.json")
        baseline = _pool_for_fee(route_proxy, 500)
        if baseline:
            _set_default(defaults, "baseline_pool", baseline, "docs/route_away_proxy.json 5bps tier")

    config = _load_config(root / "shadow" / "config.toml")
    rpc = config.get("rpc", {}) if isinstance(config.get("rpc"), dict) else {}
    _set_default(defaults, "rpc_url", rpc.get("arbitrum_wss_primary"), "shadow/config.toml")
    return defaults


def _set_default(defaults: dict[str, dict], key: str, value: object, source: str) -> None:
    if value is None or value == "":
        return
    defaults[key] = {"value": str(value), "source": source}


def _pool_for_fee(route_proxy: dict, fee_pips: int) -> str | None:
    for row in route_proxy.get("tiers", []):
        if int(row.get("fee_pips", 0)) == fee_pips and row.get("pool"):
            return str(row["pool"])
    return None


def _load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _command(values: dict[str, dict]) -> str:
    baseline_pool_id = " \\\n  --baseline-pool-id \"$BASELINE_POOL_ID\"" if str(values["baseline_kind"]["value"]) == "v4" else ""
    chain = _command_value(values, "chain", _arg_value(values, "chain"))
    pair = _command_value(values, "pair", '"${ROUTE_AWAY_PAIR:-$PAIR}"')
    rpc_flag, rpc_url = _rpc_command_parts(values)
    baseline_pool = _command_value(values, "baseline_pool", '"$BASELINE_POOL"')
    baseline_kind = _command_value(values, "baseline_kind", _arg_value(values, "baseline_kind"))
    treatment_kind = _command_value(values, "treatment_kind", _arg_value(values, "treatment_kind"))
    pre_start = _command_value(values, "pre_start_block", '"${PRE_START:-$PRE_START_BLOCK}"')
    pre_end = _command_value(values, "pre_end_block", '"${PRE_END:-$PRE_END_BLOCK}"')
    post_start = _command_value(values, "post_start_block", '"${POST_START:-$POST_START_BLOCK}"')
    post_end = _command_value(values, "post_end_block", '"${POST_END:-$POST_END_BLOCK}"')
    pre_fee = _command_value(values, "pre_treatment_fee_pips", _arg_value(values, "pre_treatment_fee_pips"))
    quote_index = _command_value(values, "quote_token_index", '"$QUOTE_TOKEN_INDEX"')
    quote_decimals = _command_value(values, "quote_decimals", _arg_value(values, "quote_decimals"))
    chunk_blocks = _command_value(values, "chunk_blocks", _arg_value(values, "chunk_blocks"))
    lines = [
            "python3 -m shadow.route_away_collect \\",
            f"  {rpc_flag} {rpc_url} \\",
            f"  --chain {chain} \\",
            f"  --pair {pair} \\",
            f"  --baseline-pool {baseline_pool} \\",
            f"  --baseline-kind {baseline_kind} \\{baseline_pool_id}",
            '  --treatment-pool "${TREATMENT_POOL:-$POOL_MANAGER}" \\',
            f"  --treatment-kind {treatment_kind} \\",
            '  --treatment-pool-id "${PEGGUARD_POOL_ID:-$TREATMENT_POOL_ID}" \\',
            f"  --pre-start-block {pre_start} \\",
            f"  --pre-end-block {pre_end} \\",
            f"  --post-start-block {post_start} \\",
            f"  --post-end-block {post_end} \\",
            f"  --pre-treatment-fee-pips {pre_fee} \\",
    ]
    if not (_can_derive_post_fee(values) and not values["post_treatment_fee_pips"]["present"]):
        lines.append('  --post-treatment-fee-pips "${VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS:-$POST_TREATMENT_FEE_PIPS}" \\')
    lines.extend(
        [
            f"  --quote-token-index {quote_index} \\",
            f"  --quote-decimals {quote_decimals} \\",
            f"  --chunk-blocks {chunk_blocks} \\",
            "  --out-input docs/route_away_ab_input.json \\",
            "  --out-md docs/route_away_ab.md \\",
            "  --out-json docs/route_away_ab.json",
        ]
    )
    return "\n".join(lines)


def _route_ab_complete(route_ab: dict) -> bool:
    try:
        validate_route_away_payload(route_ab)
    except (KeyError, TypeError, ValueError):
        return False
    pre = route_ab.get("pre", {})
    post = route_ab.get("post", {})
    values = [
        int(pre.get("baseline_notional_e6", 0)),
        int(pre.get("treatment_notional_e6", 0)),
        int(post.get("baseline_notional_e6", 0)),
        int(post.get("treatment_notional_e6", 0)),
    ]
    pre_fee = int(pre.get("treatment_fee_pips", 0))
    post_fee = int(post.get("treatment_fee_pips", 0))
    return all(value > 0 for value in values) and post_fee > pre_fee


def _route_input_ready(route_input: dict) -> bool:
    if not route_input:
        return False
    return _route_ab_complete(route_input)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    wanted = {name for _key, names, _description in REQUIRED_INPUTS + OPTIONAL_INPUTS for name in names}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in wanted:
            continue
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        if value:
            values[key] = value
    return values


def _first_env(env: Mapping[str, str], names: tuple[str, ...]) -> tuple[str | None, str | None]:
    for name in names:
        value = env.get(name)
        if value:
            return name, value
    return None, None


def _int_value(values: dict[str, dict], key: str) -> int | None:
    value = values[key]["value"]
    if value is None:
        return None
    try:
        return int(str(value), 10)
    except ValueError:
        return None


def _display_value(key: str, value: str | None) -> str:
    if value is None:
        return ""
    if key in SECRET_KEYS:
        return "<set>"
    if len(value) > 18:
        return value[:10] + "..." + value[-6:]
    return value


def _arg_value(values: dict[str, dict], key: str) -> str:
    return str(values[key]["value"] or DEFAULTS[key])


def _command_value(values: dict[str, dict], key: str, env_expr: str) -> str:
    value = values[key]
    source = str(value.get("source") or "")
    if not value.get("resolved"):
        return env_expr
    if source in value.get("env_names", []):
        return env_expr
    return shlex.quote(str(value["value"]))


def _rpc_command_parts(values: dict[str, dict]) -> tuple[str, str]:
    value = values["rpc_url"]
    source = str(value.get("source") or "")
    resolved = str(value.get("value") or "")
    if source in {"CHAIN_RPC_HTTP", "BASE_RPC_HTTP", "RPC_HTTP"}:
        return "--rpc-http", '"${CHAIN_RPC_HTTP:-${BASE_RPC_HTTP:-$RPC_HTTP}}"'
    if source in {"CHAIN_RPC_WSS", "BASE_RPC_WSS"}:
        return "--rpc-wss", '"${CHAIN_RPC_WSS:-$BASE_RPC_WSS}"'
    if resolved.startswith("http://") or resolved.startswith("https://"):
        return "--rpc-http", shlex.quote(resolved)
    if resolved:
        return "--rpc-wss", shlex.quote(resolved)
    return "--rpc-http", '"${CHAIN_RPC_HTTP:-${BASE_RPC_HTTP:-$RPC_HTTP}}"'


def _validation(name: str, passed: bool, details: str) -> dict:
    return {"name": name, "passed": passed, "details": details}


def _range_details(start: int | None, end: int | None) -> str:
    return f"start={_na(start)}, end={_na(end)}"


def _format_window(start: int | None, end: int | None) -> str:
    if start is None or end is None:
        return "missing"
    if end < start:
        return f"{start}-{end} (invalid)"
    return f"{start}-{end} ({end - start + 1} blocks)"


def _format_fee_delta(pre_fee: int | None, post_fee: int | None) -> str:
    if pre_fee is None or post_fee is None:
        return "missing"
    return f"{post_fee - pre_fee} pips ({(post_fee - pre_fee) / 100:.2f} bps)"


def _rate(value: object) -> str:
    if value is None:
        return "n/a"
    rate = float(value)
    if rate > 1:
        return ">100%"
    return f"{rate:.2%}"


def _hours(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.1f}h"


def _display_or_missing(key: str, value: object) -> str:
    if value is None or value == "":
        return "missing"
    return _display_value(key, str(value)) or "missing"


def _na(value: object) -> str:
    return "n/a" if value is None else str(value)


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Check readiness for the controlled route-away experiment")
    parser.add_argument("--route-input", type=Path, default=root / "docs" / "route_away_ab_input.json")
    parser.add_argument("--route-ab", type=Path, default=root / "docs" / "route_away_ab.json")
    parser.add_argument("--route-sizing", type=Path, default=root / "docs" / "route_ab_sizing_report.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_away_readiness.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_away_readiness.json")
    args = parser.parse_args()
    report = compute(root, route_input_path=args.route_input, route_ab_path=args.route_ab, route_sizing_path=args.route_sizing)
    write_outputs(report, args.out_md, args.out_json)
    print(f"route-away readiness={report['status']}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["ready_to_collect"] or report["controlled_result_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
