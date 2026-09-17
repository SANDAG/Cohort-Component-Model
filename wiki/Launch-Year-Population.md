The population data for the launch year, the last year of observed data used in forecast development, broken down by single year of age, sex, and race/ethnicity within population type (e.g. Household Population, Group Quarters - College, etc.). The program uses the launch year population data to generate forecasted data for the subsequent forecast increment year which then serves as the basis for generating the forecast for the following increment and so on.

# Inputs
| Input | Module Source | Usage |
| ----- | ------------- | ----- |
| Regional age/sex/ethnicity controls for total population | External (DOF) | Used to split age groups from SANDAG's Estimates Program into single of year of age |
| Population by age/sex/ethnicity by population type | External (SANDAG Estimates) | SANDAG's Estimates Program [Population by Age/Sex/Ethnicity](https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Age-Sex-Ethnicity) serves as the launch year population for the regional forecast 

## Regional age/sex/ethnicity controls for total population
The regional age/sex/ethnicity controls for total population are derived from the most recent [California Department of Finance (DOF) Projections](https://dof.ca.gov/forecasting/demographics/projections/) P-3 product available at the time.

## Population by age/sex/ethnicity by population type
[SANDAG's Estimates Program](https://github.com/SANDAG/Estimates-Program/wiki) has produced annual population and housing estimates since 1974. These estimates provide both internal and external customers with sub-jurisdiction-level information about population, housing, demographic, and household characteristics from a composite of data sources. The [population by age/sex/ethnicity](https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Age-Sex-Ethnicity) by population type (e.g. Household Population, Group Quarters - College, etc.) from SANDAG's Estimates Program serves as the launch year population for SANDAG's regional forecast.

# Outputs
## Population by Age/Sex/Ethnicity by Population Type
This module takes in SANDAG's Estimates Program population by age/sex/ethnicity by population type and applies single year of age distributions derived from the DOF regional age/sex/ethnicity controls within the age groups used by SANDAG's Estimates Program to create single year of age/sex/ethnicity by population type.

*See the **python/input_modules/launch_year.py** file and **sql/launch** folder for underlying code used by the module.*