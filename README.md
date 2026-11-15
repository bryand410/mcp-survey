# mcp-survey

What the most-installed public MCP servers actually expose to the model.

Most scanners in this space publish benchmarks against synthetic fixtures. This
one runs against the real catalogue and publishes what comes back, including
its own defects.

**Read the report: [What 514 public MCP servers expose to the model](docs/2026-11-public-mcp-survey.md)**

---

## The result in one table

| | |
|---|---|
| packages in the catalogue | 5 062 |
| with a measurable weekly download count | 514 — **all scanned** |
| servers that answered `initialize` | 265 (52%) |
| tool definitions inspected | 12 709 |
| findings after excluding harness artefacts | 262 — 182 high, 72 medium, 8 low |
| — structural (`toxic_flow`, intra-server) | 165, across 66 servers |
| — semantic (triage only, see below) | 97 |
| critical findings | 4 in the first run, **all false positives**, fixed |

## Method

1. **Catalogue** — npm packages tagged `mcp-server`, `mcp` or
   `modelcontextprotocol`, paged until the registry is exhausted, then ranked
   by real weekly download counts rather than by the registry's popularity
   score. That score saturates at 1.000 for hundreds of packages and therefore
   ranks nothing. 5 062 packages; 514 have a measurable install base.
2. **Capture** — each server is started once through `npx -y <package>`,
   exactly as a client would start it, and asked for its tool list. The
   definitions are written to disk.
3. **Scan** — the captured file is scanned offline. This is not a convenience:
   it halves the probing cost and it makes the measurement re-scorable, so a
   detector change can be applied to the same 12 709 descriptions without
   launching a server again.
4. **Measure** — a server that never answers is recorded as silent, never
   dropped. The response rate is part of the result, and **223 of the 249
   silent servers exited because they need credentials the harness does not
   supply.**

## Read the semantic column as triage, not as findings

The deterministic checks are the load-bearing part: toxic flows, cross-server
shadowing, invisible Unicode, decoded payloads, hidden recipients. The trained
model is a reading order.

Five separate false-positive classes were found by reading its output, and the
report documents each with its measured effect: a regex matching the passive
("never reported as clean"), a model probability mapped to `critical`, Chinese
prose containing "ID", emoji carrying `U+FE0F`, field lists matching the base64
alphabet, and Russian prose flagged as homoglyphs. Together they took the
semantic count from 482 to 87 on the same corpus.

Sampled again after those fixes, eight of eight remaining findings were
ordinary documentation. That is stated in the report rather than smoothed over.

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
gh workflow run survey.yml -f limit=514
```

Results land in `data/run.json` (raw, one entry per server), `data/summary.json`
(aggregate), `data/tools.json` (every captured tool definition, 16 MB) and
`results/` (one scanner report per server, unmodified).
