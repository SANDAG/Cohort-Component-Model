## 1 Overview
Crude in/out migration rates are calculated within race, sex, and single year of age for each increment from the base year up to the launch year.
* **TBD - Allow users to set either in/out or net migration control totals for each increment.**

## 2 Input Datasets
* [5-year ACS PUMS persons files](https://www.census.gov/programs-surveys/acs/microdata.html)
* Population data broken down by race, sex, and single year of age

## 3 Methods
* Migration rates are calculated using the increment year 5-year ACS PUMS person files removing active-duty military and selecting the counts of both foreign and domestic migrants into and out of San Diego County. It is important to note that no distinction is made between foreign and domestic migration.
* The counts of in/out migrants are merged with the total population and crude in/out migration rates are calculated simply as total in/out migrants divided by the non-military population. Migration rates >20% are then set to 20% within race, sex, and single year of age categories. This is a legacy carry-over from the [Series 15 Cohort Component Model](https://github.com/SANDAG/Cohort-Component-Model---SR15), per Population Reference Bureau recommendation, and was implemented due to small sample size issues within categories and the lack of a rate smoothing utility.

## 4 Repository Location
The main classes, methods, and utilities associated with creating crude birth rates are contained in **python/input_modules/migration_rates.py**