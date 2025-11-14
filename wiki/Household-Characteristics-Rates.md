## 1 Overview
Crude household characteristics rates calculated within race, sex, and single year of age for each increment from the base year up to the launch year.

## 2 Input Datasets
* [5-year ACS PUMS persons files](https://www.census.gov/programs-surveys/acs/microdata.html)
* [SANDAG's Estimates Program](https://opendata.sandag.org/stories/s/SANDAG-Estimates-PDF-Reports/mire-zdsi/)

## 3 Methods
* Take the increment year 5-year ACS PUMS persons file for the San Diego region, scaling the head of household population and all household-related variables to match the total households for the increment year from SANDAG's Estimates program using the version from the chosen launch year. Additionally, for each characteristic, if there exists a SANDAG Estimate, the total number of households within the characteristic category is scaled to match the SANDAG Estimate.
* For race, sex, and single year of age categories with less than twenty households (but greater than zero), household characteristics rates within race, sex, and more aggregate age categories are used. These categories are; Under 16, 16-17, 18-24, 25-34, 35-49, 50-59, 60-70, and 71+.
* Finally, if there exists any race, sex, and single year of age categories such that the sum of characteristic rates that cover all households does not equal one, proportionately adjust those rates within those categories such that that sum is equal to one. For example, households by size (1, 2, 3+) would be a group of characteristic rates that cover all households and thus, should sum to 1.


## 4 Repository Location
The main classes, methods, and utilities associated with creating crude group quarters and household formation rates are contained in **python/input_modules/hh_characteristics_rates.py**