This module generates fertility rates by single year of age and race/ethnicity for each increment year. Post-launch year rates are optionally adjusted from launch year rates to match asserted fertility rates.

# Inputs
| Input | Module Source | Usage |
| ----- | ------------- | ----- |
| 2007-2024 CDC WONDER Natality | [CDC WONDER natality-current: Natality, 2007-2024](https://wonder.cdc.gov/natality-current.html) | Provides fertility rates for years 2007 to 2019 |
| 2016-2024 CDC WONDER Natality | [CDC WONDER natality-expanded-current: Natality, 2016-2024 expanded](https://wonder.cdc.gov/natality-expanded-current.html) | Provides fertility rates for years 2020 to 2024 |
| Forecasted Fertility Rates | User-Input (Optional) | Optional CSV file of asserted fertility rate forecast for each increment year post-launch |

## 2007-2024 CDC WONDER Natality
The fertility rates for 2007 to 2019 are calculated from the Centers for Disease Control and Prevention (CDC) WONDER Natality 2007-2024 database by age group and race/ethnicity. This database is used in tandem with subsequent CDC natality databases to create a historical time series spanning 2007 onward. Because the `Non-Hispanic, Hawaiian or Pacific Islander` and `Non-Hispanic, Two or More Races` categories are not broken out prior to 2020, their rates for 2007-2019 are instead manufactured from all of the races.

## 2016-2024 CDC WONDER Natality
The fertility rates for 2020 and onward are calculated from the Centers for Disease Control and Prevention (CDC) WONDER Natality 2016-2024 database by age group and race/ethnicity. This database is used in tandem with preceding CDC natality databases to create a historical time series spanning 2007 onward. 

## Forecasted Fertility Rates (Optional)
An optional user-defined CSV file containing forecasted fertility rates. If provided, the CSV should include one row per post-launch increment year, single year of age (for ages 15-44), sex (female), and race/ethnicity combination. See the [README.md](https://github.com/SANDAG/Cohort-Component-Model/blob/main/README.md) for more information regarding the file structure and how to update the configuration file. 

# Outputs
## Fertility Rates
Fertility Rates are calculated using the CDC WONDER natality datasets for age groups and then uniformly assigned to single years of age within that age group and inflated to account for the % of births attributed to `Not Stated`, `Unknown`, `Not Reported`, `Not Available` or belonging to age groups `Under 15 years`, `45-49 years`, and `50 years and over`. Missing San Diego County data is substituted with data from larger geographies (California, then the United States). CDC WONDER Natality data is limited up to 2024 and subsequent launch years will use 2024 data. Post-launch year, asserted fertility rates are used if provided.

*See the **python/input_modules/birth_rates.py** file and **sql/fertility** folder for underlying code used by the module.*
