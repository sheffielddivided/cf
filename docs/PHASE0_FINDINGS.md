# Fase 0: funn og forslag

22.11.2026. Grunnlag: `docs/COVERAGE.md` og råsvarene på grenen `bot/phase0` (hentet av `phase0.yml` i GitHub Actions).

**Kort sagt:** IMF BOP dekker alt designet trenger. Alle 20 største økonomier har kvartalsdata fra 2010, og 19 av 20 har hovedmålet frem til 2026-K2. Seriekodene er funnet og verifisert. Tre små designjusteringer trenger godkjenning før fase 1, se nederst.

## API-et

- `https://api.imf.org/external/sdmx/3.0` svarer uten nøkkel, på 0,3–1 s per spørring. SDMX-CSV 2.0 er det enkleste formatet.
- BOP-dataflyten er `IMF.STA:BOP` versjon 21.0.0 med nøkkelen `COUNTRY.BOP_ACCOUNTING_ENTRY.INDICATOR.UNIT.FREQUENCY`. Flere koder i én dimensjon skrives med `+`.
- `OBS_VALUE` er i hele USD. Attributtet `SCALE` (6) gjelder bare visning.
- Tidsfilteret `c[TIME_PERIOD]=ge:2010-Q1` virker for BOP. WEO ignorerer det og gir alt fra 1980, noe som er ufarlig.
- OECD (`sdmx.oecd.org`) avviser `version=1.0.0` i Accept-headeren (HTTP 406), men godtar `version=1.0`. Strukturen for `DSD_BOP@DF_BOP` er hentet. Koblingen av OECD-seriene gjøres i fase 2.

## Seriekoder (i `config/series_map.yaml`)

| Måltall | IMF-indikator | Sider |
| --- | --- | --- |
| Finansregnskap totalt | `FAB` | netto |
| Finansregnskap ekskl. reserver | `FABXRRI` | netto |
| Direkteinvesteringer | `D_F` | netto, fordringer, gjeld |
| Portefølje | `P_F` (aksjer `P_F5`, gjeld `P_F3`) | netto, fordringer, gjeld |
| Annen investering | `O_F` | netto, fordringer, gjeld |
| Derivater | `F_F7` | netto |
| Reserver | `R_F` | netto (kun fordringer) |
| Driftsbalanse / kapitalkonto / feil og utelatelser | `CAB` / `KAB` / `EO` | netto |
| BNP i USD | WEO `NGDPD` | årlig |

**Verifisert:** `D_F + P_F + F_F7 + O_F + R_F = FAB` stemmer for **alle land og alle kvartaler** innen 0,5 mrd. USD eller 1 %.

## Utvalg og perioder

- Topp 20 etter BNP i 2025 er nøyaktig kandidatlisten i designet. Polen er nr. 21 med 1 040 mrd. USD, tett bak Sveits med 1 061 mrd. Taiwan er nr. 22, men finnes ikke i IMF BOP.
- **Siste felles kvartal er 2026-K2.** Brasil har allerede 2026-K3. Russland ligger bak, med siste kvartal 2026-K1.

## Hull og avvik

| Funn | Konsekvens |
| --- | --- |
| **Russland:** `FABXRRI` og `RUE` stopper i 2021-K4, mens `FAB` og `R_F` fortsetter til 2026-K1 | Hovedmålet mangler for Russland fra 2022. Se forslag 1 |
| `FABXRRI` ≠ `FAB − RUE` i enkelte kvartaler for 12 økonomier, blant annet Kina, Storbritannia og Saudi-Arabia | IMF behandler «related items» (ekstraordinær finansiering, IMF-kreditt) ulikt mellom land. Vi bruker `FABXRRI` slik IMF publiserer den. Komponentgrafen bruker `D/P/F7/O/R`, som summerer til `FAB` |
| Canada og Saudi-Arabia rapporterer ikke derivater separat | Vises som «ikke rapportert». Identiteten holder likevel |
| Kina: derivater først fra 2015-K1 | Merknad på landsiden |
| Irland (finanssenter) slutter i 2025-K4, og De forente arabiske emirater har bare årsdata | Ingen av dem er i topp 20 |
| Euroområdet (`G163`) | Komplett fra 2010-K1 til 2026-K2 |

## Kontrolltall (ikke publisert)

Netto innstrømning ekskl. reserver, sum 2025-K3 til 2026-K2, mrd. USD (positivt = innstrømning). Tallene brukes bare til å sjekke fortegn og størrelsesorden:

| Land | Mrd. USD | Land | Mrd. USD |
| --- | --- | --- | --- |
| USA | 1 270,9 | India | −9,0 |
| Storbritannia | 119,7 | Sveits | −29,7 |
| Brasil | 79,6 | Frankrike | −30,8 |
| Saudi-Arabia | 71,5 | Spania | −77,3 |
| Australia | 58,4 | Nederland | −85,7 |
| Tyrkia | 32,4 | Norge | −103,7 |
| Mexico | 10,2 | Tyskland | −216,0 |
| Indonesia | 7,5 | Sør-Korea | −239,2 |
| Italia | 0,9 | Japan | −266,4 |
| Canada | 0,1 | Euroområdet | −292,6 |
| | | Kina | −714,2 |

Bildet stemmer med kjente mønstre: USA finansierer driftsunderskuddet med kapitalinnstrømning, mens overskuddsland som Kina, Japan, Korea, Tyskland og Norge har netto utstrømning.

## Forslag til designjusteringer (trenger godkjenning)

1. **Russland fra 2022:** beregn `fa_ex_reserves = FAB − R_F`, merket `derived` og med en forklaring på landsiden. Alternativet er å vise Russland som «ikke rapportert» for hovedmålet.
2. **BNP-nevner:** bruk IMF WEO `NGDPD`, som er årlig. Firekvartals sum deles på BNP vektet etter hvilke år kvartalene tilhører. Kvartalsvis BNP i USD finnes ikke direkte hos IMF og måtte i så fall regnes om fra nasjonal valuta. 2026 er et WEO-estimat og merkes slik.
3. **Referanseår 2025** for topp 20 (satt i `config/countries.yaml`). Sveits og Polen ligger tett, så listen bør bare endres ved en bevisst beslutning.

## Neste steg (fase 1, etter godkjenning)

1. `pipeline update`: hent alle serier, lagre Parquet og kjør kvalitetskontrollene.
2. `update-data.yml` med ukentlig cron.
3. Eksport til JSON, deretter frontend.
