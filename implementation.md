# Implementation – Hemuppgift 2, Del A

Refaktorering av frontend i `docs/` med Claude Code i ett planstyrt flöde:
analys → plan → granskning → implementation ett steg i taget → verifiering efter varje steg.

Branch: `refactor/frontend-cleanup` (11 commits, en per steg, inget direkt på `main`).

## Flödet

1. **Analys (ingen lösning).** Agenten läste hela kodbasen mot `CLAUDE.md`. Eftersom
   `scraper/`, `tests/` och `pyproject.toml` inte finns än, analyserade den både
   befintlig kod och hur grunden avviker från `CLAUDE.md`.
2. **Plan (ingen implementation).** Planen hade två delar. Del 1 var ren refaktorering
   där beteendet inte fick ändras. Del 2 var beteendeändringar (A–E) som jag fick välja
   bland, var för sig. Varje steg angav filer, ändring och ordning, och planen sa uttryckligen
   vad som *inte* skulle göras.
3. **Granskning.** Jag godkände del 1 och agentens rekommendationer för del 2.
   LICENSE lämnades åt mig.
4. **Implementation steg för steg.** Agenten stannade efter del 1 och väntade på mitt
   beslut om del 2 innan den fortsatte.
5. **Verifiering efter varje steg.** Se nedan.

## Vad identifierade agenten?

**Brott mot CLAUDE.md**
- Google Fonts laddades från `index.html`. Det bryter mot "inga externa anrop utöver
  `menus.json`" och skickar besökarnas IP-adresser till Google.
- Kontorsspecifika antaganden var hårdkodade: `Europe/Stockholm`, `"kr"`, språk och en
  footer-länk till originalrepot.
- Datan följde inte kontraktet. `edda` (bara Instagram) hade `status: "none"` i stället för
  `"link"`, och två restauranger ligger utanför `radius_m: 500` trots att sidan sa
  "24 lunch spots within 500 m".
- Frontend behandlade `error` och `link` som `none`. En trasig källa såg därför ut som en
  restaurang utan meny.

**Duplicerad logik**
- I `app.js` fanns sex dubbletter: adress/öppettider, favorit-taggen, avståndsformatet,
  länkar, `note || includes` och avståndssorteringen.
- Hela dark-temat var kopierat i `style.css`. Det ena blocket var dessutom död kod,
  eftersom `data-theme` aldrig sätts.
- Magiska tal (`80`, `500`, `1.3`, `99999`, `9999`) låg spridda i koden.

**Läsbarhet**
- `render()` gjorde fem saker.
- HTML byggdes med långa strängkonkateneringar och inline-styles.
- Variablerna hade enbokstavsnamn.
- Headern ritades om vid varje filterklick.

**Teknisk skuld framåt**
- Viktigast: `config.yaml` säger inte varifrån en meny hämtas. Ungefär 12 av 24 menyer kommer
  från samma två aggregatorer, och utan ett `source`-fält leder scrapern lätt till den
  if-kedja per restaurang som CLAUDE.md förbjuder.
- Det finns inget schema för JSON-kontraktet.
- Öppettider är fritext.
- Det saknas LICENSE, `.gitignore` och `pyproject.toml`.

## Vad gjordes

| Steg | Commit | Ändring | Beteende |
|---|---|---|---|
| 1 | `8d9b926` | Tog bort det döda dark-temablocket i CSS | oförändrat |
| 2 | `240df31` | Namngivna konstanter för magiska tal | oförändrat |
| 3 | `0fdd492` | Hjälpfunktioner för duplicerad renderingslogik | oförändrat |
| 4 | `7cf67c7` | `render()` uppdelad i små funktioner; headern ritas bara vid laddning | oförändrat |
| 5 | `955035d` | Beskrivande namn i stället för enbokstavsvariabler | oförändrat |
| 6 | `485b807` | Inline-styles flyttade till CSS-klasser | oförändrat visuellt |
| A | `6ccfd01` | Google Fonts bort, systemtypsnitt | typsnitten ändras |
| E | `6b70873` | `.gitignore` | – |
| C | `bf54844` | `edda` → `status: "link"` | data |
| B | `3e2f7ed` | `error` får taggen "Couldn't fetch today"; `link` får egen etikett | ny visning |
| D | `073c783` | "22 lunch spots within 500 m …, plus 2 further away." | ny text |

## Vad ville agenten göra som jag stoppade, och varför?

Jag strök ingenting i den slutliga planen. Det beror på att planen var avgränsad redan från
början, och följande lades medvetet utanför:

- **`source`-fält i `config.yaml`, JSON-schema och `models.py`.** Det hör till scraper-arbetet.
  Enligt CLAUDE.md får kontraktet inte ändras utan att `models.py` och tester uppdateras i
  samma commit, och de filerna finns inte än.
- **Tidszon, valuta och språk i config.** Det är en kontraktsändring av samma skäl.
- **Ett templating-bibliotek för HTML-strängarna.** Det hade krävt ett beroende eller
  byggsteg, vilket CLAUDE.md förbjuder.
- **Att översätta gränssnittet till svenska.** Det är ett produktbeslut och ingen refaktorering.
- **LICENSE.** Licensvalet är mitt.
- **Att dölja restauranger utanför radien (D).** Agenten föreslog bara att rätta texten.
  Vilka ställen som visas styrs av `config.yaml`.

Beteendeändringarna hölls dessutom isär från refaktoreringen, så att varje sådan ändring
krävde ett eget ja.

> *Egen reflektion (fyll i):* vad hade du stoppat om agenten fått köra fritt?

## Vad missade agenten?

- **Verifieringen var opålitlig från början.** Google Fonts-anropen nekades i
  agentens miljö med varierande timing, så skärmdumparna skilde sig mellan körningar. Det
  krävdes tre försök för att blockera dem stabilt. Det slutade med CDP:s `Fetch`-domän och en
  tolerans för brus i textkanterna.
- **Steg 1 gick förlorat en gång.** När baslinjen gjordes om från `main` återställde en
  `git checkout` den ändrade CSS-filen innan den hade committats. Agenten upptäckte det på
  att `git status` var tom och gjorde om steget.
- **Testdatan täckte inte alla kodvägar.** Den riktiga datan har ingen favorit utan
  meny, ingen restaurang utan avstånd och ingen `error`-status. Det upptäcktes först i
  steg 3. Då lades påhittad kantfallsdata till, och baslinjen gjordes om från `main`. Steg 1–2
  hade verifierats utan den, men de rörde inte de kodvägarna, och slutkontrollen täckte allt.
- **Saker som fortfarande inte är åtgärdade:**
  - Avståndsnoten nämner inte faktorn 1.3 för gångväg.
  - Favorit-taggen har en tooltip på korten men inte i listan "No menu online".
  - En restaurang utan adress får en tom rad.
  - `today` räknas bara ut när sidan laddas.
- **Typsnittsbytet (A) är inte kontrollerat i en riktig webbläsare.** Agentens miljö kunde
  aldrig ladda Google-typsnitten, så skärmdumparna visar inte skillnaden. Den måste
  kontrolleras manuellt.
- **Verifieringsverktyget är inte committat.** Det finns alltså fortfarande inga tester i
  repot.

## Hur beteendet verifierades

Det finns inga tester i projektet. Agenten byggde därför ett snapshot-verktyg som bara låg i
dess egen miljö och inte är committat. Verktyget körde headless Chrome via Chrome DevTools
Protocol, med Node 22 och utan nya beroenden.

1. Sajten serverades med `python -m http.server -d docs`.
2. För varje tillstånd sparades den renderade DOM:en för `#list`, `#nlist`, `#notice`,
   `#subline`, `#stamp`, knapparnas `aria-pressed` och `localStorage`:
   - Standardläget.
   - Varje filter för sig.
   - Två filter samtidigt, samt ett filter som slås av och på.
   - Sortering på pris och tillbaka till avstånd.
   - Sökning: träff på rätt, träff på restaurang och ingen träff.
   - En kombination av filter, sortering och sökning.
   - Sparade inställningar efter omladdning, samt ogiltiga inställningar.
   - Fyra tillstånd med påhittad kantfallsdata: favorit utan meny, saknat avstånd och adress,
     `link`/`error`, pris som sträng och en osäker `javascript:`-URL.
3. Skärmdumpar togs i ljust och mörkt läge, i mobil- och desktopbredd.
4. Separat kontrollerades tom restauranglista och saknad `menus.json` på både `main` och branchen.

**Kriterier:**
- **Del 1:** DOM:en skulle vara byte för byte identisk med `main`. I steg 6 gällde det med
  undantag för det avsedda bytet `style` → `class`. Skärmdumparna skulle vara identiska,
  bortsett från brus i textkanterna på färre än 1000 pixlar.
- **Del 2:** jämförelse mot föregående steg, och diffen fick bara innehålla den avsedda
  ändringen. Listan "No menu online" kontrollerades också visuellt i utfällt läge.

## Är projektet körbart efter implementationen?

Ja. Sidan laddar och renderar utan JavaScript-fel i alla 20 testade tillstånd.

Så här startar man den:

```bash
python -m http.server -d docs   # öppna http://localhost:8000
```

Python-delen (`pip install -e ".[dev]"`, `pytest`) går inte att köra än. Den har aldrig
funnits, och det är nästa steg enligt CLAUDE.md.
