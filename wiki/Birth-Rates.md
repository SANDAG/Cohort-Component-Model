## 1 Overview
Crude birth rates are calculated within race and single year of age, restricted to females aged 15-44, for each increment from the base year up to the launch year.
* **TBD - Utility to grow/decay birth rates to meet horizon year expectations.**

## 2 Input Datasets
* [CDC WONDER natality-current: Natality, 2007-2022](https://wonder.cdc.gov/natality-current.html)
* [CDC WONDER natality-expanded-current: Natality, 2016-2022 expanded](https://wonder.cdc.gov/natality-expanded-current.html)
* Population data broken down by race, sex, and single year of age

## 3 Methods
* Birth rates are calculated using CDC WONDER Natality births for 5-year age groups ranging from ages 15 to 44 setting "Suppressed" raw births (values < 10) to values of 4.5 and dividing the raw births by three, as 3-years of births are always from CDC WONDER.
* Births are merged with the population (aggregated to 5-year age groups), inflated to account for the % of births attributed to "unknown" race/ethnicity groups, and then QC'ed to ensure no race or 5-year age group contains 0 births or births greater than the total population within the category. Note that no inflation factor is made to account for births assigned to under 15 or 45+ age groups that are excluded.
* Crude birth rates are then calculated simply as births divided population within race and 5-year age groups and assigned back to single year of age groups.

#### Table 1: CDC WONDER Exports
_Pre-2018, the Non-Hispanic Native Hawaiian or Other Pacific Islander and Non-Hispanic More than one race categories do not exist (in 2016 the natality-expanded-current becomes available so 2018 is the first year 3-years of births are available). Therefore, average birth rates across all race/ethnicity groups are assigned to these categories. Note that the Non-Hispanic Asian birth rate is likely inflated (due to including Non-Hispanic Native Hawaiian or Other Pacific Islander births) as are all other Non-Hispanic race/ethnicity groups (due to including Non-Hispanic More than one race births)._

| Increment Year | Race/Ethnicity | File |
| :---------------:| :------------: | :--: |
| 2010-2017 | Hispanic | Hispanic or Latino; natality-current; (2008-2015)-(2010-2017); San Diego County.txt |
| 2010-2017 | White alone | Non-Hispanic White; natality-current; (2008-2015)-(2010-2017); San Diego County.txt |
| 2010-2017 | Black or African American alone | Non-Hispanic Black or African American; natality-current; (2008-2015)-(2010-2017); San Diego County.txt |
| 2010-2017 | American Indian or Alaska Native alone | Non-Hispanic American Indian or Alaska Native; natality-current; (2008-2015)-(2010-2017); San Diego County.txt |
| 2010-2017 | Asian | Non-Hispanic Asian or Pacific Islander; natality-current; (2008-2015)-(2010-2017); San Diego County.txt |
| 2010-2017 | Native Hawaiian or Other Pacific Islander alone | None |
| 2010-2017 | Two or More Races | None |
| 2010-2017 | Missing Ethnicity | Missing Ethnicity All Race; natality-current; (2008-2015)-(2010-2017); San Diego County.txt |
| 2010-2017 | Missing Race| All Ethnicity Missing Race; natality-current; (2008-2015)-(2010-2017); San Diego County.txt |
| | | |
| 2018-2022 | Hispanic | Hispanic or Latino; natality-expanded-current; (2016-2020)-(2018-2022); San Diego County.txt |
| 2018-2022 | White alone | Non-Hispanic White; natality-expanded-current; (2016-2020)-(2018-2022); San Diego County.txt |
| 2018-2022 | Black or African American alone | Non-Hispanic Black or African American; natality-expanded-current; (2016-2020)-(2018-2022); San Diego County.txt |
| 2018-2022 | American Indian or Alaska Native alone | Non-Hispanic American Indian or Alaska Native; natality-expanded-current; (2016-2020)-(2018-2022); San Diego County.txt |
| 2018-2022 | Asian alone | Non-Hispanic Asian; natality-expanded-current; (2016-2020)-(2018-2022); San Diego County.txt |
| 2018-2022 | Native Hawaiian or Other Pacific Islander alone | Non-Hispanic Native Hawaiian or Other Pacific Islander; natality-expanded-current; (2016-2020)-(2018-2022); San Diego County.txt |
| 2018-2022 | Two or More Races | Non-Hispanic More than one race; natality-expanded-current; (2016-2020)-(2018-2022); San Diego County.txt |
| 2018-2022 | Missing Ethnicity | Missing Ethnicity All Race; natality-expanded-current; (2016-2020)-(2018-2022); San Diego County.txt |
| 2018-2022 | Missing Race| All Ethnicity Missing Race; natality-expanded-current; (2016-2020)-(2018-2022); San Diego County.txt |

## 4 Repository Location
The main classes, methods, and utilities associated with creating crude birth rates are contained in **python/input_modules/birth_rates.py**