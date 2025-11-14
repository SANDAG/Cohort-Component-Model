## 1 Overview
Crude group quarters and household formation rates calculated within race, sex, and single year of age for each increment from the base year up to the launch year.

## 2 Input Datasets
* [5-year ACS PUMS persons files](https://www.census.gov/programs-surveys/acs/microdata.html)
* [SANDAG's Estimates Program](https://opendata.sandag.org/stories/s/SANDAG-Estimates-PDF-Reports/mire-zdsi/)

## 3 Methods
* Take the increment year 5-year ACS PUMS persons file for the San Diego region, scaling the head of household, group quarters, and total population to match the control totals for the increment year from SANDAG's Estimates program using the version from the chosen launch year.
* If there exists any race, sex, and single year of age categories where the group quarters population exceeds the total population, set the group quarters population to the total population and distribute the excess group quarters population proportionately within categories where the group quarters population is less than the total population. Repeat this process until no category has group quarters population that exceeds the total population.
* If there exists any race, sex, and single year of age categories where the head of household population exceeds the total household population, set the head of household population to the total household population and distribute the excess head of household population proportionately within categories where the head of household population is less than the total household population. Repeat this process until no category has head of household population that exceeds the total household population.
* For single year of age categories 70 years and below, calculate the group quarters and household formation (head of household) rates.
* For single year of age categories above 70 years
  * Calculate the group quarters rate within sex combining all races and ages and apply this uniform rate to all ages above 70 years
  * Calculate the household formation rate within race and sex combining all ages and apply this uniform rate to all ages above 70 years
* Finally, if there exists any race, sex, and single year of age categories such that the sum of the group quarters and household formation rates exceeds one, proportionately adjust the group quarters and household formation rates within those categories such that that sum is equal to one.

## 4 Repository Location
The main classes, methods, and utilities associated with creating crude group quarters and household formation rates are contained in **python/input_modules/formation_rates.py**