## What the site shows

The site shows **net capital flows** for the 20 largest economies, Norway and the euro area. The figures come from the *financial account* of the balance of payments, as countries report it to the International Monetary Fund (IMF) under the BPM6 standard.

The financial account records transactions between residents and non-residents in financial assets and liabilities: purchases and sales of shares, bonds, stakes in companies, loans and deposits.

## Sign: positive means inflow

In BPM6, the net financial account = net acquisition of foreign assets − net incurrence of foreign liabilities. Positive means the country lends to the rest of the world.

This site flips the sign: **positive = net inflow** of capital and **negative = net outflow**. The conversion happens in one place in the code, and raw data is stored with the IMF’s original sign.

## Excluding reserves

The default view leaves out **reserve assets**, the central bank’s purchases and sales of foreign exchange reserves. That makes the other flows easier to see. The figure is not the same as “private capital flows”, because government and public funds are also included. You can include reserves in the overview.

For Russia, the IMF does not publish the figure excluding reserves from 2022. We derive it as the total financial account minus reserve assets and mark those values with †.

## Components

- **Direct investment:** stakes of at least 10% and lending within corporate groups.
- **Portfolio:** shares, fund units and bonds.
- **Other investment:** bank loans, deposits, trade credit.
- **Derivatives:** financial derivatives. Some countries do not report them separately.
- **Reserves:** the central bank’s reserve assets.

The components add up to the total financial account. The pipeline checks this every week.

## Net and gross

A net outflow can mean that residents buy more abroad; it does not have to mean that foreigners are pulling out. The country pages therefore show both sides: non-residents’ net investment in the country and residents’ net investment abroad.

The site does not interpret the figures automatically. It does not, for example, use the term “capital flight”.

## Flows, not positions

All figures are **flows**, meaning transactions within a period. Changes in positions are also driven by prices and exchange rates, and are never used as a substitute for flows.

## Periods and comparability

- **Latest common quarter** is the newest quarter that at least 80% of the 20 largest economies have reported. The ranking uses it, so all countries are compared over the same period.
- **Last four quarters** is the sum of four quarters up to and including the latest common quarter. This is the default view.
- **Latest per country** shows each country’s newest figure and is therefore less comparable.
- Countries without data for the period are shown as “not reported”, never as zero.

## Share of GDP

GDP is the IMF’s annual GDP in US dollars from the World Economic Outlook. Each quarter gets a quarter of its year’s GDP, so four-quarter sums are divided by GDP for the same quarters. Single quarters are annualised. GDP for the current year is an IMF estimate.

## The selection

The 20 largest economies by GDP in the **reference year**, which is the last complete year with data. The list is locked for the reference year and recomputed automatically when a new year is complete. The euro area is shown as a separate aggregate and is never added to its member countries.

## Uncertainty and revisions

- Balance of payments data is **revised**, often substantially, in the first years after publication. Large revisions are logged in the repository.
- **Errors and omissions** capture the gap between the current account and the financial account. Large values make the figures less certain.
- **Financial centres** such as the Netherlands and Switzerland have large flows through companies with no real operations, which can inflate direct investment.

## Updates

Data is fetched automatically from the IMF every Monday. It is only published when something has changed, and every change can be traced in the git history. All code is open.

## Sources and terms

Source: International Monetary Fund, Balance of Payments (BOP), [https://data.imf.org/en/datasets/IMF.STA:BOP](https://data.imf.org/en/datasets/IMF.STA:BOP)

Source: International Monetary Fund, World Economic Outlook (WEO), [https://data.imf.org/en/datasets/IMF.RES:WEO](https://data.imf.org/en/datasets/IMF.RES:WEO)

The data is reproduced under the IMF’s terms for statistical data. The site is not produced or endorsed by the IMF.
