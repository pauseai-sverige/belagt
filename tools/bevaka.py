#!/usr/bin/env python3
"""Lista det som är nytt i de bevakade källorna (bevakning.yaml).

    python tools/bevaka.py              # det som publicerats de senaste 8 dagarna
    python tools/bevaka.py --dagar 30

Skriver markdown till stdout, eller ingenting om inget är nytt. Länkar som redan är källor i
arkivet hoppas över. Körs varje vecka av .github/workflows/bevaka.yml, som lägger listan i ett
ärende. Det som listas är tips: en post skrivs bara när primärkällan har hämtats och ett ordagrant
citat bekräftar påståendet.

Sist i listan står källänkar på pauseai.se som inte finns i arkivet, så att sajtens egna
påståenden efter hand blir kontrollerade här.
"""
import argparse
import datetime
import email.utils
import gzip
import io
import json
import re
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import yaml

from regler import blockerad, värd

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (compatible; belagt-bevakning; +https://github.com/pauseai-sverige/belagt)"}
ATOM = "{http://www.w3.org/2005/Atom}"
MAX_PER_KÄLLA = 15
SITEMAP = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
# Källor med kräv_ai: true tar bara med poster där något av orden står i titeln.
AI_ORD = re.compile(r"\b(AI|KI|A\.I\.|AGI)\b|artificiell intelligens|artificial intelligence|kunstig intelligens"
                    r"|maskininlärning|machine learning|språkmodell|language model|chatbot|chattbot|generativ",
                    re.IGNORECASE)
# Riksdagsdokument som kan bära ett påstående. Protokoll, dagordningar och EU-dokument hoppas över.
RIKSDAGSTYPER = {"mot", "ip", "fr", "frs", "prop", "sou", "ds", "dir", "bet", "skr", "rir"}
MAX_TECKEN = 60000  # GitHub tar högst 65 536 tecken i ett ärende


def hämta(url, timeout=60, försök=2):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
    except (urllib.error.URLError, TimeoutError) as e:
        # Tillfälliga fel (till exempel 503 från news.google.com) får ett nytt försök.
        if försök <= 1 or (isinstance(e, urllib.error.HTTPError) and e.code < 500):
            raise
        time.sleep(10)
        return hämta(url, timeout, försök - 1)
    # deepmind.google skickar gzip även när ingen har bett om det
    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data


def datum(s):
    """Tolka datum i RSS (RFC 822), Atom (ISO 8601) och riksdagens format (ÅÅÅÅ-MM-DD)."""
    if not s:
        return None
    s = s.strip()
    try:
        return email.utils.parsedate_to_datetime(s).date()
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return datetime.date.fromisoformat(s[:10])
    except ValueError:
        return None


def text(el, *namn):
    for n in namn:
        hit = el.find(n)
        if hit is not None and (hit.text or "").strip():
            return " ".join(hit.text.split())
    return ""


def läs_flöde(data, kategorier=None):
    """Poster ur ett RSS- eller Atom-flöde som (titel, länk, datum).

    Med kategorier tas bara RSS-poster med någon av de kategorierna med."""
    rot = ET.fromstring(data)
    for item in rot.iter("item"):  # RSS
        källa = item.find("source")  # Google News anger den egentliga sajten här
        if källa is not None and blockerad(källa.get("url")):
            continue
        if kategorier and not {c.text for c in item.findall("category")} & set(kategorier):
            continue
        yield text(item, "title"), text(item, "link"), datum(text(item, "pubDate", "{http://purl.org/dc/elements/1.1/}date"))
    for entry in rot.iter(f"{ATOM}entry"):  # Atom
        länk = next((l.get("href") for l in entry.findall(f"{ATOM}link") if l.get("rel") in (None, "alternate")), "")
        yield text(entry, f"{ATOM}title"), länk, datum(text(entry, f"{ATOM}published", f"{ATOM}updated"))


def läs_sitemap(data, sökvägar=None):
    """Sidor ur en sitemap som (titel, länk, datum), för sajter utan flöde. Datumet är när sidan
    senast ändrades, så en gammal sida som har rättats kan dyka upp igen. Titeln saknas i en
    sitemap och tas ur adressen."""
    for u in ET.fromstring(data).iter(f"{SITEMAP}url"):
        länk = text(u, f"{SITEMAP}loc")
        väg = urllib.parse.urlparse(länk).path
        if sökvägar and not any(väg.startswith(s) and väg.rstrip("/") != s.rstrip("/") for s in sökvägar):
            continue
        titel = väg.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").capitalize()
        yield titel, länk, datum(text(u, f"{SITEMAP}lastmod"))


SAJT = "https://codeload.github.com/pauseai-sverige/pauseai-se/tar.gz/refs/heads/main"
LÄNK_RE = re.compile(r"https?://[^\s)\"'<>\]]+")
MAX_SAJTLÄNKAR = 10
# Sidor med sakpåståenden om AI. Sidor om att engagera sig, evenemang och insatser länkar till
# verktyg och kampanjer, inte till källor.
SAJTSIDOR = re.compile(r"src/(content/(laget|blogg)/|content/sidor/(?!engagera-dig|donera|protester|om-oss|upprop)"
                       r"|pages/(index|mejla)\.astro)")
# Länkar på sajten som inte är källor för sakpåståenden: egna sidor, sociala medier, verktyg,
# uppslagsverk och arkiv.
INTE_KÄLLA = {"pauseai.se", "pauseai.info", "lu.ma", "luma.com", "github.com", "github.io", "youtube.com", "youtu.be",
              "youtube-nocookie.com", "x.com", "twitter.com", "facebook.com", "instagram.com", "tiktok.com",
              "linkedin.com", "discord.gg", "whatsapp.com", "wikipedia.org", "archive.org", "archive.ph",
              "google.com", "creativecommons.org", "w3.org", "schema.org", "goatcounter.com", "riksdagen.se",
              "astro.build", "pagescms.org", "zod.dev"}


def jämförbar(url):
    """Adressen utan textfragment, www, avslutande snedstreck och arXiv-version."""
    url = url.split("#")[0].rstrip("/").replace("http://", "https://", 1).replace("://www.", "://", 1)
    return re.sub(r"(arxiv\.org/(?:abs|pdf)/[\d.]+)v\d+$", r"\1", url)


def sajtlänkar(kända):
    """Källänkar på pauseai.se som inte är källa i någon post, som (sida, länk)."""
    kända = {jämförbar(u) for u in kända}
    ut, sedda = [], set()
    with tarfile.open(fileobj=io.BytesIO(hämta(SAJT)), mode="r:*") as tar:  # hämta() har redan packat upp gzip
        for m in sorted(tar.getmembers(), key=lambda m: m.name):
            väg = m.name.split("/", 1)[-1]
            if not m.isfile() or not SAJTSIDOR.match(väg):
                continue
            for länk in LÄNK_RE.findall(tar.extractfile(m).read().decode("utf-8", "replace")):
                länk = länk.rstrip(".,;:")
                v = värd(länk)
                if any(v == i or v.endswith("." + i) for i in INTE_KÄLLA) or blockerad(länk):
                    continue
                if jämförbar(länk) not in kända and jämförbar(länk) not in sedda:
                    sedda.add(jämförbar(länk))
                    ut.append((väg.removeprefix("src/"), länk.split("#:~:text=")[0]))
    return ut


def läs_riksdagen(data):
    lista = json.loads(data).get("dokumentlista", {}).get("dokument") or []
    for d in lista:
        if d.get("typ") not in RIKSDAGSTYPER:
            continue
        titel = " – ".join(x for x in (d.get("titel"), d.get("undertitel")) if x)
        länk = d.get("dokument_url_html") or ""
        if länk.startswith("//"):
            länk = "https:" + länk
        yield f"{d.get('typ', '').upper()}: {titel}", länk, datum(d.get("datum"))


def befintliga():
    return {yaml.safe_load(f.read_text())["källa"]["url"] for f in (ROOT / "påståenden").glob("*/*.yaml")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dagar", type=int, default=8)
    ap.add_argument("--idag", default=datetime.date.today().isoformat())
    a = ap.parse_args()
    gräns = datetime.date.fromisoformat(a.idag) - datetime.timedelta(days=a.dagar)
    källor = yaml.safe_load((ROOT / "bevakning.yaml").read_text())
    kända, sedda = befintliga(), set()
    per_grupp, trasiga = defaultdict(list), []
    for k in källor:
        try:
            data = hämta(k["url"])
            if k.get("format") == "riksdagen":
                poster = list(läs_riksdagen(data))
            elif k.get("format") == "sitemap":
                poster = list(läs_sitemap(data, k.get("sökväg")))
            else:
                poster = list(läs_flöde(data, k.get("kategorier")))
        except Exception as e:  # nätverksfel, flytt eller ändrat format: syns i ärendet
            trasiga.append(f"- {k['namn']}: {type(e).__name__}: {e} ({k['url']})")
            continue
        nya = [(t, l, d) for t, l, d in poster
               if t and l and l not in kända and l not in sedda and d is not None and d >= gräns
               and not blockerad(l) and (not k.get("kräv_ai") or AI_ORD.search(t))
               and (not k.get("kräv_ord") or re.search(rf"\b({k['kräv_ord']})", t, re.IGNORECASE))]
        nya.sort(key=lambda x: x[2] or datetime.date.min, reverse=True)
        if nya:
            per_grupp[k["grupp"]].append((k, nya))
        sedda.update(l for _, l, _ in nya)
    try:
        saknas = sajtlänkar(kända)
    except Exception as e:
        saknas = []
        trasiga.append(f"- pauseai.se: {type(e).__name__}: {e} ({SAJT})")
    if not per_grupp and not trasiga and not saknas:
        return
    # Färre tips per källa tills ärendet ryms, så att alla källor syns.
    for högst in range(MAX_PER_KÄLLA, 0, -1):
        text_ut = rapport(gräns, per_grupp, trasiga, högst, saknas)
        if len(text_ut) <= MAX_TECKEN:
            break
    print(text_ut[:MAX_TECKEN], end="")


def rapport(gräns, per_grupp, trasiga, högst, saknas=()):
    utelämnade = sum(max(len(nya) - högst, 0) for rader in per_grupp.values() for _, nya in rader)
    bas = "https://github.com/pauseai-sverige/belagt/blob/main/"
    ut = [f"Nytt i de bevakade källorna sedan {gräns}. Det här är tips: följ länken till primärkällan, "
          "hämta den och skriv en post bara om ett ordagrant citat bekräftar påståendet "
          f"([METOD.md]({bas}METOD.md)). Ett tips är relevant om det svarar på någon av frågorna i "
          f"[relevans.yaml]({bas}relevans.yaml). Listan över källor finns i [bevakning.yaml]({bas}bevakning.yaml).\n"]
    if utelämnade:
        ut.append(f"\nÄrendet rymmer högst {högst} tips per källa, så {utelämnade} äldre tips är utelämnade.\n")
    for grupp, rader in per_grupp.items():
        ut.append(f"\n## {grupp}\n")
        for k, nya in rader:
            tips = " (ger tips, är inte själv källa: följ länkarna i texten)" if k.get("roll") == "tips" else ""
            ut.append(f"\n**{k['namn']}**{tips}\n\n")
            ut += [f"- [ ] {d or 'okänt datum'}: [{t}]({l})\n" for t, l, d in nya[:högst]]
    if saknas:
        ut.append(f"\n## Källor på pauseai.se som saknas i arkivet\n\nSajten länkar till {len(saknas)} källor som "
                  "inte finns i någon post. Finns det ett ordagrant citat som bär det sajten påstår, skriv en post. "
                  f"Här är de {min(len(saknas), MAX_SAJTLÄNKAR)} första.\n\n")
        ut += [f"- [ ] `{sida}`: {länk}\n" for sida, länk in saknas[:MAX_SAJTLÄNKAR]]
    if trasiga:
        ut.append("\n## Flöden som inte gick att läsa\n\nAdressen kan ha ändrats. Rätta den i bevakning.yaml.\n\n")
        ut.append("\n".join(trasiga) + "\n")
    return "".join(ut)


if __name__ == "__main__":
    main()
