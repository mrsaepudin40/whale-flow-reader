# whale-flow-reader

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3](https://img.shields.io/badge/python-3-blue)](scripts/flow.py)
[![API key: not required](https://img.shields.io/badge/API%20key-not%20required-brightgreen)](reference/flow-rules.md)

Read a supplied on-chain exchange-flow snapshot and return a
structured, checkable trading read: net flow, lean
(accumulation / distribution / neutral), comparison against a
baseline, large transfers, and uncertainty flags.

This skill does NOT predict prices. Flow is lagging, exchange
labels depend on the data supplier and can be wrong, a large
transfer is not a trade, and coins entering an exchange are not
necessarily sold. An accumulation lean is not a buy signal and a
distribution lean is not a sell signal. The skill reads the flow
that was supplied — nothing more.

## Run the read

```bash
python3 scripts/flow.py --input snapshot.json --output report.json
```

Dependency-free Python 3, standard library only, no network, no
credentials. It reads only the snapshot file given on the command
line and writes only the report file.

## Files

- `SKILL.md` — the skill instructions
- `scripts/flow.py` — the flow reader
- `reference/flow-rules.md` — input schema, net-flow math,
  baseline comparison, large-transfer threshold, lean rules,
  uncertainty flags, honest limits
- `examples/` — invented flow snapshots and the reports the
  script generates from them (accumulation, distribution,
  neutral, multi-asset)

## Honest limits

The reader checks the snapshot as written; it cannot verify that
exchange labels are correct, that the data supplier's coverage is
complete, or that a transfer means what it looks like. It works
from the snapshot's own numbers and the rules in
`reference/flow-rules.md`, and it says so in every report.
