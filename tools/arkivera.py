#!/usr/bin/env python3
"""Fyll i källa.arkiv med en arkivkopia i Wayback Machine för poster som saknar en.

    python tools/arkivera.py            # högst 20 källor per körning
    python tools/arkivera.py --max 50
    python tools/arkivera.py BID-24 BID-25   # bara vissa poster, direkt när de skrivs

Finns en kopia redan används den närmaste kopian från det datum källan hämtades. Annars
begärs en ny kopia. Går det inte (en del sajter blockerar Wayback Machine) används den senaste
kopian i archive.today, om det finns någon. Körs varje vecka av .github/workflows/arkivera.yml.
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "belagt-arkivering (+https://github.com/pauseai-sverige/belagt)"}


def hämta(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace"), r.geturl()


def befintlig(url, datum):
    tid = (datum or "").replace("-", "")
    q = urllib.parse.urlencode({"url": url, "timestamp": tid})
    text, _ = hämta(f"https://archive.org/wayback/available?{q}")
    snap = json.loads(text).get("archived_snapshots", {}).get("closest")
    return snap["url"].replace("http://", "https://", 1) if snap and snap.get("available") else None


def ny(url, försök=2):
    for i in range(försök):
        try:
            _, slut = hämta(f"https://web.archive.org/save/{url}", timeout=180)
            if "/web/" in slut:
                return slut
        except Exception:
            if i == försök - 1:
                raise
        time.sleep(30)
    return None


def archive_today(url):
    """Senaste kopian i archive.today. Att skapa nya kopior där kräver en människa (captcha),
    så skriptet bara letar upp befintliga."""
    try:
        _, slut = hämta(f"https://archive.ph/newest/{url}")
    except Exception:
        return None
    return slut if re.match(r"^https://archive\.(ph|today|is|md|li|vn|fo)/\w+$", slut) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id", nargs="*")
    ap.add_argument("--max", type=int, default=20)
    a = ap.parse_args()
    klara, cache = 0, {}
    for f in sorted((ROOT / "påståenden").glob("*/*.yaml")):
        text = f.read_text()
        p = yaml.safe_load(text)
        k = p["källa"]
        if k["arkiv"] or (a.id and p["id"] not in a.id):
            continue
        if k["url"] not in cache:
            if klara >= a.max:
                continue
            try:
                cache[k["url"]] = befintlig(k["url"], k["hämtad"]) or ny(k["url"])
            except Exception as e:  # nätverksfel, blockering eller hastighetsgräns
                print(f"{p['id']}: Wayback Machine: {e}")
                cache[k["url"]] = None
            # Reserv: archive.today. Annars försöker skriptet igen nästa vecka.
            cache[k["url"]] = cache[k["url"]] or archive_today(k["url"])
            klara += 1
            time.sleep(5)
        if cache[k["url"]]:
            # Byt bara raden, så att resten av filen står orörd i diffen.
            f.write_text(text.replace("  arkiv: null\n", f"  arkiv: {cache[k['url']]}\n", 1))
            print(f"{p['id']}: {cache[k['url']]}")


if __name__ == "__main__":
    main()
