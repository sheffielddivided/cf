# Global Capital Flows

Åpen nettside som viser netto kapitalstrømmer inn og ut av verdens største økonomier, basert på offisiell betalingsbalansestatistikk (IMF BOP, BPM6). Ingen betalte datakilder, ingen server: data hentes av GitHub Actions og siden publiseres på GitHub Pages.

- Design og regler: [`docs/DESIGN.md`](docs/DESIGN.md)
- Nettside: https://sheffielddivided.github.io/cf/
- Status: fase 1 ferdig (ukentlig datajobb + nettside). Neste: fase 2.

## Kom i gang

```bash
uv sync
uv run pytest
uv run pipeline update        # krever tilgang til api.imf.org
cd site && npm ci && npm run dev   # http://localhost:4321/cf/
```

## Kilder og lisens

Koden er lisensiert under MIT (se `LICENSE`). Dataene tilhører kildene og følger deres vilkår (se `DATA_LICENSE.md`).

Source: International Monetary Fund, Balance of Payments (BOP), https://data.imf.org/en/datasets/IMF.STA:BOP
