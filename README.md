# Dagens lunch

En mall som ger vilket kontor som helst en egen sajt med dagens lunchmenyer inom
gångavstånd, uppdaterad automatiskt varje vardagsmorgon.

**Live:** https://lellewipp.github.io/dagens-lunch/ (första installationen: Consid Malmö)

Inga fler flikar, Instagram-konton och restaurangsidor vid lunch. Sajten samlar alla
lunchställen nära kontoret på ett ställe, med filter för vegetariskt, fisk, kött och buffé
och sortering på avstånd eller pris. Allt är statiskt: ingen server, ingen databas, ingen
kostnad.

## Så fungerar det

```
config.yaml ──► scraper (Python, GitHub Actions varje vardag) ──► docs/data/menus.json ──► GitHub Pages
```

- `config.yaml` – kontorets adress och restaurangerna som ska visas
- `docs/` – sajten (ren HTML/CSS/JS) som läser `docs/data/menus.json`
- `scraper/` – hämtar menyerna varje vardagsmorgon (GitHub Actions, `.github/workflows/scrape.yml`)

## Status

- [x] Sajten, med 24 restauranger kring Stortorget i Malmö
- [x] Automatisk menyhämtning via GitHub Actions: 15 av 24 restauranger (menydags.se, mylunch.se
      och fasta buffémenyer), övriga visas med länk eller under "No menu online"
- [ ] Guide: sätt upp för ditt kontor på 10 minuter

Bygget görs med en AI-agent. Se [CLAUDE.md](CLAUDE.md) för projektets regler och arkitektur.

## Lägg till eller ändra en restaurang

Lägg till ett `source`-block under restaurangen i `config.yaml`:

```yaml
  source:
    type: menydags          # menydags | mylunch | static | link
    url: https://www.menydags.se/restaurang/<namn>/lunch
```

Testa lokalt med `pip install -e ".[dev]"`, `pytest` och `python -m scraper.build`. Menyerna
hämtas sedan automatiskt vardagar kl. 09:47 (vintertid), och du kan köra hämtningen direkt under
Actions → "Hämta dagens menyer" → Run workflow.
