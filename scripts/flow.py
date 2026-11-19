#!/usr/bin/env python3
"""Whale Flow Reader: read a supplied on-chain exchange-flow snapshot
and write a structured, checkable flow report.

Dependency-free Python 3, standard library only. No network, no
credentials. Reads only the snapshot file given with --input and
writes only the report file given with --output.

Net flow is outflow minus inflow. Positive net flow means more
coins left exchanges than entered (accumulation lean); negative
net flow means more entered than left (distribution lean). When
the absolute net flow is under the neutral band (5% of total
flow), the lean is neutral.

Exit 0 on success. Exit 1 on a malformed snapshot, with nothing
written.
"""

import argparse
import json
import sys
from datetime import datetime

NAME = "whale-flow-reader"
DEFAULT_LARGE_THRESHOLD_USD = 1_000_000
NEUTRAL_BAND_PCT = 5.0
SHORT_WINDOW_HOURS = 24.0


def fail(message):
    print(f"{NAME}: {message}", file=sys.stderr)
    sys.exit(1)


def parse_time(value, field):
    if not isinstance(value, str):
        fail(f"window {field} must be an ISO timestamp string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        fail(f"window {field} is not a valid ISO timestamp: {value!r}")


def load_snapshot(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        fail(f"snapshot file not found: {path}")
    except json.JSONDecodeError as exc:
        fail(f"snapshot is not valid JSON: {exc}")
    if not isinstance(data, dict):
        fail("snapshot must be a JSON object")
    transfers = data.get("transfers")
    if not isinstance(transfers, list) or not transfers:
        fail("snapshot has no transfers list, or the list is empty")
    for index, transfer in enumerate(transfers):
        if not isinstance(transfer, dict):
            fail(f"transfer {index} is not an object")
        direction = transfer.get("direction")
        if direction not in ("in", "out"):
            fail(
                f"transfer {index} has no valid direction "
                f"('in' or 'out'): {direction!r}"
            )
        amount = transfer.get("amount_usd")
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            fail(f"transfer {index} has no numeric amount_usd")
        if amount <= 0:
            fail(f"transfer {index} amount_usd must be above zero")
    return data


def window_hours(data):
    window = data.get("window")
    if not isinstance(window, dict):
        return None
    start = window.get("start")
    end = window.get("end")
    if start is None or end is None:
        return None
    delta = parse_time(end, "end") - parse_time(start, "start")
    return delta.total_seconds() / 3600.0


def lean_for(net_flow_usd, total_flow_usd):
    if total_flow_usd <= 0:
        return "neutral"
    share = abs(net_flow_usd) / total_flow_usd * 100.0
    if share < NEUTRAL_BAND_PCT:
        return "neutral"
    return "accumulation" if net_flow_usd > 0 else "distribution"


def summarise(transfers):
    inflow = sum(t["amount_usd"] for t in transfers if t["direction"] == "in")
    outflow = sum(t["amount_usd"] for t in transfers if t["direction"] == "out")
    net = outflow - inflow
    total = inflow + outflow
    return {
        "inflow_usd": inflow,
        "outflow_usd": outflow,
        "net_flow_usd": net,
        "total_flow_usd": total,
        "net_flow_pct_of_total": (
            round(net / total * 100.0, 2) if total > 0 else 0.0
        ),
        "transfer_count": len(transfers),
    }


def build_report(data):
    transfers = data["transfers"]
    default_asset = data.get("asset")
    threshold = data.get(
        "large_transfer_threshold_usd", DEFAULT_LARGE_THRESHOLD_USD
    )
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        fail("large_transfer_threshold_usd must be a number")
    if threshold <= 0:
        fail("large_transfer_threshold_usd must be above zero")

    overall = summarise(transfers)
    overall["lean"] = lean_for(
        overall["net_flow_usd"], overall["total_flow_usd"]
    )

    per_asset = {}
    assets = sorted({t.get("asset", default_asset) for t in transfers})
    for asset in assets:
        group = [t for t in transfers if t.get("asset", default_asset) == asset]
        entry = summarise(group)
        entry["lean"] = lean_for(entry["net_flow_usd"], entry["total_flow_usd"])
        per_asset[str(asset)] = entry

    large = [
        {
            "direction": t["direction"],
            "amount_usd": t["amount_usd"],
            "asset": t.get("asset", default_asset),
            "label": t.get("label"),
        }
        for t in transfers
        if t["amount_usd"] >= threshold
    ]
    large.sort(key=lambda item: item["amount_usd"], reverse=True)

    baseline = data.get("baseline_net_flow_usd")
    if baseline is None:
        baseline_change_pct = None
    elif not isinstance(baseline, (int, float)) or isinstance(baseline, bool):
        fail("baseline_net_flow_usd must be a number")
    elif baseline == 0:
        baseline_change_pct = None
    else:
        baseline_change_pct = round(
            (overall["net_flow_usd"] - baseline) / abs(baseline) * 100.0, 2
        )

    hours = window_hours(data)
    sources = data.get("sources")
    if sources is None and isinstance(data.get("source"), str):
        sources = [data["source"]]
    unlabeled = sum(
        1 for t in transfers if not t.get("label") or t.get("label") == "unknown"
    )

    flags = []
    if unlabeled:
        flags.append(
            {
                "code": "unlabeled_transfers",
                "detail": (
                    f"{unlabeled} of {len(transfers)} transfers carry no "
                    "exchange label; their direction is counted but their "
                    "exchange is unknown."
                ),
            }
        )
    if not isinstance(sources, list) or len(sources) < 2:
        flags.append(
            {
                "code": "single_source",
                "detail": (
                    "Flow comes from a single data supplier. Labels and "
                    "coverage cannot be cross-checked; treat the read as "
                    "one supplier's view."
                ),
            }
        )
    if hours is not None and hours < SHORT_WINDOW_HOURS:
        flags.append(
            {
                "code": "short_window",
                "detail": (
                    f"Window is {hours:g} hours, under {SHORT_WINDOW_HOURS:g}h. "
                    "Short windows are noisy and can be dominated by one "
                    "or two transfers."
                ),
            }
        )
    if baseline is None:
        flags.append(
            {
                "code": "no_baseline",
                "detail": (
                    "No baseline net flow was supplied, so no "
                    "versus-baseline comparison is possible."
                ),
            }
        )

    return {
        "asset": default_asset,
        "assets": assets,
        "window": data.get("window"),
        "window_hours": hours,
        "sources": sources,
        "inflow_usd": overall["inflow_usd"],
        "outflow_usd": overall["outflow_usd"],
        "net_flow_usd": overall["net_flow_usd"],
        "total_flow_usd": overall["total_flow_usd"],
        "net_flow_pct_of_total": overall["net_flow_pct_of_total"],
        "lean": overall["lean"],
        "neutral_band_pct": NEUTRAL_BAND_PCT,
        "per_asset": per_asset,
        "baseline_net_flow_usd": baseline,
        "baseline_change_pct": baseline_change_pct,
        "large_transfer_threshold_usd": threshold,
        "large_transfers": large,
        "large_transfer_count": len(large),
        "flags": flags,
        "note": (
            "Flow is not price direction. Net outflow leans accumulation "
            "and net inflow leans distribution, but a large transfer is "
            "not a trade and exchange labels depend on the data supplier."
        ),
    }


def main():
    parser = argparse.ArgumentParser(prog=NAME)
    parser.add_argument("--input", required=True, help="flow snapshot JSON")
    parser.add_argument("--output", required=True, help="flow report JSON")
    args = parser.parse_args()
    data = load_snapshot(args.input)
    report = build_report(data)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(
        f"read {len(data['transfers'])} transfers: "
        f"net flow ${report['net_flow_usd']:,.0f}, lean {report['lean']}"
    )


if __name__ == "__main__":
    main()
