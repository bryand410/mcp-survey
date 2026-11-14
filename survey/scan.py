"""Scanne chaque serveur du catalogue et écrit les résultats bruts.

Écrit pour tourner sur un runner GitHub Actions : le réseau y télécharge un
paquet npm en deux secondes, contre quatre-vingts sur une connexion résidentielle
africaine. Le script ne suppose rien de la machine au-delà de `npx`.

Chaque serveur a sa propre config, pour qu'un serveur muet n'empêche pas les
autres d'être scannés. Un résultat brut par serveur dans results/, l'agrégat
dans data/run.json.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DATA = HERE / "data"
WORK = HERE / "work"
RESULTS = HERE / "results"

TIMEOUT = float(os.environ.get("PROBE_TIMEOUT", "40"))
WORKERS = int(os.environ.get("WORKERS", "8"))
LIMIT = int(os.environ.get("LIMIT", "120"))


def slug(name: str) -> str:
    return name.replace("@", "").replace("/", "__").replace(".", "_")


def scan_one(pkg: dict) -> dict:
    name = pkg["name"]
    ident = slug(name)
    cfg = WORK / f"{ident}.json"
    out = RESULTS / f"{ident}.json"

    cfg.write_text(
        json.dumps({"mcpServers": {ident: {"command": "npx", "args": ["-y", name]}}}),
        encoding="utf-8",
    )

    started = time.time()
    try:
        subprocess.run(
            [
                sys.executable, "-m", "mcp_scrutiny", "scan",
                "--config", str(cfg),
                "--probe", "--timeout", str(TIMEOUT),
                "--format", "json", "--output", str(out),
                "--no-color", "--fail-on", "none",
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT + 120,
        )
    except subprocess.TimeoutExpired:
        pass

    if not out.exists():
        return {
            "package": name,
            "status": "no-report",
            "seconds": round(time.time() - started, 1),
        }

    report = json.loads(out.read_text(encoding="utf-8"))
    tools = sum(s.get("tools", 0) for s in report.get("servers", []))
    return {
        "package": name,
        "status": "ok" if tools else "no-tools",
        "seconds": round(time.time() - started, 1),
        "tools": tools,
        "errors": report.get("errors", []),
        "findings": report.get("findings", []),
        "servers": report.get("servers", []),
    }


def main() -> int:
    WORK.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)

    catalog = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    targets = [p for p in catalog if p.get("weekly_downloads", 0) > 0][:LIMIT]
    print(f"cibles : {len(targets)} | timeout {TIMEOUT}s | {WORKERS} en parallèle", flush=True)

    done = 0

    def run(pkg: dict) -> dict:
        nonlocal done
        result = scan_one(pkg)
        done += 1
        mark = "OK " if result["status"] == "ok" else "-- "
        print(
            f"[{done:>3}/{len(targets)}] {mark}{pkg['name']:<44} "
            f"tools={result.get('tools', 0):<4} {result['seconds']}s",
            flush=True,
        )
        return result

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(run, targets))

    (DATA / "run.json").write_text(
        json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8"
    )

    ok = [r for r in results if r["status"] == "ok"]
    print(
        f"\n{len(ok)}/{len(results)} ont répondu ({100 * len(ok) / max(len(results), 1):.0f}%)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
