This module generates groups quarters and household formation rates by single year of age, sex, and race/ethnicity for the launch year. At this time, formation rates are held constant through the entirety of the forecast. Both "Group Quarters - Military" and "Group Quarters - Institutional Correctional Facilities" populations are excluded from this module and held constant from the launch year.

# Inputs
| Input | Module Source | Usage |
| ----- | ------------- | ----- |
| Launch Year Population | [Launch Year Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population) | Rates are applied to the regional forecast [Launch Year Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population) to check control totals and to integerize outputs within age/sex/ethnicity for the launch year |
| Group Quarters Formation Rates | SANDAG's Estimates Program | SANDAG's Estimates Program [Population by Type](https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Type) and [Population by Age/Sex/Ethnicity by Type](https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Age-Sex-Ethnicity) provide launch year group quarters formation rates |
Household Formation Rates | External (ACS) | The ACS 5-year PUMS provides household formation rates by age/sex/ethnicity |
Total Households | SANDAG's Estimates Program | The total households from SANDAG's Estimates Program [Housing and Households](https://github.com/SANDAG/Estimates-Program/wiki/Housing-and-Households) are used to control household formation rates |

## Group Quarters Formation Rates
[SANDAG's Estimates Program](https://github.com/SANDAG/Estimates-Program/wiki) has produced annual population and housing estimates since 1974. These estimates provide both internal and external customers with sub-jurisdiction-level information about population, housing, demographic, and household characteristics from a composite of data sources. The [population by age/sex/ethnicity](https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Age-Sex-Ethnicity) by population type (e.g. Household Population, Group Quarters - College, etc.) from SANDAG's Estimates Program provides group quarters formation rates directly to SANDAG's regional forecast.

## Household Formation Rates
The United States Census Bureau's American Community Survey (ACS) [Public Use Microdata Sample (PUMS)](https://www.census.gov/programs-surveys/acs/microdata.html) files provide household formation rates for San Diego County.

## Total Households
When household formation rates are applied to the [Launch Year Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population) household population the rates are adjusted such that the total households formed are equal to the total households from SANDAG's Estimates Program [Housing and Households](https://github.com/SANDAG/Estimates-Program/wiki/Housing-and-Households).

# Outputs
## Group Quarters Formation Rates
Group quarters formations rates are retrieved directly from SANDAG's Estimates Program by age group, sex, and ethnicity. The rates are then uniformly assigned to the launch year population across single year of age wthin each age group. They are then adjusted such that when applied within each single year of age, sex, and ethnicity category the resulting group quarters value is equal to the launch year population value. This ensure consistency between launch year group quarters populations and formation rates.

Only *Group Quarters - College* and *Group Quarters - Other* rates are calculated as the regional forecast assumes constant *Group Quarters - Military* and *Group Quarters - Institutional Correctional Facilities* populations for the entirety of the forecast.

## Household Formation Rates
Household formation rates are calculated from the Census Bureau ACS 5-year PUMS by age group, sex, and ethnicity. The rates are then uniformly assigned to the launch year population across single year of age wthin each age group. They are then adjusted such that when applied they result in integer values within single year of age, sex, and ethnicity categories and that the regional total equals the total households from SANDAG's Estimates Program.

*See the **python/input_modules/formation_rates.py** file and **sql/formation_rates** folder for underlying code used by the module.*