## 1 Overview
Crude birth rates are calculated within race and single year of age, restricted to females aged 15-44, for each increment from the base year up to the launch year.
* **TBD - Utility to grow/decay birth rates to meet horizon year expectations.**

## 2 Input Datasets
* [CDC WONDER natality-current: Natality, 2007-2024](https://wonder.cdc.gov/natality-current.html)
* [CDC WONDER natality-expanded-current: Natality, 2016-2024 expanded](https://wonder.cdc.gov/natality-expanded-current.html)
* Population data broken down by race, sex, and single year of age

## 3 Methods
* Fertility rates for San Diego County are provided by the CDC WONDER Natality.
* Rates are inflated to account for the % of births attributed to `Not Stated`, `Unknown`, `Not Reported`, `Not Available` or belonging to age groups `Under 15 years`, `45-49 years`, and `50 years and over`.

## 4 Repository Location
The main classes, methods, and utilities associated with creating crude birth rates are contained in **python/input_modules/birth_rates.py**