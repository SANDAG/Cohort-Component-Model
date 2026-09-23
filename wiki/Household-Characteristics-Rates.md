This module generates household characteristics rates by single year of age, sex, and race/ethnicity for the launch year. At this time, household characteristics rates are held constant through the entirety of the forecast.

# Inputs
| Input | Module Source | Usage |
| ----- | ------------- | ----- |
| Launch Year Population | [Launch Year Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population) | Rates are applied to the regional forecast [Launch Year Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population) to check control totals and to integerize outputs within age/sex/ethnicity for the launch year |
| Formation Rates | [Formation Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Formation-Rates) | Launch year household formation rates are needed to generate total households to check controls and to integerize outputs within age/sex/ethnicity for the launch year |
| Household Characteristics Rates | External (ACS) | The ACS 5-year PUMS provides household characteristics rates by age/sex/ethnicity |
| Total Households by Characteristics | SANDAG's Estimates Program | SANDAG's Estimates Program [Household Characteristics](https://github.com/SANDAG/Estimates-Program/wiki/Household-Characteristics) are used to control household characteristics rates |

## Launch Year Population
See [Launch Year Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population).

## Formation Rates
See [Formation Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Formation-Rates).

## Household Characteristics Rates
The United States Census Bureau's American Community Survey (ACS) [Public Use Microdata Sample (PUMS)](https://www.census.gov/programs-surveys/acs/microdata.html) files provide household characteristics rates for San Diego County.

## Total Households by Characteristics
When household characteristics rates are applied to the [Launch Year Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population) households formed by applying household [Formation Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Formation-Rates), the rates are adjusted such that the total households formed within each characteristic are equal to the total households from SANDAG's Estimates Program [Household Characteristics](https://github.com/SANDAG/Estimates-Program/wiki/Household-Characteristics), if any such exists.

# Outputs
## Household Characteristics Rates
Household characteristics rates are calculated from the Census Bureau ACS 5-year PUMS by age group, sex, and ethnicity. The rates are then uniformly assigned to the launch year households across single year of age wthin each age group. They are then adjusted such that when applied they result in integer values within single year of age, sex, and ethnicity categories and that the regional totals equal the totals from SANDAG's Estimates Program and remain consistent with the launch year households within each category.
