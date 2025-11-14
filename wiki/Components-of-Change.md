## 1 Overview
Calculate the components of change and create the input population for the next increment from the base year up to the horizon year.

## 2 Input Datasets
* [Input Module Calculated Death Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Death-Rates)
* [Input Module Calculated Birth Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Birth-Rates)
* [Input Module Calculated Migration Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Migration-Rates)
* [Calculated Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Population-Calculator)

## 3 Methods
* Take the Calculated Population and calculate deaths by race, sex, and single year of age using the Input Module Calculated Death Rates. Death rates are applied only to the civilian (non-military) population as it is assumed the military population remains constant outside of pre-launch year controls. Deaths are integerized and reallocated such that their sum is preserved, and they do not exceed the civilian population for any race, sex, and single year of age record.
* Calculate births by race, sex, and single year of age using the Input Module Calculated Birth Rates. Birth rates are applied to the survived population (the military population plus the survived civilian population). Note that the survived civilian population is assigned birth rates for the next single year of age increment as the population ages through the annual cycle. The military population is not assumed to age as it is held constant. Births are integerized and reallocated such that their sum is preserved, and they do not exceed the survived population for any race, sex, and single year of age record.
* Calculate in/out migration by race, sex, and single year of age. Migration rates are applied to the survived civilian population. Note that the survived civilian population is assigned migration rates for the next single year of age increment as the population ages through the annual cycle. In/Out migrants are integerized and reallocated such that their sum is preserved, and that the out migrants do not exceed the survived civilian population for any race, sex, and single year of age record.
* To create the input population for the next increment, calculated births are used to create the age 0 newborn population applying an asserted split between male/female sex to assign sex to the newborn population. Deaths and out migrants are subtracted from and in migrants are added to the total population within race, sex, and single year of age records. The population is then aged to the next single year of age increment (capped at 110) while the military population is held constant. Note that the military population is reallocated here for records where the military population exceeds the total population, if this occurs.

## 4 Repository Location
The main classes, methods, and utilities associated with calculating the components of change and incrementing the population are contained in **python/annual_cycle.py**