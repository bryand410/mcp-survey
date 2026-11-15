# What 514 public MCP servers expose to the model

**Measured 15 November 2026.** Scanner: `mcp-scrutiny` at `4307209` (0.1.4),
with the semantic column re-scored at `7ede726` (0.1.5). Catalogue: every npm
package tagged `mcp-server`, `mcp` or `modelcontextprotocol` that has a
measurable weekly download count, ranked by that count. Raw data in
`data/run.json`, every captured tool definition in `data/tools.json`, one
scanner report per server in `results/`.

---

## The numbers

| | |
|---|---|
| packages in the catalogue | 5 062 |
| with a measurable weekly download count | **514 — all of them scanned** |
| servers that answered `initialize` | **265 (52%)** |
| tool definitions inspected | **12 709** |
| findings after excluding harness artefacts | **262** |
| — by severity | 182 high, 72 medium, 8 low |
| — by detector | 165 `toxic_flow`, 97 `semantic` |
| servers carrying a finding | 79 of 265 |

The median server exposes 10 tools. The largest, `crawlora-mcp`, exposes
4 684 — more than a third of the entire sample on its own.

---

## What the 52% means, and what it does not

249 servers never produced a tool list. **223 of them exited with a non-zero
status before replying to `initialize`** — not hung, not crashed, exited. A
server that talks to GitLab needs a GitLab token; one that talks to Confluence
needs a Confluence URL. The harness supplies neither. Ten accepted the
connection and then said nothing within 40 seconds. Sixteen produced no
diagnostic at all.

So the honest reading is *not* "48% of MCP servers are broken". It is:

> **Nearly half of published MCP servers cannot be evaluated without the
> credentials they exist to consume.** Any scanner that reports on them
> without saying so is reporting on its own harness.

That number is also the one this survey nearly got wrong. The first version of
the harness recorded the server's exit status and stderr; a refactor to
capture-and-scan dropped both, and 246 silent servers were filed as "no tool
definitions available" — which describes what the scanner saw, not why the
server never answered. The reason is now parsed from the capture step. See
*What this survey does not establish*.

---

## The 165 toxic flows

Every one is **intra-server**: two tools in the same package compose into a
capability neither has alone.

| combination | count |
|---|---|
| reads credentials or secrets + sends email or messages | 40 |
| executes commands + sends data outbound | 28 |
| executes commands + writes or deletes files | 28 |
| reads credentials or secrets + sends data outbound | 27 |
| reads files + sends data outbound | 24 |
| reads files + modifies a database | 8 |
| reads environment variables + sends data outbound | 5 |
| reads environment variables + sends email or messages | 5 |

**None of these is a vulnerability claim, and the report should not be read as
one.** A Firebase server that can read a service account *and* send mail is a
Firebase server doing its job. The scanner's own detail text says as much:
"Both sides live in the same server, which may well be by design; confirm it."

What the count establishes is narrower and still useful: **66 of the 265
servers that could be inspected expose a combination that would become an
exfiltration path if the model were ever steered.** That is a property of the
design, not of the intent.

---

## The five false positives, and why they matter more than the findings

This is the part worth reading, because it is where the measurement was wrong
five times and the corrections are what the data now rests on.

### 1–2. Two regexes read the wrong grammatical role (71-server run)

The first run produced **four critical findings**. All four were wrong, and
both causes were lexical:

| description fragment | scored | cause |
|---|---|---|
| `not_assessed is never reported as clean` | 1.00 critical | `never report` matched the **passive** — an assurance about output |
| `shares a system prompt or tools` | 1.00 critical | `system prompt` matched the **subject** of a tool that analyses agents |

The first says *this result is never mislabelled as safe*. The second says
*this tool inspects system prompts*. Both were read as *hide this from the
user* and *write into the system prompt*. Fixed in `7858bae`; the first
attempt at the fix stopped detecting `append the following to the system
prompt`, a genuine injection, and a regression test caught it.

### 3. A model probability was mapped to `critical` (250-server run)

The next run produced **75 critical findings**, all semantic. Sampled eight,
read them by hand: zero true positives. A Heroku dyno runner described as
"network and filesystem access"; a fleet tool that works "without asking
permission"; a Premiere timeline predictor.

The code already said *a probability is not a severity* and then mapped
0.95 → CRITICAL. Fixed in `c7079b1`: `critical` now belongs only to evidence
that needs no model — invisible Unicode, a decoded payload, a hidden
recipient. A model score caps at HIGH.

The distinction to keep: **long, technical, imperative prose is what a good
tool description looks like. It is also what the model was trained to
distrust.** Length correlates with technicality, not with intent.

### 4. Chinese prose and emoji read as attacks (514-server run)

482 semantic findings at HIGH. Two causes, both ordinary text:

| what was flagged | why | count |
|---|---|---|
| Chinese/Japanese description containing `ID`, `API`, `v2` | `mixed_script_words` counted any non-Latin script as the "other" half of a homoglyph | 324 |
| any description containing `⚠️` | `U+FE00-FE0F` was in the invisible-Unicode set, and `⚠️` is `U+26A0 U+FE0F` | 91 |

Only Cyrillic and Greek contain Latin lookalikes, so only those count now. A
variation selector follows the character it modifies — that is its only
defined use — so a single one is presentation and a run of four or more is
still reported, which is what smuggling needs. Fixed in `88b945f`.

### 5. A field list read as an encoded payload, and Russian read as a homoglyph

`/` belongs to the base64 alphabet, so
`function/class/method/variable/interface/type/module` cleared the
40-character bar: 25 findings, all documented parameter lists. And
`confusables` returned every Cyrillic character it found regardless of
context, so `mcp-yandex-wordstat`, which documents itself in Russian, produced
five findings whose entire evidence was the Russian alphabet. Fixed in
`4307209` and `7ede726`.

### What the corrections are worth

| | semantic findings |
|---|---|
| before any correction, 250 servers | 482 |
| after the CJK, emoji and field-list fixes, 514 servers | 97 |
| after the Russian-prose fix, same 12 709 descriptions, re-scored | **87** |

The last number is exact rather than estimated: the semantic check is
tool-local, so re-scoring the archived descriptions gives the same answer as
re-scanning, and `data/tools.json` exists precisely so that is true.

**87 is still not a list of 87 attacks.** Sampling it again after the fixes,
eight of eight were ordinary documentation: `POST {"url": "https://..."}` in an
example read as exfiltration, "IMPORTANT: a `warning` in the result means…"
read as concealment, a dataset description read as a hardcoded recipient. The
semantic column is a **triage list**, not a finding set, and the four
deterministic checks above are what makes the rest of the report trustworthy.

A scanner that scores documentation at 1.00 critical is a scanner nobody
leaves switched on. This is the same lesson as the October mobile-money audit:
the false positive found in the tool mattered more than any finding in the
scan.

---

## What this survey does not establish

- **It does not say the MCP ecosystem is clean.** 12 709 tool definitions is
  roughly 0.1% of the repositories tagged `mcp-server` on GitHub. It says
  something about 265 servers that start without credentials.
- **It does not rank scanners.** It measures one scanner against real input,
  including its own five defects.
- **It does not name a malicious server.** None was found. If one had been,
  the maintainer would have been contacted before publication — the same rule
  as the October audit.
- **The semantic column is triage.** 87 findings, sampled eight, all false
  positives. Treat it as a reading order, not as evidence.

## Reproduce

```
gh workflow run survey.yml -f limit=514
```

Each server is captured once (`mcp-scrutiny capture`) and the resulting file is
scanned offline (`mcp-scrutiny scan --tools-json`). The combined capture is
committed as `data/tools.json`, so any detector change can be re-scored on the
exact same 12 709 descriptions without launching a single server again.

Results are committed by the workflow itself.
