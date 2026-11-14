"""Agrège les résultats bruts en un tableau lisible et vérifiable.

Deux détecteurs sont exclus du décompte, et il faut le dire plutôt que le
cacher : `pinning` signale l'absence de version dans *nos* configs de test —
c'est notre méthode, pas un défaut des serveurs ; `drift` signale l'absence de
baseline, vraie par construction puisqu'on scanne chaque serveur une seule fois.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DATA = HERE / "data"

EXCLUDED = {"pinning", "drift"}
ORDER = ["info", "low", "medium", "high", "critical"]


def main() -> int:
    run = json.loads((DATA / "run.json").read_text(encoding="utf-8"))

    answered = [r for r in run if r["status"] == "ok"]
    silent = [r for r in run if r["status"] != "ok"]

    print(f"serveurs testés    : {len(run)}")
    print(f"ont répondu        : {len(answered)} ({100 * len(answered) / max(len(run), 1):.0f}%)")
    print(f"muets ou en échec  : {len(silent)}")

    total_tools = sum(r.get("tools", 0) for r in answered)
    print(f"outils inspectés   : {total_tools}")

    by_detector: Counter[str] = Counter()
    by_severity: Counter[str] = Counter()
    flagged: dict[str, list[dict]] = defaultdict(list)

    for result in answered:
        for finding in result.get("findings", []):
            if finding["detector"] in EXCLUDED:
                continue
            by_detector[finding["detector"]] += 1
            by_severity[finding["severity"]] += 1
            flagged[result["package"]].append(finding)

    print(f"\nfindings (hors {', '.join(sorted(EXCLUDED))}) : {sum(by_detector.values())}")
    print("  par sévérité :", dict(by_severity) or "aucun")
    print("  par détecteur:", dict(by_detector) or "aucun")

    if flagged:
        print(f"\nserveurs porteurs de findings : {len(flagged)}")
        for package, findings in flagged.items():
            worst = max((f["severity"] for f in findings), key=ORDER.index)
            print(f"  {package:<44} {worst:<8} {len(findings)} finding(s)")
            for finding in findings[:3]:
                print(f"      - [{finding['severity']}] {finding['detector']}: {finding['title'][:80]}")

    print(f"\nserveurs muets ({len(silent)}) :")
    for result in silent[:20]:
        reason = (result.get("errors") or ["sans rapport"])[0]
        print(f"  {result['package']:<44} {str(reason)[:70]}")

    summary = {
        "tested": len(run),
        "answered": len(answered),
        "silent": len(silent),
        "tools": total_tools,
        "findings_excluding": sorted(EXCLUDED),
        "by_severity": dict(by_severity),
        "by_detector": dict(by_detector),
        "flagged_servers": {
            package: [
                {"severity": f["severity"], "detector": f["detector"], "title": f["title"]}
                for f in findings
            ]
            for package, findings in flagged.items()
        },
        "silent_servers": [
            {"package": r["package"], "reason": str((r.get("errors") or [""])[0])[:160]}
            for r in silent
        ],
    }
    (DATA / "summary.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print("\nécrit : data/summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
