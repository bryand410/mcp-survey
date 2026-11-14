"""Construit le catalogue complet : tout le registre npm, filtré, classé.

La recherche npm renvoie au plus 250 résultats par requête. Les trois premiers
appels donnaient 704 paquets uniques ; le registre en contient 11 510 pour le
seul mot-clé `mcp-server`. Ce script pagine jusqu'à épuisement, puis classe par
téléchargements réels.

Deux filtres, tous deux conservateurs :

* le nom ne doit pas être de l'outillage (`sdk`, `client`, `transport`, ...) ;
* la description doit dire qu'il s'agit d'un serveur MCP.

Un faux positif coûte un lancement de serveur ; un faux négatif coûte un
serveur absent de l'échantillon. On préfère donc inclure large ici et laisser
le scan trancher — c'est lui qui dira si le paquet répond au protocole.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent.parent
DATA = HERE / "data"

KEYWORDS = ("mcp-server", "mcp", "modelcontextprotocol")
PAGE = 250
MAX_PAGES = int(os.environ.get("MAX_PAGES", "40"))
DOWNLOAD_WORKERS = int(os.environ.get("DOWNLOAD_WORKERS", "32"))

NOT_A_SERVER = re.compile(
    r"(?:^|[-/@])(sdk|client|transport|transports|types|type-defs|core|protocol|"
    r"inspector|ui|web-ui|proxy|gateway|framework|template|boilerplate|generator|"
    r"scaffold|utils|common|shared|registry|spec|schema|test|example)(?:$|[-/])",
    re.IGNORECASE,
)

LOOKS_LIKE_SERVER = re.compile(
    r"\b(mcp|model context protocol)\b.{0,40}\b(server|serveur)\b"
    r"|\b(server|serveur)\b.{0,40}\b(mcp|model context protocol)\b",
    re.IGNORECASE | re.DOTALL,
)

SDK_SCOPE = "@modelcontextprotocol/"


def get_json(url: str, attempts: int = 3) -> dict | None:
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"Accept": "application/json"})
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read())
        except (HTTPError, URLError, OSError, ValueError):
            time.sleep(1.5 * (attempt + 1))
    return None


def search(keyword: str) -> list[dict]:
    """Pagine la recherche jusqu'à épuisement ou jusqu'à MAX_PAGES."""
    out: list[dict] = []
    for page in range(MAX_PAGES):
        url = (
            "https://registry.npmjs.org/-/v1/search"
            f"?text=keywords:{quote(keyword)}&size={PAGE}&from={page * PAGE}"
        )
        blob = get_json(url)
        if not blob:
            print(f"   {keyword}: arrêt page {page} (pas de réponse)", flush=True)
            break
        objects = blob.get("objects") or []
        if not objects:
            break
        out.extend(objects)
        total = blob.get("total")
        print(
            f"   {keyword}: page {page + 1}, {len(out)}/{total} paquets",
            flush=True,
        )
        if len(out) >= (total or 0):
            break
    return out


def downloads(name: str) -> int:
    url = "https://api.npmjs.org/downloads/point/last-week/" + quote(name, safe="")
    blob = get_json(url, attempts=2)
    if not blob:
        return 0
    try:
        return int(blob.get("downloads") or 0)
    except (TypeError, ValueError):
        return 0


def main() -> int:
    DATA.mkdir(exist_ok=True)
    packages: dict[str, dict] = {}

    for keyword in KEYWORDS:
        print(f"recherche « {keyword} »", flush=True)
        for obj in search(keyword):
            pkg = obj.get("package") or {}
            name = pkg.get("name")
            if not name:
                continue
            if name in packages:
                continue
            packages[name] = {
                "name": name,
                "version": pkg.get("version"),
                "description": (pkg.get("description") or "").strip(),
                "score": (obj.get("score") or {}).get("final", 0.0),
                "date": pkg.get("date"),
                "links": pkg.get("links", {}),
            }

    print(f"\npaquets uniques vus : {len(packages)}", flush=True)

    kept, dropped_tool, dropped_desc, dropped_scope = [], 0, 0, 0
    for name, pkg in packages.items():
        bare = name.split("/")[-1]
        if name.startswith(SDK_SCOPE) and not name.startswith(SDK_SCOPE + "server-"):
            dropped_scope += 1
            continue
        if NOT_A_SERVER.search(bare):
            dropped_tool += 1
            continue
        if not LOOKS_LIKE_SERVER.search(pkg["description"]):
            dropped_desc += 1
            continue
        kept.append(pkg)

    print(f"retenus             : {len(kept)}")
    print(f"  écartés outillage : {dropped_tool}")
    print(f"  écartés SDK       : {dropped_scope}")
    print(f"  écartés (pas de description de serveur) : {dropped_desc}", flush=True)

    print(f"\ntéléchargements hebdomadaires pour {len(kept)} paquets", flush=True)
    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
        counts = list(pool.map(lambda p: downloads(p["name"]), kept))

    for pkg, count in zip(kept, counts):
        pkg["weekly_downloads"] = count

    kept.sort(key=lambda p: (-p["weekly_downloads"], p["name"]))

    measurable = [p for p in kept if p["weekly_downloads"] > 0]
    print(f"\navec un volume mesurable : {len(measurable)}")
    print("20 premiers :")
    for pkg in kept[:20]:
        print(f"  {pkg['weekly_downloads']:>9,}  {pkg['name']:<44} {(pkg['description'] or '')[:44]}")

    (DATA / "catalog.json").write_text(
        json.dumps(kept, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nécrit : {DATA / 'catalog.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
