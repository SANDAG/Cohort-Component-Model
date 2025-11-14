## 1 Overview
Calculate the group quarters, households, and household characteristics for an input population within race, sex, and single year of age for each increment from the base year up to the horizon year.

## 2 Input Datasets
* [Input Module Calculated Formation Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Formation-Rates)
* [Input Module Calculated Household Characteristics Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Household-Characteristics-Rates)
* Population data broken down by race, sex, and single year of age

## 3 Methods
* Take the increment year population and apply the group quarters formation rate to the total population, including the military population.
* Take the increment year population and apply the household formation rate to the total civilian (non-military) population.
* Apply the household characteristics rates to the formed households calculated in the prior step.

## 4 Repository Location
The main classes, methods, and utilities associated with calculating the households, household characteristics, and population are contained in **python/calculate_population.py**