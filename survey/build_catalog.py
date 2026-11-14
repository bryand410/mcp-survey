"""Construit un catalogue de serveurs MCP npm réellement lançables.

Entrée  : data/npm_*.json (résultats de recherche du registre npm)
Sortie  : data/catalog.json

Le filtre est volontairement conservateur. Un faux positif coûte un
téléchargement npx de 30 secondes ; un faux négatif coûte un serveur manquant
dans l'échantillon. On préfère donc inclure large ici et laisser le scan
trancher — c'est lui qui dira si le paquet répond au protocole.
"""

from __future__ import annotations

import glob
import json
import re
from pathlib import Path

DATA = Path(__file__).parent / "data"

# Paquets qui sont de l'outillage autour de MCP, pas des serveurs.
NOT_A_SERVER = re.compile(
    r"(?:^|[-/@])(sdk|client|transport|transports|types|type-defs|core|protocol|"
    r"inspector|ui|web-ui|proxy|gateway|framework|template|boilerplate|generator|"
    r"scaffold|utils|common|shared|registry|spec|schema|test|example)(?:$|[-/])",
    re.IGNORECASE,
)

# La description doit dire, d'une façon ou d'une autre, que c'est un serveur MCP.
LOOKS_LIKE_SERVER = re.compile(
    r"\b(mcp|model context protocol)\b.{0,40}\b(server|serveur)\b"
    r"|\b(server|serveur)\b.{0,40}\b(mcp|model context protocol)\b",
    re.IGNORECASE | re.DOTALL,
)


def load() -> dict[str, dict]:
    packages: dict[str, dict] = {}
    for path in sorted(glob.glob(str(DATA / "npm_*.json"))):
        blob = json.loads(Path(path).read_text(encoding="utf-8"))
        for obj in blob.get("objects", []):
            pkg = obj["package"]
            name = pkg["name"]
            if name in packages:
                # On garde le meilleur score rencontré.
                packages[name]["score"] = max(
                    packages[name]["score"], obj.get("score", {}).get("final", 0.0)
                )
                continue
            packages[name] = {
                "name": name,
                "version": pkg.get("version"),
                "description": (pkg.get("description") or "").strip(),
                "score": obj.get("score", {}).get("final", 0.0),
                "popularity": obj.get("score", {}).get("detail", {}).get("popularity", 0.0),
                "date": pkg.get("date"),
                "links": pkg.get("links", {}),
            }
    return packages


def main() -> int:
    packages = load()
    print(f"paquets uniques vus      : {len(packages)}")

    kept: list[dict] = []
    rejected: dict[str, int] = {"outillage": 0, "pas de description de serveur": 0}

    for name, pkg in packages.items():
        bare = name.split("/")[-1]
        if NOT_A_SERVER.search(bare):
            rejected["outillage"] += 1
            continue
        if not LOOKS_LIKE_SERVER.search(pkg["description"]):
            rejected["pas de description de serveur"] += 1
            continue
        kept.append(pkg)

    kept.sort(key=lambda p: (-p["popularity"], -p["score"], p["name"]))

    print(f"retenus                  : {len(kept)}")
    for reason, count in rejected.items():
        print(f"  écartés ({reason}) : {count}")

    out = DATA / "catalog.json"
    out.write_text(json.dumps(kept, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nécrit : {out}")
    print("\n20 premiers :")
    for pkg in kept[:20]:
        print(f"  {pkg['popularity']:.3f}  {pkg['name']:<45} {(pkg['description'] or '')[:55]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
