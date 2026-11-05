# Kodgranskning – Hemuppgift 2, Del B

Tre separata granskningar av kodbasen: arkitektur, säkerhet och kodkvalitet. Varje fynd
kontrollerades i en andra genomgång mot exakt fil och rad. Där det gick bekräftades fyndet
med ett experiment i headless Chrome i stället för att bara läsas ut ur koden. Fynd som inte
höll ströks eller formulerades om, och det redovisas nedan.

**Radnummer** avser commit `aba3d99`, alltså koden som den såg ut när granskningen gjordes,
före åtgärderna.

**Åtgärdat på branchen `review/del-b`**, ett fynd per kategori och en commit per åtgärd:

| Kategori | Commit | Åtgärd |
|---|---|---|
| Arkitektur | `27e9711` | Trasiga poster i `menus.json` isoleras i stället för att välta hela sidan |
| Kodkvalitet | `5494746` | Laddnings- och renderingsfel skiljs åt, och orsaken loggas |
| Säkerhet | `630b7b9` | Content-Security-Policy som andra försvarslinje |

---

## 1. Arkitektur – granskning mot CLAUDE.md

*Prompt: "Granska kodbasen mot de arkitekturprinciper jag definierat i CLAUDE.md. Var bryter
koden mot principerna? Var är den i linje med dem? Ge konkreta filreferenser."*

### Brott mot principerna

| # | Princip (CLAUDE.md) | Fynd | Var |
|---|---|---|---|
| A1 | "En källa som går sönder får aldrig stoppa de andra" (rad 101) | Frontend litade blint på `menus.json`. **Bekräftat med experiment:** om `osaka` saknar `name` kastas ett `TypeError` vid varje sökning och listan fryser. Om `osaka.dishes` är en sträng visar hela sidan "Couldn't load today's menus". **→ Åtgärdat i `27e9711`.** | `docs/app.js` 164, 176, 217 |
| A2 | "Ingen kontorsspecifik data i koden" (rad 103) | Tidszonen `Europe/Stockholm` och valutan `kr` är hårdkodade. Ett kontor i ett annat land får fel datum, fel tidsstämpel och fel valuta. Att flytta dem till config är en kontraktsändring och kräver `models.py` och tester, som inte finns än. | `docs/app.js` 27, 115, 128 |
| A3 | "Nya källtyper följer `Source`-protokollet – ingen if-kedja per restaurang" (rad 105) | `config.yaml` säger inte vilken källtyp eller URL en restaurang har. Bara 4 av 24 har `menu_source`, men ungefär 12 menyer kommer från samma två aggregatorer (menydags.se, mylunch.se). Scrapern kan inte bli datadriven utan ett `source`-fält. | `config.yaml` 100, 135, 170, 178 |
| A4 | "JSON-formatet är ett kontrakt … schemat i `scraper/models.py`" (rad 107) | Kontraktet finns bara som en kommentar i CLAUDE.md, och `models.py` saknas. Datan använder `"price": null`, vilket kontraktet inte beskriver. | `docs/data/menus.json` 331, 529; CLAUDE.md 52 |
| A5 | Arkitekturen och kommandona (rad 75–95, 133–140) | `scraper/`, `tests/`, `pyproject.toml` och ett GitHub Actions-workflow saknas, så `pip install -e ".[dev]"` och `pytest` går inte att köra. Stacken (rad 67) nämner dessutom ingen YAML-parser, fast `config.py` ska läsa `config.yaml`. Det beroendet behöver godkännas enligt rad 121. | CLAUDE.md 67, 85, 121, 135–136 |
| A6 | "Inga globala muterbara variabler" (rad 109) | **Gränsfall.** `state` är muterbart men ligger i en IIFE och är alltså inte globalt. Principen är skriven för Python, så det här räknas inte som ett brott. | `docs/app.js` 15 |

### I linje med principerna

- **Inga externa anrop utöver `menus.json`.** Sidan gör bara anropet på rad 215, och inga
  typsnitt laddas utifrån sedan `6ccfd01`. Bekräftat: 0 font-anrop i snapshot-körningen.
- **Inget ramverk eller byggsteg.** Sajten består av ren HTML/CSS/JS i `docs/`.
- **Ingen backend och ingen databas.** Datan är en statisk JSON-fil.
- **Consid, Malmö och Stortorget finns bara i datan.** `git grep` hittar dem bara i
  `config.yaml`, `menus.json`, README och CLAUDE.md, inte i koden.
- **Frontend läser exakt kontraktets fält.** `menus.json` kontrollerades maskinellt mot
  kontraktet: inga okända nycklar och inga motsägelser mellan status och rätter.
  Avstånden stämmer med koordinaterna i `config.yaml`.
- **Varje körning arkiveras.** Arkivkopian finns i `docs/data/archive/`.
- **Funktioner gör en sak.** Det gäller i stort sett efter refaktoreringen i Del A. Undantaget
  är K2 nedan.

---

## 2. Säkerhet

*Prompt: "Gå igenom kodbasen och leta efter: hårdkodade hemligheter eller uppgifter, saknad
inputvalidering, injection-risker (SQL, kommando, path traversal), känsliga data i loggar,
och osäkra standardvärden. Lista varje fynd med filnamn och radnummer."*

| # | Kategori | Fynd | Var | Allvar |
|---|---|---|---|---|
| S1 | Inputvalidering / injection | Skrapad text från restaurangsajter renderas med `innerHTML`, och sidan saknade CSP. **Bekräftat med experiment:** en XSS-payload i alla 14 renderade fält stoppades. `esc()` escapar `& < > "`, alla attribut står inom dubbla citattecken och `isUrl()` släpper bara igenom http(s). Men nästa gång någon glömmer `esc()` finns ingen andra försvarslinje. Ett injicerat `onerror` kördes. **→ Åtgärdat i `630b7b9`.** | `docs/index.html` 3–9; `docs/app.js` 179, 199 | Medel |
| S2 | Inputvalidering | `menus.json` validerades inte vid laddning, så en felaktig post kunde välta sidan (samma som A1). Det är tillgänglighet snarare än intrång. **→ Åtgärdat i `27e9711`.** | `docs/app.js` 217 | Låg |
| S3 | Osäkert standardvärde | `python -m http.server -d docs` binder till alla nätverksgränssnitt, så förhandsgranskningen exponeras på nätverket, till exempel på ett café-wifi. Lägg till `--bind 127.0.0.1`. | CLAUDE.md 139 | Låg |
| S4 | Integritet | Externa länkar har `rel="noopener"` men inte `noreferrer`. Moderna webbläsare skickar ändå bara origin som referer, så det läcker lite. | `docs/app.js` 60 | Låg |
| S5 | Inputvalidering | Filterlistan i `localStorage` läses in utan kontroll. Den används bara i `Set.has` och renderas aldrig, så det går inte att utnyttja. | `docs/app.js` 20 | Ingen |

**Ingenting hittat:**
- **Hemligheter:** `git grep` på nycklar, tokens, lösenord och privata nycklar gav bara
  kommentaren i `.gitignore`, både i alla spårade filer och i hela historiken.
- **SQL-, kommando- och path traversal-risker:** det finns ingen server och ingen Python-kod än.
  Framtida risk: `build.py` kommer att bygga sökvägen `archive/<datum>.json`, och datumet
  måste då valideras som `YYYY-MM-DD`.
- **Känsliga data i loggar:** det fanns ingen loggning alls, och datan innehåller bara
  företagsadresser.

**Struket i den andra genomgången:**
- *"Saknad `'` i `esc()` ger attributinjektion."* Det går inte, eftersom alla attribut står
  inom dubbla citattecken. XSS-testet bekräftade det.
- *"Footer-länken till LelleWipp är kontorsspecifik."* Länken går till mallens ursprungsrepo,
  vilket är rätt även i en fork.

---

## 3. Kodkvalitet – de fem allvarligaste

*Prompt: "Identifiera: funktioner som gör mer än en sak, otydlig namngivning, saknad
felhantering för externa anrop, och kod som är svår att läsa utan kommentarer. Lista de fem
allvarligaste problemen."*

1. **Saknad felhantering för externa anrop** (`docs/app.js` 215–218, 101).
   - Ett enda `.catch()` fångade HTTP-fel, ogiltig JSON *och* programmeringsfel. Det loggade
     ingenting och visade "Couldn't load" för alla.
   - Fel från filter- och sökhändelser hanterades inte alls.
   - **Bekräftat med experiment:** 404, ogiltig JSON, saknad lista och ett simulerat
     renderingsfel gav samma meddelande och tom konsol.
   - **→ Åtgärdat i `5494746`.**
2. **`renderHeader` gör fem saker** (`docs/app.js` 103–125): titel, antal restauranger,
   avståndsnot, tidsstämpel och notisen om helg eller gammal meny. Antalet inom radien räknas
   också ut här.
3. **HTML byggs med strängkonkatenering** (`docs/app.js` 127–150, 184–191). Strukturen syns
   inte i koden, och varje fält måste komma ihåg `esc()`. Det är samma risk som S1, sedd från
   läsbarhetssidan.
4. **Otydlig eller missvisande namngivning:**
   - `sortRows` (168–171) sorterar på plats *och* returnerar listan, men returvärdet ignoreras.
   - `state.q` och `#q` (101, 164) borde heta `query` eller `search`.
   - `extraInfo` (52) säger inte att det handlar om "note eller includes".
   - CSS-klasserna `.nitem`, `.chead`, `.incl`, `.cfoot` och `.seg` är svåra att tolka.
5. **Kod som är svår att läsa utan kommentarer:**
   - `style.css` är skriven som komprimerade enradsregler. Sex rader är 160–223 tecken långa
     (rad 32, 39, 40, 44, 51, 66), vilket också gör diffarna svåra att granska.
   - `byPrice` (170) använder `||` för att bryta lika pris med avstånd, vilket inte syns utan
     att man läser noga.

---

## Hur åtgärderna verifierades

**Regressionstest:** snapshot-verktyget från Del A kördes för varje åtgärd. Det jämför den
renderade DOM:en i 20 tillstånd och 4 skärmdumpar mot läget före åtgärden. För giltig data
var resultatet identiskt efter alla tre åtgärderna.

**Riktade experiment före och efter varje åtgärd:**

| Åtgärd | Före | Efter |
|---|---|---|
| **A1** – restaurang utan `name` | sökningen kastar ett fel | 14 kort, och sökningen fungerar |
| **A1** – `dishes` som sträng | hela sidan visar "Couldn't load" | 13 kort; Osaka visas i listan "No menu online" med "Couldn't fetch today" |
| **K1** – 404 / ogiltig JSON / ingen lista | samma meddelande, tom konsol | samma meddelande, orsaken i konsolen |
| **K1** – renderingsfel | "Couldn't load today's menus" | "Something went wrong showing the menus", med felet i konsolen |
| **S1** – injicerat `onerror`/`onclick` i `#list` | körde | blockeras (`script-src-attr`); 0 överträdelser vid normal användning |

## Kvar att göra (inte åtgärdat)

- **A2:** tidszon och valuta, när `models.py` finns.
- **A3:** ett `source`-fält i `config.yaml`, som första steget i scraper-arbetet.
- **A4:** ett maskinläsbart schema, och `price` som får vara `null` i kontraktet.
- **A5:** grundfilerna för scraper-delen. YAML-beroendet behöver godkännas först.
- **S3:** `--bind 127.0.0.1` i CLAUDE.md. Det är din fil, så den ändras inte utan att du säger till.
- **K2–K5:** dela `renderHeader`, bättre namn och en läsbar `style.css`.
