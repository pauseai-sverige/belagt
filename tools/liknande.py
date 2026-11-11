#!/usr/bin/env python3
"""Lista aktuella poster som kan beröras av en ny post: samma avsändare eller samma källa.

    python tools/liknande.py BID-24 BID-25

Används när en post skrivs, för att se om den är en dubblett eller om den ersätter en äldre
post (en ny mätning, ett ändrat beslut, en preprint som har publicerats). Den äldre posten får
då ersatt_av. Skriver en lista per post, eller ingenting om inget liknar.
"""
import re
import sys
from pathlib import Path

import yaml

from regler import värd

ROOT = Path(__file__).resolve().parent.parent


def avsändare(p):
    return re.split(r"[,(]", p["vem"])[0].strip().lower()


def main():
    poster = {p["id"]: p for p in (yaml.safe_load(f.read_text()) for f in (ROOT / "påståenden").glob("*/*.yaml"))}
    for pid in sys.argv[1:]:
        ny = poster[pid]
        lika = [p for p in poster.values() if p["id"] != pid and not p["ersatt_av"] and (
            avsändare(p) == avsändare(ny) or p["källa"]["url"] == ny["källa"]["url"]
            or (värd(p["källa"]["url"]) == värd(ny["källa"]["url"]) and set(p["tema"]) & set(ny["tema"])
                and p["typ"] == ny["typ"]))]
        if not lika:
            continue
        print(f"\n{pid} ({ny['datum']}, {ny['typ']}): {ny['påstående']}")
        for p in sorted(lika, key=lambda p: p["datum"], reverse=True):
            print(f"  {p['id']} ({p['datum']}, {p['typ']}): {p['påstående']}")


if __name__ == "__main__":
    main()
