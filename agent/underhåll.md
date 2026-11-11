# Underhåll

Månadsvis körning. Du ser till att det som redan finns i arkivet fortfarande stämmer, och
öppnar en pull request som granskningen ([granskning.md](granskning.md)) sedan prövar. Du slår
aldrig ihop själv. Skriv på svenska. Läs hela [METOD.md](../METOD.md) först.

Ingenting tas bort ur arkivet. Ett påstående som inte längre stämmer får en ny post, och den
gamla får `ersatt_av`.

## 1. Poster som passerat bäst före

Ärendet med etiketten `bäst-före` ("Dags att kontrollera igen") listar dem. För varje post,
hämta källan som den ser ut i dag (`källa.url`, inte arkivkopian) och sök efter nyare uppgifter
från samma avsändare om samma sak.

- **Stämmer fortfarande:** citatet står kvar och inget nyare läge finns. Sätt `kontrollerad`
  till dagens datum och flytta fram `bäst_före`, lika långt som förra gången.
- **Har ändrats:** skriv en ny post med det nya läget enligt [nya-poster.md](nya-poster.md),
  steg 4 och 5, och sätt `ersatt_av` på den gamla.
- **Källan är borta:** citatet finns bara i arkivkopian. Skriv i förbehållet att originalet är
  borta och sedan när, sätt `kontrollerad` och låt `bäst_före` bli `null` om påståendet gäller
  något som hände, inte ett läge som kan ändras.

## 2. Citatkontrollens fynd

Ärendet med etiketten `citatkontroll` listar citat som inte hittades, döda länkar och sidor som
inte gick att hämta.

- **Citatet hittades inte:** jämför källan i dag med arkivkopian. Har källan ändrats, gäller
  arkivkopian och det skrivs i förbehållet. Säger källan nu något annat i sak, skriv en ny post
  och sätt `ersatt_av`. Står citatet varken i källan eller i arkivkopian är posten fel: rapportera
  den som ärende med mallen *Fel i en post* och ändra den inte.
- **Död länk:** finns arkivkopia gäller citatet. Skriv i förbehållet att originalet är borta.
  Har sidan flyttat, ange den nya adressen i förbehållet. `källa.url` ändras inte.
- **Gick inte att hämta:** inget att göra, om det inte är tredje månaden i rad. Rapportera då.

## 3. Preprints som har publicerats

För poster med `källa.typ: preprint` som är äldre än sex månader: se på arXiv-sidan om artikeln
har publicerats efter granskning (fältet *Journal reference* eller en DOI till en tidskrift).
I så fall blir `källa.typ` `granskad`, förbehållet säger var och när den publicerades, och
`kontrollerad` blir dagens datum. Kontrollera att citatet står kvar i den publicerade versionen.

## 4. Poster som bygger på att någon annan återger källan

[statistik.md](../statistik.md) listar dem. Sök efter originalet. Hittas det och går att hämta,
skriv en ny post på originalet och sätt `ersatt_av` på den gamla.

## 5. Kontrollera och öppna pull requesten

```
pip install -r requirements.txt
python tools/arkivera.py <nya id> …
python tools/kontrollera_citat.py --strikt <alla ändrade id> …
python tools/bygg.py
python tools/bygg.py --kontroll
```

Gren `underhåll-ÅÅÅÅ-MM-DD`, pull request som utkast, bara ändringar i `påståenden/` och det som
bygget genererar. Beskrivningen listar varje ändrad post med vad som gjordes och varför. Kryssa
i de genomgångna raderna i ärendena och kommentera dem med länk till pull requesten.

## 6. Rapportera om bevakningen

Se tabellen *Bevakningens utfall* i statistik.md. Källor som har gett många tips men ingen post
under tre månader, och frågor i relevans.yaml som inte har fått någon ny post på tre månader,
skriver du upp i en kommentar i bevakningsärendet. Ändra inte bevakning.yaml eller relevans.yaml
själv: det är ett beslut för en människa.
