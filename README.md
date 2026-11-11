# Belagt

**Verifierade påståenden om AI-utvecklingen, med primärkällor.**

Belagt är ett växande arkiv på svenska. Varje post är ett enda påstående om vad som har hänt,
mätts, bedömts eller föreslagits inom AI-utvecklingen. Till varje påstående hör vem som står
bakom det, när det hände och ett ordagrant citat ur primärkällan. Tanken är att du ska kunna
kontrollera varje påstående själv och hänvisa rätt när du skriver.

👉 **Sök i arkivet: [pauseai-sverige.github.io/belagt](https://pauseai-sverige.github.io/belagt/)**

## Vad kan jag använda det till?

- **Skriva eget material.** Faktablad, debattartiklar, föredrag, studiecirklar och
  lektioner kan hämta sina belägg härifrån. Varje post har en färdig källhänvisning att kopiera.
- **Kontrollera något du har hört.** Sök på ett namn, ett företag eller en händelse.
- **Följa utvecklingen över tid.** [Tidslinjen](tidslinje.md) visar allt i datumordning.
  Påståenden som blir inaktuella tas aldrig bort, utan märks med vad som ersatt dem.
- **Bygga verktyg.** Hela arkivet finns som [JSON](data/belagt.json) och [CSV](data/belagt.csv).
- **Se hur arkivet fördelar sig.** [Statistiken](statistik.md) visar hur många poster som
  kommer från varje sorts källa, avsändare, språk och tema, så att det syns var arkivet är tunt.

## Teman

| Tema | Handlar om |
|---|---|
| [förmågor](teman/förmågor.md) | Vad AI-systemen kan göra och hur det mäts |
| [tempo](teman/tempo.md) | Hur snabbt utvecklingen går och varför |
| [självförbättring](teman/självförbättring.md) | AI som används för att utveckla AI |
| [kontroll](teman/kontroll.md) | Går systemen att styra, övervaka och testa? |
| [missbruk](teman/missbruk.md) | Cyberangrepp, påverkan och biologiska risker |
| [styrning](teman/styrning.md) | Reglering, tillsyn och förslag om att bromsa |
| [geopolitik](teman/geopolitik.md) | Kapplöpningen mellan länder |
| [nytta](teman/nytta.md) | Vad AI redan gör för sjukvård, forskning och samhälle |
| [röster](teman/röster.md) | Vad forskare, insiders och politiker säger |
| [samhälle](teman/samhälle.md) | Jobb, ekonomi, beroende och AI-kompanjoner |
| [miljö](teman/miljö.md) | Energi, klimat och vatten |
| [rättigheter](teman/rättigheter.md) | Upphovsrätt, diskriminering och integritet |

## Vad betyder "belagt"?

Ett påstående kommer bara in i arkivet om det har kontrollerats mot primärkällan och ett
ordagrant citat därifrån bekräftar det. Det betyder att **källan säger så**, inte att det källan
säger är sant. När OpenAI skriver om sin egen modell står det därför "OpenAI uppger" och inte
att något är ett faktum. Förbehållen under varje post anger vad som behöver vägas in, och varje post är märkt med vilken
sorts källa det är: myndighet, granskad forskning, preprint, rapport, partsuppgift, opinion eller
media. Källänken öppnar källan med citatet markerat.
Hur kontrollen går till står i [METOD.md](METOD.md).

## Så här hänvisar du

Hänvisa till primärkällan och gärna till posten här, till exempel:

> Epoch AI (oberoende forskningsinstitut), 2026-09. Trends in Artificial Intelligence. https://epoch.ai/trends. Via Belagt TID-01: https://pauseai-sverige.github.io/belagt/#TID-01

Knappen *Kopiera källhänvisning* på webbsidan ger den texten. Id:t (`TID-01`) ändras aldrig.

## Ursprung och öppenhet

Arkivet drivs av [PauseAI Sverige](https://pauseai.se) och finns för att det som står på
pauseai.se ska gå att kontrollera. PauseAI vill att utvecklingen av de mest kraftfulla
AI-systemen pausas tills de går att göra säkra. Det styr vilka frågor arkivet täcker, men inte
vilka svar som tas med: motröster, osäkerheter och exempel på vad AI redan gör för nytta tas med
på samma villkor.
Ett arkiv som bara tar med det som passar den egna saken blir oanvändbart för alla, den egna
saken inräknad.

AI (Claude) hittar, skriver och granskar posterna. Citatet kontrolleras maskinellt mot den
hämtade källtexten, och en oberoende AI-session läser varje post mot källan innan den kommer in.
En människa läser ett stickprov varje vecka. Varje post visar vilken granskning den har fått, och
hur det går till står i [METOD.md](METOD.md#granskning). Varje månad kontrolleras alla citat igen
mot arkivkopiorna, och resultatet läggs öppet i ett
[ärende](https://github.com/pauseai-sverige/belagt/issues?q=label%3Acitatkontroll).

Vad som letas efter styrs av vad [pauseai.se](https://pauseai.se) behöver belägg för. Frågorna
står i [relevans.yaml](relevans.yaml), och en [fast lista med källor](bevakning.yaml) bevakas
varje vecka, så att urvalet inte bara beror på vad någon råkar läsa.

## Bidra

Har du hittat ett fel, en död länk eller ett påstående som saknas? Öppna ett
[ärende](https://github.com/pauseai-sverige/belagt/issues/new/choose).

**Läser du kinesiska, japanska, koreanska, portugisiska, norska eller danska?** Citat på andra språk står i original med en översättning bredvid.
Översättningarna är gjorda av AI och märkta *inte granskade* tills någon som läser språket har
kontrollerat dem. [Här är de ogranskade](https://pauseai-sverige.github.io/belagt/?q=ogranskad).
Använd mallen [Granska en översättning](https://github.com/pauseai-sverige/belagt/issues/new?template=oversattning.yml),
så skrivs ditt namn in som granskare. Förslag på nya poster går också
att skicka som pull request, se [METOD.md](METOD.md).

**Använder du en AI-agent?** Läs [AGENTS.md](AGENTS.md). Där står hur agenten hämtar posterna,
använder dem i texter och föreslår nya poster.

## Licens

Innehållet får användas fritt, även kommersiellt, om du anger källan:
[CC BY 4.0](LICENSE). Koden i `tools/` och `docs/` är [MIT](LICENSE-kod). Citaten ur
primärkällorna är korta utdrag som återges med stöd av citaträtten, och upphovsrätten till dem
ligger kvar hos källan.
