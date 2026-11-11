"""Regler som flera verktyg delar: vilka sajter som aldrig kan vara källa (METOD.md, avsnittet
Vilka avsändare som kan vara källa). Används av bevakningen, så att de inte dyker upp som tips,
och av bygget, så att de inte kan komma in som källa."""
import urllib.parse

# Maskinöversatta eller troligen automatgenererade sajter, återpublicering av andras texter och
# tjänster för betalda pressmeddelanden.
BLOCKERADE = {
    # maskinöversatt, automatgenererat eller utan identifierbar redaktion
    "vietnam.vn", "news55.se", "news.lavx.hu", "streamlinefeed.co.ke", "powersofafrica.com", "inyheter.no",
    # återpublicerar andras texter, gå till originalet
    "tradingview.com",
    # kryptonyheter och fackpress inom reklam och tv
    "tokenpost.com", "adgully.com", "indiantelevision.com",
    # betalda pressmeddelanden
    "markets.businessinsider.com", "prnewswire.com", "globenewswire.com", "businesswire.com",
    "einpresswire.com", "openpr.com", "accessnewswire.com", "newsfilecorp.com",
}
# Länkar som leder vidare till en källa men aldrig är källan själva.
MELLANLED = {"news.google.com", "t.co", "bit.ly", "lnkd.in"}


def värd(url):
    return (urllib.parse.urlparse(url or "").hostname or "").removeprefix("www.")


def _i(url, mängd):
    v = värd(url)
    return any(v == b or v.endswith("." + b) for b in mängd)


def blockerad(url):
    return _i(url, BLOCKERADE)


def mellanled(url):
    return _i(url, MELLANLED)
