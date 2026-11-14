# What 71 public MCP servers expose to the model

**Measured 14 November 2026.** Scanner: `mcp-scrutiny` at `7858bae`.
Catalogue: npm packages tagged `mcp-server`, `mcp` or `modelcontextprotocol`,
ranked by real weekly downloads. Raw data in `data/run.json`, one scanner
report per server in `results/`.

---

## The numbers

| | |
|---|---|
| servers launched | 71 |
| servers that answered `initialize` | **26 (37%)** |
| tool definitions inspected | **420** |
| findings after excluding harness artefacts | **10** |
| — by severity | 7 high, 3 medium |
| — by detector | 10 `toxic_flow`, **0 `semantic`** |
| servers carrying a finding | 7 of 26 |

The busiest server in the sample, `@leonio/kern-ux-mcp`, exposes 57 tools.
The median is 17.

---

## What the 37% means, and what it does not

45 servers never answered. **39 of them exited with a non-zero status before
replying to `initialize`** — not hung, not crashed, exited. A server that talks
to GitLab needs a GitLab token; one that talks to Confluence needs a
Confluence URL. The harness supplies neither.

So the honest reading is *not* "63% of MCP servers are broken". It is:

> **A majority of published MCP servers cannot be evaluated without the
> credentials they exist to consume.** Any scanner that reports on them without
> saying so is reporting on its own harness.

Three servers accepted the connection and then said nothing within 40 seconds.
Two produced no report at all. Both are counted as silent, never dropped.

---

## The ten findings

Every finding is `toxic_flow`, and every one is **intra-server**: two tools in
the same package compose into a capability neither has alone.

| server | combination | severity |
|---|---|---|
| `gamealia-mcp` | executes commands + sends data outbound | high |
| `gamealia-mcp` | reads credentials + sends messages | high |
| `gamealia-mcp` | reads credentials + sends data outbound | high |
| `gamealia-mcp` | executes commands + writes or deletes | medium |
| `echelongraph-mcp` | executes commands + sends data outbound | high |
| `echelongraph-mcp` | reads files + sends data outbound | medium |
| `@growthbook/mcp` | executes commands + sends data outbound | high |
| `@leonio/kern-ux-mcp` | reads credentials + sends messages | high |
| `@kunal_dutt/token-lens` | reads credentials + sends messages | high |
| `@mozilla/firefox-devtools-mcp-moz` | executes commands + sends data outbound | medium |

**None of these is a vulnerability claim, and the report should not be read as
one.** A GrowthBook server that can run a query *and* reach its API is a
GrowthBook server doing its job. The scanner's own detail text says as much:
"Both sides live in the same server, which may well be by design; confirm it."

What the count establishes is narrower and still useful: **seven of the
twenty-six servers that could be inspected expose a combination that would
become an exfiltration path if the model were ever steered.** That is a
property of the design, not of the intent.

Zero cross-server flows were found. With 26 servers in the sample and no shared
capability pairs across packages, that is the expected result rather than a
reassuring one.

---

## The four false positives, and why they matter more than the findings

The first run of this survey produced **four critical findings**. All four were
wrong. They came from two regular expressions, not from the statistical model,
and both had the same defect: a word list written for one grammatical role
matched the opposite role.

| description fragment | scored | cause |
|---|---|---|
| `not_assessed is never reported as clean` | 1.00 critical | `never report` matched the **passive** — an assurance about output |
| `a count of 0 … is never reported as not affected` | 1.00 critical | same |
| `shares a system prompt or tools` | 1.00 critical | `system prompt` matched the **subject** of a tool that analyses agents |
| `where an agent's tokens go (system prompt, tools…)` | 1.00 critical | same |

The first says *this result is never mislabelled as safe*. The second says
*this tool inspects system prompts*. Both were read as *hide this from the
user* and *write into the system prompt*.

Fixed in `mcp-scrutiny@7858bae`. The patterns now refuse the passive
(`never reported as <state>`) and require a verb that moves text *into* the
prompt, allowing the complement to sit a few words away. Measured after the
fix:

```
am_i_affected      p 1.00 -> 0.03
workload_triage    p 1.00 -> 0.01
optimize_agent     p 1.00 -> 0.03
real injection     p 1.00 -> 1.00
```

The first attempt at the fix stopped detecting `append the following to the
system prompt`, a genuine injection. A regression test caught it. Three tests
now pin both directions.

This is the same lesson as the mobile-money audit: **the false positive found
in the tool mattered more than any finding in the scan.** A scanner that scores
documentation at 1.00 critical is a scanner nobody leaves switched on.

---

## What this survey does not establish

- **It does not say the MCP ecosystem is clean.** 420 tool definitions is
  0.02% of the 43 428 GitHub repositories tagged `mcp-server`. It says
  something about 26 servers that start without credentials.
- **It does not rank scanners.** It measures one scanner against real input,
  including its own defects.
- **It does not name a malicious server.** None was found. If one had been,
  the maintainer would have been contacted before publication — the same rule
  as the October audit.

## Reproduce

```
gh workflow run survey.yml -f limit=120
```

Results are committed by the workflow itself.
