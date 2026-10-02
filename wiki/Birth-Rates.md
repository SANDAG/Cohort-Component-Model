This module generates fertility rates by single year of age and race/ethnicity for each increment year. Post-launch year rates are optionally adjusted from launch year rates to match asserted mortality rates.

# Inputs
| Input | Module Source | Usage |
| ----- | ------------- | ----- |
| 2007-2024 CDC WONDER Natality | [CDC WONDER natality-current: Natality, 2007-2024](https://wonder.cdc.gov/natality-current.html) | Provides fertility rates for years 2007 to 2019 |
| 2016-2024 CDC WONDER Natality | [CDC WONDER natality-expanded-current: Natality, 2016-2024 expanded](https://wonder.cdc.gov/natality-expanded-current.html) | Provides fertility rates for years 2020 to 2024 |

# Outputs
## Fertility Rates
Fertility rates for San Diego County are provided by the CDC WONDER Natality. Rates are inflated to account for the % of births attributed to `Not Stated`, `Unknown`, `Not Reported`, `Not Available` or belonging to age groups `Under 15 years`, `45-49 years`, and `50 years and over`. CDC WONDER Natality data is limited up to 2024 and subsequent launch years will use 2024 data. Post-launch year, rates are optionally adjusted to use asserted mortality rates, if provided.
