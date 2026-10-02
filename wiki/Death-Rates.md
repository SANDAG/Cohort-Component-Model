This module generates mortality rates by single year of age, sex, and race/ethnicity for each increment year. Post-launch year rates are optionally adjusted from launch year rates to match asserted mortality rates.

# Inputs
| Input | Module Source | Usage |
| ----- | ------------- | ----- |
| 1999-2020 CDC WONDER Mortality | [CDC WONDER ucd-icd10: 1999-2020: Underlying Cause of Death by Bridged-Race Categories](https://wonder.cdc.gov/ucd-icd10.html) | Provides death counts for years 1999-2020 |
| 2018-2024 CDC WONDER Mortality | [CDC WONDER ucd-icd10-expanded: 2018-2024: Underlying Cause of Death by Single-Race Categories](https://wonder.cdc.gov/ucd-icd10-expanded.html) | Provides death counts for years 2022-2024 |
| Launch Year Population | [Launch Year Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population) | Population used to supplement missing population within the CDC WONDER mortality database for San Diego County in years 2022 and beyond |   
| UN DESA Life Table Survivors | [UN DESA Life Table Survivors](https://population.un.org/wpp/downloads?folder=Standard%20Projections&group=Mortality) | Provides number of life table survivors which are then used to calculate mortality rates for ages 85-99 |
| Mortality Forecasting | User-Input (Optional) | Optional CSV file of asserted mortality forecasts for each year |

## Launch Year Population
See [Launch Year Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population).

## Mortality Forecasting (Optional)
An optional user defined CSV file containing forecasted mortality rates. If provided, the CSV should include one row per increment year, post-launch year, sex, and race/ethnicity. See the [README.md](https://github.com/SANDAG/Cohort-Component-Model/blob/main/README.md) for more information regarding the file structure and how to update the configuration file.

# Outputs
## Mortality Rates
For ages under 85, mortality rates are calculated using CDC WONDER as deaths divided by population for each single year of age, sex, and race/ethnicity. The calculation starts with San Diego County data and, when a value is suppressed or zero, substitutes data from larger geographies (California, then the United States). This approach reduces missing records and avoids unrealistic 0% death rates. Because 2021 data are missing, 2020 data are used instead. Due to a product change in the CDC WONDER Mortality database, population for years 2022 and beyond are missing for San Diego County, and will be substituted with the Launch Year Population. CDC WONDER Mortality data is limited up to 2024 and subsequent launch years will use 2024 data.
For ages 85 and older, the United Nations Department of Economic and Social Affairs (UN DESA) Life Table Survivors dataset is used instead. Because this dataset is stratified only by age and sex, a scaling factor is applied to estimate age-, sex-, and race/ethnicity-specific mortality rates. A scaling factor is then derived by comparing implied mortality rates for ages 85 and older from CDC WONDER and solving for the value that aligns the UN DESA implied rate with CDC WONDER. UN DESA data is limited up to 2023 and subsequent launch years will use 2023 data. 
Post-launch year, rates are optionally adjusted to use asserted mortality rates, if provided.
