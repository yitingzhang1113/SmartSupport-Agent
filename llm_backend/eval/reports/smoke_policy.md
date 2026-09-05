# SmartSupport eval report: smoke_policy

Questions scored: 4

## Accuracy by category

| category | smoke_policy |
|---|---|
| policy | 75% (3/4) |
| **overall** | **75% (3/4)** |

## Accuracy by subtype

| category | subtype | n | smoke_policy |
|---|---|---|---|
| policy | damage_report_window | 1 | 1/1 |
| policy | restocking_exceptions | 1 | 0/1 |
| policy | restocking_fee | 1 | 1/1 |
| policy | return_window | 1 | 1/1 |

## Run stats

| run | clarify interrupts | transport errors | median latency | mean set recall |
|---|---|---|---|---|
| smoke_policy | 0 | 0 | 29.66s | n/a |

## Failures: smoke_policy

### q056 · policy/restocking_exceptions
- Q: Is a restocking fee charged if you shipped me the wrong item?
- gold: `[["not normally charged", "no restocking fee", "not charged", "store error", "wrong item"]]`
- why: missed_groups=[['not normally charged', 'no restocking fee', 'not charged', 'store error', 'wrong item']]
- answer: I could not find this policy in the available company documents .( Note :The provided Shipping Policy document does not address rest ocking fees for incorrect shipments .It only mentions rest ocking costs in the context of refused deliveries without authorization .) I could not find this policy in the available company documents.    (Note: The provided Shipping Policy document does not address res…
