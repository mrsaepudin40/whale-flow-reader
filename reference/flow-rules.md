# Flow Rules

How Whale Flow Reader turns a supplied snapshot into a report.
The script never fetches data; the agent fetches the snapshot
from a real source and names that source.

## Input schema

```json
{
  "asset": "BTC",
  "window": {
    "start": "2026-11-18T00:00:00Z",
    "end": "2026-11-19T00:00:00Z"
  },
  "source": "Example exchange-flow provider",
  "sources": ["Example exchange-flow provider"],
  "transfers": [
    {
      "direction": "in",
      "amount_usd": 20000000,
      "asset": "BTC",
      "label": "Binance"
    },
    {
      "direction": "out",
      "amount_usd": 50000000,
      "asset": "BTC",
      "label": "Coinbase"
    }
  ],
  "baseline_net_flow_usd": 40000000,
  "large_transfer_threshold_usd": 1000000
}
```

- `asset` — the coin the snapshot covers. Optional when every
  transfer carries its own `asset` (multi-asset snapshot).
- `window` — start and end as ISO timestamps. Optional, but a
  missing window means no short-window check is possible.
- `source` / `sources` — who supplied the data. One string or a
  list. Fewer than two named sources raises the `single_source`
  flag.
- `transfers` — required, non-empty list. Each transfer needs
  `direction` (`in` = into an exchange, `out` = out of an
  exchange) and a positive numeric `amount_usd`. `label` is the
  exchange name when known; a missing label or `"unknown"` counts
  as unlabeled. `asset` per transfer is optional and defaults to
  the snapshot asset.
- `baseline_net_flow_usd` — optional net flow (outflow minus
  inflow) from a previous, comparable window, in USD.
- `large_transfer_threshold_usd` — optional, default 1,000,000.
  A transfer counts as large when its amount is at or above it.

## Net-flow math

- Total inflow = sum of `amount_usd` over transfers with
  direction `in`. Total outflow = the same over `out`.
- Net flow = outflow minus inflow, in USD. Computed overall and
  per asset.
- Total flow = inflow plus outflow. Net flow as a percentage of
  total flow = net flow / total flow x 100, rounded to 2 decimals.
  The percentage is signed: positive means net outflow.

## Baseline comparison

When `baseline_net_flow_usd` is supplied and is not zero:

```
change_pct = (net_flow - baseline) / abs(baseline) x 100
```

rounded to 2 decimals. A positive change means net flow moved
further toward outflow than the baseline window; a negative
change means it moved toward inflow. When no baseline is supplied
(or it is zero), the comparison is null and the `no_baseline`
flag is raised.

## Large transfers

Every transfer with `amount_usd` at or above the threshold is
listed, largest first, with direction, amount, asset, and label.
Transfers below the threshold are counted in the totals but not
listed individually.

## Accumulation / distribution lean

- Net flow positive and its absolute value at least 5% of total
  flow: **accumulation** — more coins left exchanges than
  entered.
- Net flow negative and its absolute value at least 5% of total
  flow: **distribution** — more coins entered exchanges than
  left.
- Absolute net flow under 5% of total flow: **neutral** — the
  flow is balanced and says nothing.

The 5% neutral band is stated in every report as
`neutral_band_pct`. The lean is computed overall and per asset;
the headline lean is the overall one.

## Uncertainty flags

- `unlabeled_transfers` — one or more transfers carry no
  exchange label. Their direction is counted; their exchange is
  unknown.
- `single_source` — fewer than two data suppliers are named.
  Labels and coverage cannot be cross-checked.
- `short_window` — the window is under 24 hours. Short windows
  are noisy and can be dominated by one or two transfers.
- `no_baseline` — no baseline net flow was supplied, so no
  versus-baseline comparison is possible.

A report with flags is still a valid report; the flags are part
of the read, not a failure.

## Honest limits

- The reader checks the flow as written. It cannot verify that
  an exchange label is correct, that the snapshot covers every
  transfer, or that the window is representative.
- Flows lag the market. A large transfer is not a trade, and
  coins entering an exchange are not necessarily sold.
- Flow is not price direction. An accumulation lean is not a buy
  signal and a distribution lean is not a sell signal.
- The reader never places an order, never moves funds, and never
  predicts a price.
