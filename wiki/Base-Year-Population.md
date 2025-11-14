## 1 Overview

The population data for the base year, broken down by race, sex, and single year of age, initiates the main forecast program. The program uses the base year population data to generate forecasted data for the subsequent increment which then serves as the base for generating the forecast for the following increment.

## 2 Input Datasets
### Launch Years 2020+
Due to issues with the 2020 Census, a blended approach is used instead of the decennial Census to create the base year 2020 population for launch years occurring on or after 2020.
* [2016-2020 5-year ACS PUMS person files](https://www.census.gov/programs-surveys/acs/microdata.html)
* [San Diego County population projections from CA DOF vintage 2020 (2021.7.14)](https://dof.ca.gov/forecasting/demographics/projections/)
* [2020 Census: DHC P5 Table](https://www.census.gov/data/tables/2023/dec/2020-census-dhc.html)
* [San Diego County population estimates from CA DOF (E-5 Population and Housing Estimates for Cities, Counties, and the State)](https://dof.ca.gov/forecasting/demographics/estimates/)
### Launch Years 2010-2019
**TBD**

## 3 Methods
### Launch Years 2020+
Sets base year to 2020. Creates a blended estimate of the total population distribution by race, sex, and single year of age using the 2016-2020 5-year PUMS persons file and the CA DOF population projections vintage 2020 (2021.7.14) controlled to the San Diego County population estimate from CA DOF for 2020 using the vintage of the chosen launch year.

* Creates blended estimate of population broken down by race, sex, and single year of age using the average of the 2016-2020 5-year ACS PUMS and vintage 2020 DOF projection populations for ages <= 90. Reverts to solely using the DOF projection population for ages > 90. This method ensures a balanced race, sex, and age distribution.
* Resulting population scaled within race categories to match the 2020 Census P5 table values for San Diego County.
* Population is then scaled such that the total population matches the San Diego County population estimate from CA DOF for 2020 using the vintage from the chosen launch year.

### Base/Launch Years 2010-2019
**TBD**

## 4 Repository Location
The main classes, methods, and utilities associated with generating the base/launch year population are contained in **python/input_modules/base_yr.py**.