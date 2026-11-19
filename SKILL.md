---
name: whale-flow-reader
description: Read a supplied on-chain exchange-flow snapshot — inflows, outflows, net flow, large transfers — and return a structured, checkable read: accumulation or distribution lean, flow versus baseline, and uncertainty flags. It never predicts a price.
summary: Read exchange net flow and large transfers from supplied on-chain data and return an accumulation or distribution lean with uncertainty flags.
version: 1.0.0
docs_url: https://github.com/mrsaepudin40/whale-flow-reader
tags:
  - crypto
  - whale
  - onchain
  - exchange-flow
  - net-flow
  - trading
  - risk
  - market-read
keywords:
  - whale flow
  - exchange inflow outflow
  - net flow
  - accumulation distribution
  - large transfers
  - on-chain flow
use_cases:
  - Read exchange net flow for a coin before deciding
  - List large transfers above a threshold in a window
  - Check whether flow leans accumulation or distribution
---

# Whale Flow Reader

Read a supplied on-chain exchange-flow snapshot and return a
structured, checkable read: how much flowed into exchanges, how
much flowed out, the net flow, how it compares with a baseline
window, which transfers were large, and whether the flow leans
accumulation or distribution — plus every uncertainty flag that
applies.

This skill does NOT predict prices. It does not say what to buy,
sell, or hold, and it never places an order or moves funds. Flow
is not price direction: coins leaving exchanges can sit in a
wallet for months, and coins entering exchanges are not
necessarily sold. A large transfer is not a trade. The read checks
the flow as supplied, nothing more.

Use this skill when the user asks what exchange flow says about a
coin, whether whales are accumulating or distributing, which large
transfers happened in a window, or how this window compares with
the previous one.

## The snapshot

The trader supplies a flow snapshot JSON file in the format in
`reference/flow-rules.md`. It holds: the asset (or one asset per
transfer for a multi-asset snapshot), the window start and end,
the data source(s), the list of transfers (each with a direction
`in` for into an exchange or `out` for out of an exchange, an
amount in USD, and an exchange label when known), an optional
baseline net flow from a previous window, and an optional
large-transfer threshold. The agent must fetch the snapshot data
from a real source and name that source; the script never fetches
anything itself.

## Run the read

```bash
python3 scripts/flow.py --input snapshot.json --output report.json
```

The script is dependency-free Python 3, standard library only, no
network, no credentials. It reads only the snapshot file given on
the command line and writes only the report file. Read the report
back and present it to the trader in this order:

1. The lean, in plain words — accumulation, distribution, or
   neutral — with the net flow figure behind it.
2. The computed numbers: total inflow, total outflow, net flow in
   USD and as a percentage of total flow, per asset when the
   snapshot covers more than one.
3. The baseline comparison, when a baseline was supplied.
4. The large transfers, largest first.
5. Every uncertainty flag, with its detail — never hide one.

## The math, in short

Net flow is outflow minus inflow. Positive net flow means more
coins left exchanges than entered: an accumulation lean. Negative
net flow means more entered than left: a distribution lean. When
the absolute net flow is under 5% of total flow, the lean is
neutral — the flow is balanced and says nothing. The exact
threshold is stated in every report. The full rules, including
the baseline comparison and the flags, are in
`reference/flow-rules.md`.

## Rules for the agent

- Never invent a transfer, a label, a baseline, or a source the
  snapshot did not supply. A missing field is an uncertainty
  flag, not a value to fill in.
- Never present a lean as a price call. Say plainly that flow
  lags, that exchange labels depend on the data supplier and can
  be wrong, and that a large transfer is not a trade.
- Never present a single-source read as confirmed. When only one
  supplier is named, say so.
- Never place, send, or recommend an order. The read ends at the
  report.

## Honest limits

The reader checks the flow as written; it cannot verify that an
exchange label is correct, that the snapshot covers every
transfer, or that the window is representative. Flows lag the
market, labels can be wrong, and a snapshot from one supplier is
one supplier's view. It works from the snapshot's own numbers and
says so in every report.
