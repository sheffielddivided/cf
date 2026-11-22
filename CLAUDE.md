# Prosjekt: Global Capital Flows (cf)

Les `docs/DESIGN.md` først. Den er fasit for definisjoner, datamodell og regler.
Skriv kode, identifikatorer og commit-meldinger på engelsk; dokumentasjon og UI-tekst på norsk (bokmål) med engelsk som andrespråk.

## Status
- Fase 0 (dekningsmatrise) pågår. Ikke start på frontend (`site/`) før fase 0 er levert og godkjent av eieren.

## Arbeidsmåte
- Jobb fase for fase. Én PR per avgrenset oppgave, med tester. Bruk GitHub Issues for oppgaver og funn.
- Gjett aldri SDMX-koder. Hent dem fra struktur-API-et (dataflow, DSD, kodelister) og legg dem i `config/series_map.yaml`.
- Hvis miljøet ditt ikke når `api.imf.org` / `sdmx.oecd.org` (f.eks. en sandkasse med nettverks-allowlist), kjør hentingen i GitHub Actions: `phase0.yml` kjører ved push som endrer `pipeline/` eller `config/`, og legger alt den hentet (råsvar, manifest, logg) på grenen `bot/phase0`. Hent med `git fetch origin bot/phase0`.

## Data
- IMF API: `https://api.imf.org/external/sdmx/3.0` (SDMX 3.0) og `https://api.imf.org/external/sdmx/2.1`. Ingen innlogging. Dataflow `IMF.STA:BOP`.
- IKKE bruk `dataservices.imf.org`. Den ble lagt ned i november 2025, og mange eksempler på nettet er utdaterte.
- Sett beskrivende User-Agent, bruk retry med backoff, og cache råsvar.
- Lagre alltid `value_raw` med kildens fortegn. Fortegnskonvertering skjer KUN i `pipeline.normalize.to_inflow_sign()`.
- Manglende data = `None`/null + `obs_status = "missing"`. Aldri 0.

## Regler som ikke kan brytes
- Positivt tall på siden = netto innstrømning.
- Standardvisning: siste fire kvartaler, ekskl. reserver, mrd. USD.
- Rangering bruker siste felles kvartal.
- Beholdninger presenteres aldri som strømmer. Høyfrekvente data blandes aldri inn i hovedrangeringen.
- Euroområdet summeres aldri med medlemslandene.
- Kildeangivelse på hver side: "Source: International Monetary Fund, Balance of Payments (BOP), <lenke>".

## Kommandoer
- `uv sync` – installer
- `uv run pipeline explore --out data/explore` – fase 0: utforsk IMF/OECD og lagre råsvar
- `uv run pytest` – tester
- `uv run ruff check .` – lint
