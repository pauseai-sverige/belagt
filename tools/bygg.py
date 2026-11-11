#!/usr/bin/env python3
"""Validera påståendena och bygg allt som genereras ur dem.

    python tools/bygg.py              # validera och skriv om genererade filer
    python tools/bygg.py --kontroll   # validera och kontrollera att genererade filer är aktuella (CI)

Källan är påståenden/<år>/<id>.yaml. Allt annat genereras och redigeras aldrig för hand:
    data/belagt.json, data/belagt.csv   hela arkivet som data
    tidslinje.md                        alla påståenden i datumordning
    teman/<tema>.md                     ett dokument per tema
    docs/belagt.json                    underlag för webbsidan i docs/
    statistik.md                        hur arkivet fördelar sig, så att snedfördelningar syns
"""
import csv
import io
import json
import re
import sys
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from regler import blockerad, mellanled

ROOT = Path(__file__).resolve().parent.parent
PÅST = ROOT / "påståenden"
REPO_URL = "https://github.com/pauseai-sverige/belagt"
SIDA_URL = "https://pauseai-sverige.github.io/belagt/"

TYPER = {"händelse", "mätning", "bedömning", "prognos", "förslag"}
TEMAN = {
    "förmågor": "Vad AI-systemen kan göra och hur det mäts.",
    "tempo": "Hur snabbt utvecklingen går och varför: beräkningskraft, investeringar och skalning.",
    "självförbättring": "AI som används för att utveckla AI.",
    "kontroll": "Går systemen att styra, övervaka och testa? Alignment, tankekedjor och testmedvetenhet.",
    "missbruk": "Hur AI används för att skada: cyberangrepp, påverkan och biologiska risker.",
    "styrning": "Reglering, standarder, tillsyn och förslag om att bromsa eller pausa.",
    "geopolitik": "Kapplöpningen mellan länder, exportkontroller, USA och Kina.",
    "nytta": "Vad AI redan gör för sjukvård, forskning och samhälle.",
    "röster": "Vad forskare, insiders, politiker och andra bedömare säger.",
    "samhälle": "Hur AI påverkar arbete, ekonomi och vardag: jobb, beroende, AI-kompanjoner och kritiskt tänkande.",
    "miljö": "Energi, klimat och vatten: hur mycket el och vatten AI kräver och vad det betyder för utsläppen.",
    "rättigheter": "Upphovsrätt, diskriminering och integritet: hur AI påverkar enskildas rättigheter.",
}
FÄLT = ["id", "påstående", "typ", "vem", "datum", "tema", "källa", "förbehåll", "vikt",
        "bäst_före", "kontrollerad", "ersatt_av"]
# Valfria fält. granskning: hur posten granskades innan den kom in (se METOD.md). Poster utan
# fältet kom in före november 2026, via en pull request som en människa slog ihop.
# relevans: vilka frågor i relevans.yaml posten svarar på.
VALFRIA = ["granskning", "relevans"]
GRANSKNINGAR = {
    "maskinell": "Citatet är kontrollerat maskinellt och posten granskad av en oberoende AI-session.",
    "människa": "En människa har läst posten mot källan.",
}
KÄLLFÄLT = ["url", "titel", "typ", "citat", "hämtad", "arkiv"]
# Vilken sorts källa det är, så att läsaren ser hur tung den är utan att läsa förbehållet.
KÄLLTYPER = {
    "myndighet": "Regering, myndighet, parlament eller mellanstatlig organisation.",
    "granskad": "Vetenskaplig artikel som har granskats av andra forskare före publicering.",
    "preprint": "Forskningsartikel som inte har granskats (än), till exempel på arXiv.",
    "rapport": "Rapport från forskningsinstitut, universitet, tankesmedja, analysföretag eller "
               "intresseorganisation, om något annat än den egna verksamheten.",
    "partsuppgift": "Företag eller organisation som skriver om sig själv, sina produkter eller sina ståndpunkter.",
    "opinion": "Person eller grupp som argumenterar i eget namn: essä, blogg, debattartikel, tal eller öppet brev.",
    "media": "Nyhetsartikel, reportage eller intervju i medier.",
}
# Källor på andra språk än engelska och svenska: citatet står på originalspråket och
# översättningen bredvid, med vem som översatt och om en människa har granskat den.
ÖVERSÄTTNINGSFÄLT = ["språk", "översättning", "översatt_av", "granskad_av"]
SPRÅKNAMN = {"zh": "kinesiska", "ja": "japanska", "ko": "koreanska", "ru": "ryska", "fr": "franska", "pt": "portugisiska",
             "de": "tyska", "es": "spanska", "ar": "arabiska", "no": "norska", "da": "danska"}
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
MAX_CITAT_TECKEN = 120
DATUM_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
DAG_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[A-Za-z0-9_]+-\d{2,3}$")
REF_RE = re.compile(r"\b[A-Za-z0-9_]{3,}-\d{2,3}\b")
MAX_CITAT_ORD = 50


def ladda():
    poster, fel = [], []
    for f in sorted(PÅST.glob("*/*.yaml")):
        try:
            p = yaml.safe_load(f.read_text())
        except yaml.YAMLError as e:
            fel.append(f"{f.relative_to(ROOT)}: ogiltig YAML: {e}")
            continue
        p["_fil"] = f
        poster.append(p)
    return poster, fel


def relevansnycklar():
    f = ROOT / "relevans.yaml"
    return {r["nyckel"] for r in yaml.safe_load(f.read_text())} if f.exists() else set()


def jämför(s):
    return "".join(c for c in (s or "").lower() if c.isalnum())


def validera(poster):
    fel, ids, citat, nycklar = [], {}, {}, relevansnycklar()
    for p in poster:
        f = p["_fil"].relative_to(ROOT)
        pid = p.get("id", "?")

        def err(msg):
            fel.append(f"{f} {pid}: {msg}")

        if saknas := [k for k in FÄLT if k not in p]:
            err(f"saknar {saknas}")
            continue
        if okända := [k for k in p if k not in FÄLT + VALFRIA and k != "_fil"]:
            err(f"okända fält {okända}")
        if not ID_RE.match(str(pid)) or p["_fil"].stem != pid:
            err("id ska matcha filnamnet och ha formen PREFIX-NN")
        if pid in ids:
            err(f"dubblerat id (även i {ids[pid]})")
        ids[pid] = f
        if not isinstance(p["påstående"], str) or len(p["påstående"]) < 20:
            err("påståendet saknas eller är för kort")
        if p["typ"] not in TYPER:
            err(f"typ {p['typ']!r}, ska vara en av {sorted(TYPER)}")
        if not p["vem"]:
            err("vem saknas")
        if not isinstance(p["datum"], str) or not DATUM_RE.match(p["datum"]):
            err(f"datum {p['datum']!r} ska vara ÅÅÅÅ, ÅÅÅÅ-MM eller ÅÅÅÅ-MM-DD (inom citattecken)")
        elif p["_fil"].parent.name != p["datum"][:4]:
            err(f"ligger i {p['_fil'].parent.name}/ men datum är {p['datum']}")
        if not isinstance(p["tema"], list) or not p["tema"] or set(p["tema"]) - set(TEMAN):
            err(f"tema {p['tema']!r}, ska vara en lista ur {sorted(TEMAN)}")
        if "granskning" in p and p["granskning"] not in GRANSKNINGAR:
            err(f"granskning {p['granskning']!r}, ska vara en av {sorted(GRANSKNINGAR)}")
        if "relevans" in p and (not isinstance(p["relevans"], list) or set(p["relevans"]) - nycklar):
            err(f"relevans {p['relevans']!r}, ska vara en lista med nycklar ur relevans.yaml")
        if p["vikt"] not in (1, 2, 3):
            err(f"vikt {p['vikt']!r}, ska vara 1, 2 eller 3")
        for fält in ("bäst_före", "kontrollerad"):
            v = p[fält]
            if (v is not None or fält == "kontrollerad") and not (isinstance(v, str) and DAG_RE.match(v)):
                err(f"{fält} {v!r} ska vara ÅÅÅÅ-MM-DD")
        k = p["källa"]
        if not isinstance(k, dict) or [x for x in KÄLLFÄLT if x not in k]:
            err(f"källa ska ha fälten {KÄLLFÄLT}")
            continue
        if not str(k["url"]).startswith(("http://", "https://")):
            err("källa.url ska vara en webbadress")
        elif blockerad(k["url"]):
            err("källa.url är en sajt som aldrig kan vara källa (tools/regler.py, se METOD.md)")
        elif mellanled(k["url"]):
            err("källa.url är en sök- eller kortlänk, inte källan själv")
        # Samma citat ur samma källa två gånger är en dubblett, om inte den ena har ersatt den andra.
        nyckel = (str(k["url"]).split("#")[0].rstrip("/"), jämför(k["citat"]))
        if nyckel in citat and not p["ersatt_av"] and not citat[nyckel]["ersatt_av"]:
            err(f"samma citat ur samma källa som {citat[nyckel]['id']}")
        citat.setdefault(nyckel, p)
        if k["typ"] not in KÄLLTYPER:
            err(f"källa.typ {k['typ']!r}, ska vara en av {sorted(KÄLLTYPER)}")
        if not k["citat"]:
            err("källa.citat saknas: ett verifierat påstående har alltid ett ordagrant citat")
        elif CJK_RE.search(k["citat"]):
            if len(re.sub(r"\s+", "", k["citat"])) > MAX_CITAT_TECKEN:
                err(f"källa.citat är längre än {MAX_CITAT_TECKEN} tecken")
        elif len(k["citat"].split()) > MAX_CITAT_ORD:
            err(f"källa.citat är längre än {MAX_CITAT_ORD} ord")
        if okända := [x for x in k if x not in KÄLLFÄLT + ÖVERSÄTTNINGSFÄLT]:
            err(f"okända fält i källa {okända}")
        if k.get("språk") or CJK_RE.search(k["citat"] or ""):
            if k.get("språk") not in SPRÅKNAMN:
                err(f"källa.språk {k.get('språk')!r} ska vara en av {sorted(SPRÅKNAMN)}")
            if not k.get("översättning") or not k.get("översatt_av"):
                err("källa på annat språk kräver översättning och översatt_av")
        if k["hämtad"] is not None and not (isinstance(k["hämtad"], str) and DAG_RE.match(k["hämtad"])):
            err(f"källa.hämtad {k['hämtad']!r} ska vara ÅÅÅÅ-MM-DD")
        if k["arkiv"] is not None and not str(k["arkiv"]).startswith("https://"):
            err("källa.arkiv ska vara en webbadress eller null")
    for p in poster:
        if not isinstance(p.get("källa"), dict):
            continue
        f = p["_fil"].relative_to(ROOT)
        if p.get("ersatt_av") and p["ersatt_av"] not in ids:
            fel.append(f"{f}: ersatt_av {p['ersatt_av']} finns inte")
        for ref in REF_RE.findall(p.get("förbehåll") or ""):
            if ref not in ids and not DATUM_RE.match(ref):
                fel.append(f"{f}: förbehållet hänvisar till {ref}, som inte finns i arkivet")
    return fel


def ren(p):
    return {k: p[k] for k in FÄLT + VALFRIA if k in p}


def sortera(poster):
    return sorted(poster, key=lambda p: (p["datum"], p["id"]))


def citera(p):
    k = p["källa"]
    titel = f"{k['titel']}. " if k["titel"] else ""
    return f"{p['vem']}, {p['datum']}. {titel}{k['url']}. Via Belagt {p['id']}: {SIDA_URL}#{p['id']}"


def citatlänk(k):
    """Länk som öppnar källan med citatet markerat (textfragment, #:~:text=början,slut).

    Webbläsare som inte stöder textfragment öppnar bara sidan. PDF-filer stöder det inte alls,
    och då blir länken den vanliga."""
    url, citat = k["url"], (k["citat"] or "").strip()
    if not citat or urllib.parse.urlparse(url).path.lower().endswith(".pdf"):
        return url
    # Ett utelämnande (…) i citatet finns inte i källan, så början tas före det första och
    # slutet efter det sista.
    delar = [d.strip(" .,;:\"'”“’‘()[]") for d in re.split(r"…|\.\.\.|\[…\]", citat)]
    delar = [d for d in delar if d]
    if not delar:
        return url
    if CJK_RE.search(citat):
        start, slut = delar[0][:12], delar[-1][-12:]
        if len(delar) == 1 and len(delar[0]) <= 24:
            start, slut = delar[0], ""
    else:
        först, sist = delar[0].split(), delar[-1].split()
        if len(delar) == 1 and len(först) <= 8:
            start, slut = " ".join(först), ""
        else:
            start, slut = " ".join(först[:4]), " ".join(sist[-4:])
    # Bindestreck avgränsar prefix och suffix i textfragment och måste därför kodas.
    koda = lambda s: urllib.parse.quote(s, safe="").replace("-", "%2D")
    fragment = ":~:text=" + koda(start) + ("," + koda(slut) if slut else "")
    return url + ("" if "#" in url else "#") + fragment


def översättningsetikett(k):
    granskning = f"granskad av {k['granskad_av']}" if k.get("granskad_av") else \
        f"inte granskad av någon som läser {SPRÅKNAMN.get(k['språk'], k['språk'])}"
    return f"Översatt från {SPRÅKNAMN.get(k['språk'], k['språk'])} av {k['översatt_av']}, {granskning}"


def md_post(p, relativ=".."):
    k = p["källa"]
    arkiv = f" · [arkivkopia]({k['arkiv']})" if k["arkiv"] else ""
    ersatt = f"\n  *Ersatt av {p['ersatt_av']}.*" if p["ersatt_av"] else ""
    rader = [
        f"- **{p['påstående']}**{ersatt}",
        f"  {p['vem']} · {p['datum']} · {', '.join(p['tema'])} · {k['typ']} · "
        f"[{p['id']}]({relativ}/påståenden/{p['datum'][:4]}/{p['id']}.yaml)",
        f"  > {k['citat']}",
    ]
    if k.get("översättning"):
        rader.append(f"  >\n  > *{översättningsetikett(k)}:* {k['översättning']}")
    rader.append(f"  > — [{k['titel'] or k['url']}]({citatlänk(k)}){arkiv}")
    if p["förbehåll"]:
        # Id:n som pekar på andra poster blir länkar till posten på webbsidan.
        förbehåll = REF_RE.sub(lambda m: f"[{m[0]}]({SIDA_URL}#{m[0]})" if m[0] in IDS else m[0], p["förbehåll"])
        rader.append(f"\n  *Förbehåll:* {förbehåll}")
    return "\n".join(rader) + "\n"


HUVUD = "<!-- Genereras av tools/bygg.py. Redigera påståenden/ i stället. -->\n\n"


def tidslinje(poster):
    ut = [HUVUD, "# Tidslinje\n\n",
          f"Alla {len(poster)} påståenden i arkivet, i den ordning det de handlar om hände eller sades.\n"]
    år = None
    for p in sortera(poster):
        if p["datum"][:4] != år:
            år = p["datum"][:4]
            ut.append(f"\n## {år}\n\n")
        ut.append(md_post(p, "."))
    return "".join(ut)


def tema_md(tema, poster):
    urval = [p for p in sortera(poster) if tema in p["tema"]]
    ut = [HUVUD, f"# {tema.capitalize()}\n\n", f"{TEMAN[tema]}\n\n",
          f"{len(urval)} påståenden, de viktigaste först inom varje år.\n"]
    per_år = defaultdict(list)
    for p in urval:
        per_år[p["datum"][:4]].append(p)
    for år in sorted(per_år, reverse=True):
        ut.append(f"\n## {år}\n\n")
        for p in sorted(per_år[år], key=lambda p: (-p["vikt"], p["datum"], p["id"])):
            ut.append(md_post(p))
    return "".join(ut)


def data_csv(poster):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["id", "datum", "påstående", "typ", "vem", "tema", "vikt", "källa_url", "källa_titel", "källa_typ",
                "citat", "hämtad", "arkiv", "förbehåll", "bäst_före", "kontrollerad", "ersatt_av",
                "citat_språk", "översättning", "översatt_av", "granskad_av", "granskning", "relevans"])
    for p in sortera(poster):
        k = p["källa"]
        w.writerow([p["id"], p["datum"], p["påstående"], p["typ"], p["vem"], ";".join(p["tema"]),
                    p["vikt"], k["url"], k["titel"] or "", k["typ"], k["citat"], k["hämtad"] or "",
                    k["arkiv"] or "", p["förbehåll"] or "", p["bäst_före"] or "", p["kontrollerad"],
                    p["ersatt_av"] or "", k.get("språk") or "", k.get("översättning") or "",
                    k.get("översatt_av") or "", k.get("granskad_av") or "", p.get("granskning") or "",
                    ";".join(p.get("relevans") or [])])
    return buf.getvalue()


def data_json(poster):
    return json.dumps({"källa": REPO_URL, "licens": "CC BY 4.0", "teman": TEMAN, "källtyper": KÄLLTYPER,
                       "granskningar": GRANSKNINGAR,
                       "påståenden": [dict(ren(p), citera=citera(p), citatlänk=citatlänk(p["källa"]))
                                      for p in sortera(poster)]},
                      ensure_ascii=False, indent=1) + "\n"


def statistik(poster):
    """Hur arkivet fördelar sig. Varje påstående kan stämma och arkivet ändå ge en skev bild,
    om urvalet är skevt. Den här sidan gör fördelningen synlig."""
    n = len(poster)
    aktuella = [p for p in poster if not p["ersatt_av"]]

    def tabell(rubrik, räknare, förklaring=None, ordning=None):
        rader = [f"\n## {rubrik}\n\n"]
        if förklaring:
            rader.append(f"{förklaring}\n\n")
        rader.append("| | Antal | Andel |\n|---|---:|---:|\n")
        nycklar = ordning or [k for k, _ in räknare.most_common()]
        for k in nycklar:
            rader.append(f"| {k} | {räknare[k]} | {round(100 * räknare[k] / n)} % |\n")
        return "".join(rader)

    vem = Counter(re.split(r"[,(]", p["vem"])[0].strip() for p in poster)
    domäner = Counter(urllib.parse.urlparse(p["källa"]["url"]).netloc.removeprefix("www.") for p in poster)
    källor = Counter(p["källa"]["url"] for p in poster)
    språk = Counter(SPRÅKNAMN.get(p["källa"].get("språk"), "engelska eller svenska") for p in poster)
    ogranskade = sum(1 for p in poster if p["källa"].get("språk") and not p["källa"].get("granskad_av"))
    utan_arkiv = sum(1 for p in poster if not p["källa"]["arkiv"])
    återgivet = [p["id"] for p in aktuella if re.search(r"återgiv|enligt ", p["vem"])]
    ut = [HUVUD, "# Statistik\n\n",
          "Varje påstående i arkivet är kontrollerat mot sin källa. Men arkivet kan ändå ge en skev bild om "
          "*urvalet* är skevt, till exempel om en enda rapport eller ett enda företag står för en stor del av "
          "posterna. Den här sidan visar hur arkivet fördelar sig, så att det syns var det är tunt.\n\n",
          f"- **{n}** påståenden, varav {len(aktuella)} aktuella och {n - len(aktuella)} ersatta\n",
          f"- **{len(källor)}** olika källor och **{len(domäner)}** olika webbplatser\n",
          f"- **{utan_arkiv}** poster saknar ännu arkivkopia\n",
          f"- **{ogranskade}** översättningar är inte granskade av någon som läser språket\n",
          f"- **{len(återgivet)}** aktuella poster bygger på att någon annan återger primärkällan: "
          f"{', '.join(återgivet) or '–'}. Intervjuer i medier räknas med här, men duger enligt "
          "[metoden](METOD.md) när tidningen själv har gjort intervjun.\n"]
    maskinella = sum(1 for p in poster if p.get("granskning") == "maskinell")
    lästa = sum(1 for p in poster if p.get("granskning") == "människa")
    ut.append(f"- **{maskinella}** poster är maskinellt granskade och väntar på att kunna lottas till "
              f"[stickprov](METOD.md#granskning), och **{lästa}** har en människa läst mot källan i ett stickprov. "
              "Övriga kom in före november 2026, via en pull request som en människa slog ihop.\n")
    ut.append(tabell("Tema", Counter(t for p in poster for t in p["tema"]),
                     "Ett påstående kan ha flera teman, så andelarna summerar till mer än 100 %.", list(TEMAN)))
    ut.append(tabell("Typ av påstående", Counter(p["typ"] for p in poster)))
    ut.append(tabell("Typ av källa", Counter(p["källa"]["typ"] for p in poster),
                     " ".join(f"*{k}*: {v}" for k, v in KÄLLTYPER.items()), list(KÄLLTYPER)))
    ut.append(tabell("Språk i källan", språk))
    ut.append(tabell("År", Counter(p["datum"][:4] for p in poster), None,
                     sorted({p["datum"][:4] for p in poster}, reverse=True)))
    topp = Counter(dict(vem.most_common(15)))
    ut.append(tabell("Vanligaste avsändarna", topp, "De 15 som står bakom flest påståenden.",
                     [k for k, _ in vem.most_common(15)]))
    ut.append(tabell("Vanligaste webbplatserna", Counter(dict(domäner.most_common(15))), None,
                     [k for k, _ in domäner.most_common(15)]))
    ut.append(bevakningens_utfall())
    return "".join(ut)


def bevakningens_utfall():
    """Hur många tips och poster varje bevakad källa har gett, ur bevakning/utfall.csv som
    veckans körning fyller på. Visar vilka källor som bär arkivet och vilka som bara ger brus."""
    f = ROOT / "bevakning" / "utfall.csv"
    rader = list(csv.DictReader(f.open())) if f.exists() else []
    if not rader:
        return ""
    summa = defaultdict(lambda: [0, 0, set()])
    for r in rader:
        s = summa[r["källa"]]
        s[0] += int(r["genomgångna"])
        s[1] += int(r["poster"])
        s[2].add(r["vecka"])
    ut = ["\n## Bevakningens utfall\n\n",
          "Hur många tips från varje källa i [bevakning.yaml](bevakning.yaml) som har gåtts igenom och hur många "
          "poster de har gett. *Egen sökning* är sökningarna per fråga i [relevans.yaml](relevans.yaml).\n\n",
          "| Källa | Veckor | Tips | Poster |\n|---|---:|---:|---:|\n"]
    for namn, (tips, antal, veckor) in sorted(summa.items(), key=lambda x: (-x[1][1], -x[1][0], x[0])):
        ut.append(f"| {namn} | {len(veckor)} | {tips} | {antal} |\n")
    return "".join(ut)


IDS = set()


def generera(poster):
    IDS.update(p["id"] for p in poster)
    ut = {
        "data/belagt.json": data_json(poster),
        "data/belagt.csv": data_csv(poster),
        "docs/belagt.json": data_json(poster),
        "tidslinje.md": tidslinje(poster),
        "statistik.md": statistik(poster),
    }
    for tema in TEMAN:
        ut[f"teman/{tema}.md"] = tema_md(tema, poster)
    return ut


def main():
    kontroll = "--kontroll" in sys.argv
    poster, fel = ladda()
    fel += validera(poster)
    if fel:
        print("\n".join(fel))
        sys.exit(f"{len(fel)} fel i {len(poster)} poster")
    utdata = generera(poster)
    inaktuella = []
    for namn, text in utdata.items():
        f = ROOT / namn
        if f.exists() and f.read_text() == text:
            continue
        if kontroll:
            inaktuella.append(namn)
        else:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
    if inaktuella:
        sys.exit("Genererade filer är inte aktuella, kör python tools/bygg.py:\n  " + "\n  ".join(inaktuella))
    print(f"{len(poster)} påståenden, 0 fel" + ("" if kontroll else f", {len(utdata)} filer byggda"))


if __name__ == "__main__":
    main()
