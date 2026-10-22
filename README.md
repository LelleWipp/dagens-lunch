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
- `scraper/` – hämtar menyerna varje morgon *(under utveckling)*

## Status

- [x] Sajten, med 24 restauranger kring Stortorget i Malmö
- [ ] Automatisk menyhämtning via GitHub Actions
- [ ] Guide: sätt upp för ditt kontor på 10 minuter

Bygget görs med en AI-agent. Se [CLAUDE.md](CLAUDE.md) för projektets regler och arkitektur.
