# CLAUDE.md – Dagens lunch

## Vad projektet gör

En öppen mall för en "dagens lunch"-sajt för ett kontor. Sajten visar alla restauranger
inom gångavstånd och vad de serverar till lunch i dag, med filter (vegetariskt, fisk,
kött, buffé) och sortering (närmast, billigast).

**Problemet:** Varje lunch går åt till att öppna fem flikar, Instagram-konton och
restaurangsidor för att se vad som finns. Menyerna ligger utspridda, i olika format och
uppdateras olika.

**Lösningen:** Ett kontor forkar repot, fyller i `config.yaml` med sin adress och sina
restauranger, och får en egen sajt på GitHub Pages. Menyerna hämtas automatiskt varje
vardagsmorgon. Ingen server, ingen databas, ingen kostnad.

Första installationen är Consid Malmö (Stortorget 29), men ingenting i koden får vara
specifikt för den.

## Teknikstack

| Del | Val | Varför |
| --- | --- | --- |
| Menyhämtning | Python 3.12+, `httpx`, `selectolax` | Min vardagsstack; snabb HTML-parsning utan tung browser |
| Schemaläggning | GitHub Actions (cron, vardagar ~10:00 svensk tid) | Gratis, ingen egen server, loggar per körning |
| Data | `docs/data/menus.json` (+ arkiv per datum) | Statisk fil = sajten fungerar utan backend |
| Frontend | Ren HTML/CSS/JS (ingen build, inget ramverk) i `docs/` | GitHub Pages serverar direkt; lätt för andra att förstå |
| Hosting | GitHub Pages | Alla som forkar får en URL direkt |
| Tester | `pytest` med sparade HTML-fixtures | Scrapers testas utan nätverk |
| Lint/format | `ruff` | Ett verktyg för båda |

## Arkitektur

```
config.yaml ──► scraper/ (Python) ──► docs/data/menus.json ──► docs/ (statisk sajt)
                   ▲                          ▲
          GitHub Actions cron          committas av Actions
```

```
scraper/
  config.py        # läser och validerar config.yaml
  models.py        # dataclasses: Restaurant, Dish, MenuEntry, DailyMenu
  sources/         # en modul per källtyp (html, json-api, instagram-länk, …)
    base.py        # gemensamt Source-protokoll: fetch(restaurant, date) -> MenuEntry
  normalize.py     # rätt-typ (meat/fish/veg/buffet/other), pris, rensning av text
  build.py         # kör alla källor, skriver menus.json
tests/
  fixtures/        # sparad HTML per källa
docs/              # GitHub Pages-roten: index.html, app.js, style.css, data/
config.yaml
```

## Arkitekturprinciper

- **All nätverks-I/O sker i `scraper/sources/`.** `normalize.py` och `build.py` är rena
  funktioner: data in, data ut.
- **En källa som går sönder får aldrig stoppa de andra.** Varje källa körs isolerat; fel
  loggas och restaurangen markeras `status: "error"` i JSON, de övriga skrivs ändå.
- **Ingen kontorsspecifik data i koden.** Adresser, koordinater, restauranger och URL:er
  hör hemma i `config.yaml`.
- **Nya källtyper följer `Source`-protokollet** i `sources/base.py` – ingen if-kedja per
  restaurang.
- **JSON-formatet är ett kontrakt** mellan scraper och frontend. Ändras det: uppdatera
  `docs/app.js`, schemat i `scraper/models.py` och ett test i samma commit.
- **Funktioner gör en sak** och har typannoteringar. Inga globala muterbara variabler.
- **Varje scraper har ett test mot en sparad fixture**, så vi märker när en sajt byter
  layout.
- **Frontend fungerar utan JavaScript-ramverk**, laddar en JSON-fil och har inga
  externa anrop utöver den.
- **Respektera restaurangernas sajter:** ett anrop per restaurang och dag, tydlig
  User-Agent, följ robots.txt.

## Saker agenten INTE ska göra

- Lägg inte till en backend, databas eller server (Supabase, Firebase, Flask osv.).
  Röstning/"jag går dit" är medvetet utanför scope för v1.
- Lägg inte till externa beroenden (Python eller JS) utan att fråga först.
- Inför inte ett frontend-ramverk eller byggsteg (React, Vite, Tailwind-build osv.).
- Använd inte headless browser (Playwright/Selenium) i scrapern utan att fråga – det gör
  Actions-körningen långsam och skör.
- Hårdkoda aldrig Consid, Malmö eller Stortorget i kod – bara i `config.yaml`.
- Skrapa inte Instagram eller sajter som förbjuder det i robots.txt; länka till källan
  istället (`status: "link"`).
- Ändra inte JSON-formatet i `menus.json` utan att uppdatera frontend och tester.
- Committa inte API-nycklar eller hemligheter; använd GitHub Actions secrets.
- Pusha inte direkt till `main` vid större ändringar – gör en branch och beskriv ändringen.

## Kommandon

```bash
pip install -e ".[dev]"       # installera
pytest                        # kör tester
ruff check . && ruff format . # lint + format
python -m scraper.build       # hämta dagens menyer lokalt -> docs/data/menus.json
python -m http.server -d docs # förhandsgranska sajten på localhost:8000
```

## Definition of done för v1

- [ ] `config.yaml` med minst 10 restauranger kring Stortorget 29
- [ ] Minst 6 restauranger hämtas automatiskt; resten visas med länk till menyn
- [ ] GitHub Action kör vardagar och committar `menus.json`
- [ ] Sajten live på GitHub Pages, fungerar på mobil
- [ ] README med "Sätt upp för ditt kontor på 10 minuter"
- [ ] Tester för varje scraper, grön CI
