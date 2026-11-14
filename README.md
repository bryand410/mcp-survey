# mcp-survey

What the most-installed public MCP servers actually expose to the model.

Most scanners in this space publish benchmarks against synthetic fixtures. This
one runs against the real catalogue and publishes what comes back, including
its own defects.

**Read the report: [What 71 public MCP servers expose to the model](docs/2026-11-public-mcp-survey.md)**

---

## The result in one table

| | |
|---|---|
| servers launched | 71 |
| servers that answered `initialize` | 26 (37%) |
| tool definitions inspected | 420 |
| findings after excluding harness artefacts | 10 — 7 high, 3 medium |
| — all of them | `toxic_flow`, intra-server |
| critical findings | 4 in the first run, **all false positives**, fixed |

## Method

1. **Catalogue** — npm packages tagged `mcp-server`, `mcp` or
   `modelcontextprotocol`, ranked by real weekly download counts, not by the
   registry's popularity score (which saturates at 1.000 for hundreds of
   packages and therefore ranks nothing). 374 candidates, 71 with a measurable
   install base.
2. **Scan** — each server is started through `npx -y <package>`, exactly as a
   client would start it, and asked for its tool list. `mcp-scrutiny` scores
   every description with its trained feature model plus the deterministic
   checks (invisible Unicode, encoded payloads, cross-server shadowing, toxic
   flows).
3. **Measure** — a server that never answers is recorded as silent, never
   dropped. The response rate is part of the result, and 39 of the 45 silent
   servers exited because they need credentials the harness does not supply.

## What is deliberately excluded

`pinning` and `drift` findings are removed from the totals. Both are artefacts
of the method, not properties of the servers: the harness launches every package
without a version, so `pinning` fires on every single one, and no baseline is
supplied, so `drift` fires too. Reporting them would inflate the numbers with
something we caused.

## Why it runs on GitHub Actions

The first attempt ran locally. A package that takes two seconds to fetch on a
runner took eighty on a residential connection in Douala, and the network
dropped twice mid-run. Seventy-one packages became two hours of downloading
with no guarantee of finishing. The workflow is not a convenience — it is the
only way this measurement completes.

## Reproduce

```
gh workflow run survey.yml -f limit=120
```

Results land in `data/run.json` (raw, one entry per server), `data/summary.json`
(aggregate) and `results/` (one scanner report per server, unmodified).
