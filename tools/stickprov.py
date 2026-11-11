#!/usr/bin/env python3
"""Lotta ut maskinellt granskade poster som en människa ska läsa mot källan.

    python tools/stickprov.py            # 5 poster
    python tools/stickprov.py --antal 10

Poster med granskning: maskinell har kontrollerats av citatkontrollen och av en oberoende
AI-session, men inte av en människa. Varje vecka lottas några ut. En post som håller får
granskning: människa och kommer inte med i lotten igen. Skriver markdown till stdout, eller
ingenting om det inte finns något att lotta. Körs av .github/workflows/stickprov.yml.
"""
import argparse
import datetime
import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/pauseai-sverige/belagt/blob/main/"
SIDA = "https://pauseai-sverige.github.io/belagt/"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--antal", type=int, default=5)
    ap.add_argument("--idag", default=datetime.date.today().isoformat())
    a = ap.parse_args()
    poster = [yaml.safe_load(f.read_text()) for f in sorted((ROOT / "påståenden").glob("*/*.yaml"))]
    lott = [p for p in poster if p.get("granskning") == "maskinell"]
    if not lott:
        return
    # Samma dag ger samma urval, så att en omkörning inte byter ut listan.
    urval = random.Random(a.idag).sample(lott, min(a.antal, len(lott)))
    ut = [f"Lottat {a.idag} bland {len(lott)} poster som bara är maskinellt granskade.\n",
          "Läs varje post mot källan: bär citatet påståendet, stämmer avsändare, datum och källtyp, och "
          "saknas något förbehåll?\n",
          "- **Håller:** ändra `granskning: maskinell` till `granskning: människa` i posten och kryssa i här.",
          "- **Håller inte:** öppna ett ärende med mallen *Fel i en post* och skriv vad som är fel. "
          "Skriv också här vilken sorts fel det var, så att granskningsinstruktionen i `agent/granskning.md` "
          "kan skärpas.\n"]
    for p in sorted(urval, key=lambda p: p["id"]):
        f = f"påståenden/{p['datum'][:4]}/{p['id']}.yaml"
        ut.append(f"- [ ] **[{p['id']}]({SIDA}#{p['id']})** ([fil]({REPO}{f})): {p['påstående']}  \n"
                  f"  Citat: ”{p['källa']['citat']}”  \n  Källa: {p['källa']['url']}")
    print("\n".join(ut))


if __name__ == "__main__":
    main()
