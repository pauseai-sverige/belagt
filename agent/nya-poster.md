# Nya poster

Veckovis körning. Du tar fram nya poster och öppnar en pull request. Du slår aldrig ihop den:
det gör granskningen ([granskning.md](granskning.md)), som är en annan session. Skriv på svenska.

## 1. Läs in dig

Läs hela [METOD.md](../METOD.md) och [relevans.yaml](../relevans.yaml). Metoden gäller utan
undantag. Relevansfilen säger vad arkivet letar efter: frågorna som pauseai.se behöver belägg för.

## 2. Samla tips

1. Det öppna ärendet med etiketten `bevakning` ("Nytt att granska, vecka …"). Tips som redan är
   ikryssade är genomgångna. Kör också `python tools/bevaka.py` för det allra senaste.
2. Avsnittet *Källor på pauseai.se som saknas i arkivet* i samma ärende. Det är källor sajten
   redan använder, och de går före nya tips.
3. Egna sökningar. Välj de tre till fem frågor i relevans.yaml där arkivet är tunnast eller
   äldst (se `relevans` i `data/belagt.csv` och `teman/`), och sök på webben med frågans
   `sökord` och egna formuleringar. Sök efter primärkällor från den senaste månaden.

Källor med rollen `tips` i [bevakning.yaml](../bevakning.yaml) är nyhetsbrev. De citeras aldrig.
Läs dem och följ länkarna till myndighetens, företagets eller forskarnas egen text.

## 3. Välj

Ett tips är relevant om det kan ge ett påstående som svarar på någon av frågorna i
relevans.yaml. Svarar det inte på någon, välj bort det. Bland de relevanta går följande först:

1. Källor som pauseai.se redan länkar till men som saknas i arkivet.
2. Mätningar, händelser och beslut från oberoende institut och myndigheter.
3. Daterade uttalanden i primärkälla från personer vars bedömning väger (se metoden).
4. Motröster. Ett påstående som talar emot pauseai.se:s linje är lika relevant som ett som talar för.

Skriv högst 15 poster per körning. Hellre fem som bär än femton som fyller ut. Välj bort
reklam, kundcase, produktnyheter och åsikter utan sakinnehåll.

## 4. Skriv posterna

För varje valt tips:

1. Gå till primärkällan och hämta den. Svarar sidan 403 eller kräver JavaScript, hämta den
   senaste kopian i Wayback Machine (`https://web.archive.org/web/2id_/<adress>`). Går källan
   inte att hämta någonstans blir det ingen post.
2. Skriv en post bara om ett ordagrant citat bekräftar hela påståendet. Följ mallen i METOD.md
   och befintliga poster. Ett påstående per post. Är du osäker, låt bli.
3. Id är `BID-` och nästa lediga nummer. Hitta inte på nya prefix.
4. Sätt `granskning: maskinell` och `relevans:` med nycklarna för de frågor posten svarar på.
   `hämtad` och `kontrollerad` är dagens datum.
5. Kör `python tools/liknande.py <id>`. Säger en befintlig post samma sak ur samma källa är
   din post en dubblett och stryks. Gäller din post ett nyare läge av samma sak (en ny mätning,
   ett ändrat beslut), sätt `ersatt_av: <ditt id>` på den äldre posten. Ändra inget annat i den.

## 5. Kontrollera

```
pip install -r requirements.txt
python tools/arkivera.py <id> …            # arkivkopia direkt, så att kontrollen läser samma text senare
python tools/kontrollera_citat.py --strikt <id> …
python tools/bygg.py
python tools/bygg.py --kontroll
```

En post vars citat inte hittas stryks. Skriv inte om citatet tills det passar: gå tillbaka till
källan och kopiera, eller låt bli.

## 6. Redovisa utfallet

Lägg till en rad per källa i [bevakning/utfall.csv](../bevakning/utfall.csv): veckan (som
`2026-46`), källans namn som i bevakning.yaml, hur många av dess tips du gick igenom och hur
många poster de gav. Egna sökningar får källnamnet `Egen sökning`, och sajtens saknade källor
`pauseai.se`. Kör `python tools/bygg.py` igen efteråt.

## 7. Öppna pull requesten

Gren `nya-ÅÅÅÅ-MM-DD` (dagens datum), pull request som utkast. Ändra bara filer i
`påståenden/`, `bevakning/utfall.csv` och det som bygget genererar, annars slås den inte ihop.
Beskrivningen ska ha:

- för varje post: id, påståendet, källänken, citatet och vilken fråga i relevans.yaml den svarar på
- vilka äldre poster som fått `ersatt_av` och varför
- vilka sökningar du gjorde
- vilka tips som valdes bort, med en rad om varför

Kryssa sedan i de genomgångna tipsen i bevakningsärendet, också de bortvalda. Skriv inte om
ärendet för hand: hämta texten, ändra bara `- [ ]` till `- [x]` på rätt rader, kontrollera att
inget annat ändrats och spara. Kommentera ärendet med länk till pull requesten.

Finns inget som håller en vecka: öppna ingen pull request. Kryssa i tipsen och skriv en
kommentar i ärendet om det.
