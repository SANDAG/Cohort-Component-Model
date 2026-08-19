## 1 Overview
Crude death rates are calculated within race, sex, and single year of age for each increment from the base year up to the launch year.
* **TBD - Utility to grow/decay death rates to meet horizon year expectations.**

## 2 Input Datasets
* [UN DESA Life Table Survivors](https://population.un.org/wpp/downloads?folder=Standard%20Projections&group=Mortality)
* [CDC WONDER ucd-icd10: 1999-2020: Underlying Cause of Death by Bridged-Race Categories](https://wonder.cdc.gov/ucd-icd10.html)
* [CDC WONDER ucd-icd10-expanded: 2018-2024: Underlying Cause of Death by Single-Race Categories](https://wonder.cdc.gov/ucd-icd10-expanded.html)

## 3 Methods
* For ages under 85, death rates are calculated using CDC WONDER as deaths divided by population for each race, sex, and single year of age. The calculation starts with San Diego County data and, when a value is suppressed or zero, substitutes data from larger geographies (California, then the United States). This approach reduces missing records and avoids unrealistic 0% death rates. The CDC WONDER sources used for each base and launch year by race/ethnicity are listed below. Because 2021 data are missing, 2020 data are used instead.
* For ages 85 and older, we use the United Nations Department of Economic and Social Affairs (UN DESA) Life Table Survivors dataset. Because this dataset is stratified only by age and sex, we apply a scaling factor to estimate age-, sex-, and race-specific mortality rates. We derive that scaling factor by comparing implied mortality rates for ages 85 and older from CDC WONDER and solving for the value that aligns the UN DESA implied rate with CDC WONDER.

## 4 Repository Location
The main classes, methods, and utilities associated with creating crude death rates are contained in **python/input_modules/death_rates.py**
