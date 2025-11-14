## 1 Overview
The Active-Duty military population is split out from the total population within race, sex, and single year of age. This is run after base year population data is generated and then for each subsequent increment year up to the launch year. The active-duty military population is then held constant for all subsequent increments past the launch year.

## 2 Input Datasets

### Increment Years 2018+
* Population data broken down by race, sex, and single year of age
* [5-year ACS PUMS persons files](https://www.census.gov/programs-surveys/acs/microdata.html)
* [SDMAC Military Economic Impact Report (MEIR)](https://sdmac.org/reports/past-sdmac-economic-impact-reports/)

### Increment Years 2010-2017
* Population data broken down by race, sex, and single year of age
* [5-year ACS PUMS persons files](https://www.census.gov/programs-surveys/acs/microdata.html)
* [DMDC Military and Civilian Personnel by Service/Agency by State/Country](https://dwp.dmdc.osd.mil/dwp/app/dod-data-reports/workforce-reports)

## 3 Methods

### Increment Years > Launch Year
* The active-duty military population is held constant for all subsequent increments past the launch year.

### Increment Years 2018+
* Take the total population and merge with the 5-year ACS PUMS persons files for the increment year active-duty military population within race, sex, and single year of age for the San Diego region.
* Scale the active-duty military population such that the total active-duty military population matches the total active-duty military population from the SDMAC MEIR for the increment year.
* If there exists any race, sex, and single year of age categories where the active-duty military population exceeds the total population, set the active-duty military population to the total population and distribute the excess active-duty military population proportionately within categories where the active-duty military population is less than the total population. Repeat this process until no category has active-duty military population that exceeds the total population.

### Increment Years 2010-2017
* Take the increment year 5-year ACS PUMS persons files active-duty military population within race, sex, and single year of age for the State of California. Scale the population such that the total active-duty military population matches the total active-duty military population from the DMDC Location Report for the increment year.
* Take the total population and merge with the scaled active-duty military population within race, sex, and single year of age for the San Diego region.
* If there exists any race, sex, and single year of age categories where the active-duty military population exceeds the total population, set the active-duty military population to the total population and distribute the excess active-duty military population proportionately within categories where the active-duty military population is less than the total population. Repeat this process until no category has active-duty military population that exceeds the total population.

## 4 Repository Location
The main classes, methods, and utilities associated with generating the base/launch year population and active-duty military sub-module are contained in **python/input_modules/active_duty_military.py**.