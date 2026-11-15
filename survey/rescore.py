"""Re-score the captured corpus offline, one server at a time.

Why this file exists
--------------------
The first re-scores of the 12 709 descriptions were run two ways that both
produced numbers, and only one of them was comparable to the published scan:

1. **All servers in a single ``scan()`` call.** The ``shadowing`` detector
   compares tool names *across* servers, so merging 265 servers into one
   ScanResult invents collisions that no client would ever see, and
   ``_cross_references`` fires on the phrase "the tool" in ordinary
   documentation. That run reported 11 339 shadowing findings on a corpus
   where the real scan reported none. The numbers were not wrong because the
   detector was broken; they were wrong because the corpus shape changed.

2. **A stale checkout.** One run reported ``mcp-scrutiny 0.1.2`` while the
   fixes under test landed in 0.1.7, so it measured the bug it was meant to
   prove fixed.

Both are the same mistake in different clothes: the measurement stopped being
the published one. This script makes the comparison exact — same corpus, same
per-server shape, same detector set, and the version of the scanner that
produced the numbers is recorded in the output.

Usage::

    python survey/rescore.py --tools-json data/tools.json --out /tmp/rescore.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from mcp_scrutiny import __version__
from mcp_scrutiny.detectors import get_detectors
from mcp_scrutiny.model import load_default_model
from mcp_scrutiny.scanner import load_tool_dump, scan


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tools-json", default="data/tools.json")
    ap.add_argument("--out", default="rescore.json")
    ap.add_argument(
        "--disable",
        default="drift,pinning",
        help="detectors to skip; drift has no baseline offline and pinning "
        "reads the launch command, which the dump does not carry",
    )
    args = ap.parse_args()

    servers = load_tool_dump(args.tools_json)
    model = load_default_model()
    detectors = get_detectors(disable=[d for d in args.disable.split(",") if d])

    findings: list[dict] = []
    per_server: list[dict] = []
    errors: list[str] = []

    for index, server in enumerate(servers, 1):
        # One server per scan. This is the shape the published run used and the
        # only shape in which cross-server detectors mean what they claim.
        result = scan([server], model=model, detectors=detectors)
        errors.extend(result.errors)
        per_server.append(
            {
                "server": server.name,
                "tools": len(server.tools),
                "findings": len(result.findings),
            }
        )
        for finding in result.findings:
            findings.append(finding.to_dict() if hasattr(finding, "to_dict") else vars(finding))
        if index % 25 == 0:
            print(f"  {index}/{len(servers)} servers, {len(findings)} findings", flush=True)

    by_detector = Counter(f.get("detector") for f in findings)
    by_severity = Counter(f.get("severity") for f in findings)
    payload = {
        "tool": {"name": "mcp-scrutiny", "version": __version__},
        "corpus": args.tools_json,
        "method": "one scan() call per server, detectors: "
        + ", ".join(d.name for d in detectors),
        "summary": {
            "servers": len(servers),
            "tools": sum(len(s.tools) for s in servers),
            "findings": len(findings),
            "by_severity": dict(by_severity),
            "by_detector": dict(by_detector),
            "flagged_servers": sum(1 for s in per_server if s["findings"]),
        },
        "servers": per_server,
        "findings": findings,
        "errors": errors,
    }
    Path(args.out).write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))
    print(f"written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
