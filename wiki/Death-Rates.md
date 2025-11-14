## 1 Overview
Crude death rates are calculated within race, sex, and single year of age for each increment from the base year up to the launch year.
* **TBD - Utility to grow/decay death rates to meet horizon year expectations.**

## 2 Input Datasets
* [Social Security Actuarial Life Table](https://www.ssa.gov/oact/STATS/table4c6.html)
* [CDC WONDER ucd-icd10: 1999-2020: Underlying Cause of Death by Bridged-Race Categories](https://wonder.cdc.gov/ucd-icd10.html)
* [CDC WONDER ucd-icd10-expanded: 2018-2021: Underlying Cause of Death by Single-Race Categories](https://wonder.cdc.gov/ucd-icd10-expanded.html)

## 3 Methods
* Death rates are calculated for ages < 85 from CDC WONDER by simply dividing raw deaths by population for each race, sex, and single year of age category after setting "Suppressed" raw deaths (values < 10) to values of 4.5 and 0 raw deaths to values of 1. This strategy avoids missing value records and implausible 0% death rates. The CDC WONDER data sources used for each base/launch year within race/ethnicity categories is shown below.
* For ages >= 85 the Social Security Actuarial Life Table is used for the chosen base/launch year, substituting the 2019 dataset for base/launch years 2020 and 2021 due to the outsize impact of COVID-19 on geriatric death rates. Note that there was no data published for 2012 or 2018 so those base/launch years default to the previous years of 2011 and 2017.

#### Table 1: CDC WONDER Exports
_Note there is preference given to using actual race/ethnicity category data when available (in 2018 the ucd-icd10-expanded becomes available), 5-year rates, and never including both 2020 and 2021 datasets together due to the outsize impact of COVID-19; in that respective order._
| Increment Year | Race/Ethnicity | File |
| :---------------:| :------------: | :--: |
| 2010-2017 | Hispanic | Hispanic or Latino; ucd-icd10; (2006-2013)-(2010-2017); Five Counties.txt |
| 2010-2017 | White alone | Non-Hispanic White; ucd-icd10; (2006-2013)-(2010-2017); California (06).txt |
| 2010-2017 | Black or African American alone | Non-Hispanic Black or African American; ucd-icd10; (2006-2013)-(2010-2017); Arizona (04), California (06), Oregon (41), Washington (53).txt |
| 2010-2017 | American Indian or Alaska Native alone | Non-Hispanic American Indian or Alaska Native; ucd-icd10; (2006-2013)-(2010-2017); National.txt |
| 2010-2017 | Asian alone | Non-Hispanic Asian or Pacific Islander; ucd-icd10; (2006-2013)-(2010-2017); Arizona (04), California (06), Oregon (41), Washington (53).txt |
| 2010-2017 | Native Hawaiian or Other Pacific Islander alone | All Origins and Races; ucd-icd10; (2006-2013)-(2010-2017); California (06).txt |
| 2010-2017 | Two or More Races | All Origins and Races; ucd-icd10; (2006-2013)-(2010-2017); California (06).txt |
| | | |
| 2018 | Hispanic | Hispanic or Latino; ucd-icd10; 2014-2018; Five Counties.txt |
| 2018 | White alone | Non-Hispanic White; ucd-icd10; 2014-2018; California (06).txt |
| 2018 | Black or African American alone | Non-Hispanic Black or African American; ucd-icd10; 2014-2018; Arizona (04), California (06), Oregon (41), Washington (53).txt |
| 2018 | American Indian or Alaska Native alone | Non-Hispanic American Indian or Alaska Native; ucd-icd10; 2014-2018; National.txt |
| 2018 | Asian alone | Non-Hispanic Asian or Pacific Islander; ucd-icd10; 2014-2018; Arizona (04), California (06), Oregon (41), Washington (53).txt |
| 2018 | Native Hawaiian or Other Pacific Islander alone | Non-Hispanic Native Hawaiian or Other Pacific Islander; ucd-icd10-expanded; 2018; National.txt |
| 2018 | Two or More Races | Non-Hispanic More than one race; ucd-icd10-expanded; 2018; National.txt |
| | | |
| 2019 | Hispanic | Hispanic or Latino; ucd-icd10; 2015-2019; Five Counties.txt |
| 2019 | White alone | Non-Hispanic White; ucd-icd10; 2015-2019; California (06).txt |
| 2019 | Black or African American alone | Non-Hispanic Black or African American; ucd-icd10; 2015-2019; Arizona (04), California (06), Oregon (41), Washington (53).txt |
| 2019 | American Indian or Alaska Native alone | Non-Hispanic American Indian or Alaska Native; ucd-icd10; 2015-2019; National.txt |
| 2019 | Asian alone | Non-Hispanic Asian or Pacific Islander; ucd-icd10; 2015-2019; Arizona (04), California (06), Oregon (41), Washington (53).txt |
| 2019 | Native Hawaiian or Other Pacific Islander alone | Non-Hispanic Native Hawaiian or Other Pacific Islander; ucd-icd10-expanded; 2018-2019; National.txt |
| 2019 | Two or More Races | Non-Hispanic More than one race; ucd-icd10-expanded; 2018-2019; National.txt |
| | | |
| 2020 | Hispanic | Hispanic or Latino; ucd-icd10; 2016-2020; Five Counties.txt |
| 2020 | White alone | Non-Hispanic White; ucd-icd10; 2016-2020; California (06).txt |
| 2020 | Black or African American alone | Non-Hispanic Black or African American; ucd-icd10; 2016-2020; Arizona (04), California (06), Oregon (41), Washington (53).txt |
| 2020 | American Indian or Alaska Native alone | Non-Hispanic American Indian or Alaska Native; ucd-icd10; 2016-2020; National.txt |
| 2020 | Asian alone | Non-Hispanic Asian or Pacific Islander; ucd-icd10; 2016-2020; Arizona (04), California (06), Oregon (41), Washington (53).txt |
| 2020 | Native Hawaiian or Other Pacific Islander alone | Non-Hispanic Native Hawaiian or Other Pacific Islander; ucd-icd10-expanded; 2018-2020; National.txt |
| 2020 | Two or More Races | Non-Hispanic More than one race; ucd-icd10-expanded; 2018-2020; National.txt |
| | | |
| 2021 | Hispanic | Hispanic or Latino; ucd-icd10; 2016-2020; Five Counties.txt |
| 2021 | White alone | Non-Hispanic White; ucd-icd10; 2016-2020; California (06).txt |
| 2021 | Black or African American alone | Non-Hispanic Black or African American; ucd-icd10; 2016-2020; Arizona (04), California (06), Oregon (41), Washington (53).txt |
| 2021 | American Indian or Alaska Native alone | Non-Hispanic American Indian or Alaska Native; ucd-icd10; 2016-2020; National.txt |
| 2021 | Asian alone | Non-Hispanic Asian or Pacific Islander; ucd-icd10; 2016-2020; Arizona (04), California (06), Oregon (41), Washington (53).txt |
| 2021 | Native Hawaiian or Other Pacific Islander alone | Non-Hispanic Native Hawaiian or Other Pacific Islander; ucd-icd10-expanded; 2018-2019, 2021; National.txt |
| 2021 | Two or More Races | Non-Hispanic More than one race; ucd-icd10-expanded; 2018-2019, 2021; National.txt |
| | | |
| 2022 | Hispanic | Hispanic or Latino; ucd-icd10; 2016-2020; Five Counties.txt |
| 2022 | White alone | Non-Hispanic White; ucd-icd10; 2016-2020; California (06).txt |
| 2022 | Black or African American alone | Non-Hispanic Black or African American; ucd-icd10; 2016-2020; Arizona (04), California (06), Oregon (41), Washington (53).txt |
| 2022 | American Indian or Alaska Native alone | Non-Hispanic American Indian or Alaska Native; ucd-icd10; 2016-2020; National.txt |
| 2022 | Asian alone | Non-Hispanic Asian or Pacific Islander; ucd-icd10; 2016-2020; Arizona (04), California (06), Oregon (41), Washington (53).txt |
| 2022 | Native Hawaiian or Other Pacific Islander alone | Non-Hispanic Native Hawaiian or Other Pacific Islander; ucd-icd10-expanded; 2018-2019, 2021-2022; National.txt |
| 2022 | Two or More Races | Non-Hispanic More than one race; ucd-icd10-expanded; 2018-2019, 2021-2022; National.txt |

## 4 Repository Location
The main classes, methods, and utilities associated with creating crude death rates are contained in **python/input_modules/death_rates.py**
