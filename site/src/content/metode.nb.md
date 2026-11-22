## Hva siden viser

Siden viser **netto kapitalstrømmer** for de 20 største økonomiene, Norge og euroområdet. Tallene kommer fra betalingsbalansens *finansregnskap*, slik landene rapporterer det til Det internasjonale pengefondet (IMF) etter standarden BPM6.

Finansregnskapet registrerer transaksjoner mellom innenlandske og utenlandske aktører i finansielle eiendeler og forpliktelser: kjøp og salg av aksjer, obligasjoner, eierandeler i selskaper, lån og innskudd.

## Fortegn: positivt betyr innstrømning

I BPM6 er netto finansregnskap = netto erverv av fordringer på utlandet − netto pådrag av forpliktelser overfor utlandet. Positivt betyr der at landet låner ut til resten av verden.

Denne siden snur fortegnet: **positivt tall = netto innstrømning** av kapital, og **negativt tall = netto utstrømning**. Konverteringen skjer på ett sted i koden, og rådataene lagres med IMFs opprinnelige fortegn.

## Ekskludert reserver

Standardvisningen utelater **reserveaktiva**, altså sentralbankens kjøp og salg av valutareserver. Det gjør det lettere å se de øvrige strømmene. Tallet er ikke det samme som «private kapitalstrømmer», fordi også stat og offentlige fond inngår. Du kan inkludere reservene i oversikten.

For Russland publiserer ikke IMF tallet uten reserver fra 2022. Da beregner vi det som finansregnskapet totalt minus reserveaktiva, og merker verdiene med †.

## Komponenter

- **Direkteinvesteringer:** eierandeler på minst 10 % og lån innad i konsern.
- **Portefølje:** aksjer, fondsandeler og obligasjoner.
- **Annen investering:** banklån, innskudd, handelskreditt.
- **Derivater:** finansielle derivater. Noen land rapporterer dem ikke separat.
- **Reserver:** sentralbankens reserveaktiva.

Komponentene summerer til finansregnskapet totalt. Pipelinen kontrollerer dette hver uke.

## Netto og brutto

En netto utstrømning kan skyldes at innenlandske investorer kjøper mer i utlandet, og trenger ikke bety at utlendinger trekker seg ut. Landsidene viser derfor begge sider: utlendingers netto investeringer i landet og innenlandske aktørers netto investeringer i utlandet.

Siden tolker ikke tallene automatisk. Den bruker for eksempel ikke ordet «kapitalflukt».

## Strømmer, ikke beholdninger

Alle tall er **strømmer**, altså transaksjoner i en periode. Endringer i beholdninger påvirkes også av kurser og valuta, og brukes aldri som erstatning for strømmer.

## Perioder og sammenlignbarhet

- **Siste felles kvartal** er det nyeste kvartalet minst 80 % av de 20 største økonomiene har rapportert. Rangeringen bruker dette, så alle land sammenlignes over samme periode.
- **Siste fire kvartaler** er summen av fire kvartaler til og med siste felles kvartal. Dette er standardvisningen.
- **Nyeste per land** viser hvert lands nyeste tall, og er derfor mindre sammenlignbart.
- Land uten data for perioden vises som «ikke rapportert», aldri som null.

## Andel av BNP

BNP er IMFs årlige BNP i dollar fra World Economic Outlook. Hvert kvartal får en fjerdedel av sitt års BNP. Firekvartalssummer deles derfor på BNP for de samme kvartalene. Enkeltkvartaler blir annualisert. BNP for inneværende år er et IMF-anslag.

## Utvalget

De 20 største økonomiene etter BNP i **referanseåret**, som er siste hele år med data. Listen låses for referanseåret og regnes automatisk ut på nytt når et nytt år er komplett. Euroområdet vises som eget aggregat og summeres aldri med medlemslandene.

## Kart

Kartet viser samme tall som rangeringen, som farge per land. Standard er andel av BNP, fordi store land ellers dominerer. Kartet viser hvert lands netto kapitalstrøm mot resten av verden, ikke strømmer mellom land. Euroområdet er et aggregat og tegnes ikke.

## Nåkast

Nåkast-siden viser ferskere indikatorer fra nasjonale kilder: amerikanske verdipapirkjøp (US Treasury, TIC, månedlig), euroområdets betalingsbalanse (ECB, månedlig) og japanske verdipapirkjøp (finansdepartementet, ukentlig). De dekker bare deler av kapitalstrømmene, bruker egne valutaer og definisjoner, og er aldri med i rangeringen.

## Kryssjekk mot OECD

Hver uke sammenlignes IMF-tallene med OECDs betalingsbalanse for de siste åtte kvartalene. Avvik over 5 % og 0,5 mrd. USD vises på datakvalitet-siden. Aggregater som euroområdet sammenlignes ikke, fordi IMF og OECD setter dem sammen ulikt.

## Usikkerhet og revisjoner

- Betalingsbalansetall **revideres**, ofte betydelig, de første årene etter publisering. Store revisjoner logges i repoet.
- **Feil og utelatelser** fanger opp avvik mellom driftsbalansen og finansregnskapet. Store verdier gjør tallene mer usikre.
- **Finanssentre** som Nederland og Sveits har store strømmer gjennom selskaper uten egen virksomhet, noe som kan blåse opp direkteinvesteringene.

## Oppdatering

Dataene hentes automatisk fra IMF hver mandag. De publiseres bare når noe er endret, og hver endring kan spores i git-historikken. Hele koden er åpen.

## Kilder og vilkår

Source: International Monetary Fund, Balance of Payments (BOP), [https://data.imf.org/en/datasets/IMF.STA:BOP](https://data.imf.org/en/datasets/IMF.STA:BOP)

Source: International Monetary Fund, World Economic Outlook (WEO), [https://data.imf.org/en/datasets/IMF.RES:WEO](https://data.imf.org/en/datasets/IMF.RES:WEO)

OECD (2026), Balance of payments (DSD_BOP@DF_BOP), [https://data-explorer.oecd.org/](https://data-explorer.oecd.org/) – brukt til kryssjekk.

Nåkast: U.S. Department of the Treasury (TIC), European Central Bank (BPS) og Ministry of Finance Japan (International Transactions in Securities).

Kart: Natural Earth via world-atlas (offentlig eiendom).

Dataene gjengis etter kildenes vilkår. Siden er ikke laget av eller godkjent av IMF, OECD, ECB, US Treasury eller det japanske finansdepartementet.
