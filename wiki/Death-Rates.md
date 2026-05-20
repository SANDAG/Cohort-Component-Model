## 1 Overview
Crude death rates are calculated within race, sex, and single year of age for each increment from the base year up to the launch year.
* **TBD - Utility to grow/decay death rates to meet horizon year expectations.**

## 2 Input Datasets
* [UN DESA Life Table Survivors](https://population.un.org/wpp/downloads?folder=Standard%20Projections&group=Mortality)
* [CDC WONDER ucd-icd10: 1999-2020: Underlying Cause of Death by Bridged-Race Categories](https://wonder.cdc.gov/ucd-icd10.html)
* [CDC WONDER ucd-icd10-expanded: 2018-2024: Underlying Cause of Death by Single-Race Categories](https://wonder.cdc.gov/ucd-icd10-expanded.html)

## 3 Methods
* Death rates are calculated for ages < 85 from CDC WONDER by dividing raw deaths by population for each race, sex, and single year of age category after using the substitution methodology which involves beginning with San Diego County level data and switching to higher level geographies (California-state, United States-national) whenever the former is "Suppressed" or zero. This strategy avoids missing value records and implausible 0% death rates. The CDC WONDER data sources used for each base/launch year within race/ethnicity categories is shown below. Note that 2020 data is substituted for missing 2021 data. 
* For ages >= 85 the United Nations Department of Economic and Social Affairs (UN DESA) Life Table Survivors dataset is used for the chosen base/launch year. This table is only stratified by age and sex, and requires a scaling factor to produce age, sex, and race-specific mortality rates. The scaling factor is calculated by acquiring an implied mortality rate for ages 85+ from both CDC products and solving for the scaling factor such that the implied mortality rates from UN DESA match the mortality rates for the CDC products. Note UN DESA stops at 2023, so further calculations will be using 2023 data.

#### Table 1: CDC WONDER Exports
_Note each CDC product has different race reporting standards ([OMB SPD-15](https://spd15revision.gov/content/spd15revision/en/history.html)) and eligible datasets. The 1999-2020 product is missing `Non-Hispanic Native Hawaiian or Pacific Islander` and `Two or More Races` and uses the combined data for all races. Meanwhile, the 2018-2024 product is missing population at the county level and is substituted with population estimates from within CCM. There is not enough data in the 2018-2024 product to do a five-year moving average for 2021, and as such, 2020 data will be used instead. The `SYA` files consist of ages 0-84 while the `TYA` files represent 85+._
| Increment Year | Race/Ethnicity | File |
| :---------------:| :------------: | :--: |
| 2010-2020 | Hispanic | (SD-CA-US); 1999-2020; (SYA-TYA); (F-M); HIS; ALL; (2010-2020); 5Y.(txt-csv) |
| 2010-2020 | American Indian or Alaska Native alone | (SD-CA-US); 1999-2020; (SYA-TYA); (F-M); NON; AIAN; (2010-2020); 5Y.(txt-csv) |
| 2010-2020 | Asian alone | (SD-CA-US); 1999-2020; (SYA-TYA); (F-M); NON; ASIAN; (2010-2020); 5Y.(txt-csv) |
| 2010-2020 | Black or African American alone | (SD-CA-US); 1999-2020; (SYA-TYA); (F-M); NON; BAA; (2010-2020); 5Y.(txt-csv) |
| 2010-2020 | Native Hawaiian or Other Pacific Islander alone | (SD-CA-US); 1999-2020; (SYA-TYA); (F-M); NON; ALL; (2010-2020); 5Y.(txt-csv) |
| 2010-2020 | White alone | (SD-CA-US); 1999-2020; (SYA-TYA); (F-M); NON; WH; (2010-2020); 5Y.(txt-csv) |
| 2010-2020 | Two or More Races | (SD-CA-US); 1999-2020; (SYA-TYA); (F-M); NON; ALL; (2010-2020); 5Y.(txt-csv) |
| | | |
| 2022-2024 | Hispanic | (SD-CA-US); 2018+; (SYA-TYA); (F-M); HIS; ALL; (2022-2024); 5Y.(txt-csv) |
| 2022-2024 | American Indian or Alaska Native alone | (SD-CA-US); 2018+; (SYA-TYA); (F-M); NON; AIAN; (2022-2024); 5Y.(txt-csv) |
| 2022-2024 | Asian alone | (SD-CA-US); 2018+; (SYA-TYA); (F-M); NON; ASIAN; (2022-2024); 5Y.(txt-csv) |
| 2022-2024 | Black or African American alone | (SD-CA-US); 2018+; (SYA-TYA); (F-M); NON; BAA; (2022-2024); 5Y.(txt-csv) |
| 2022-2024 | Native Hawaiian or Other Pacific Islander alone | (SD-CA-US); 2018+; (SYA-TYA); (F-M); NON; ALL; (2022-2024); 5Y.(txt-csv) |
| 2022-2024 | White alone | (SD-CA-US); 2018+; (SYA-TYA); (F-M); NON; WH; (2022-2024); 5Y.(txt-csv) |
| 2022-2024 | Two or More Races | (SD-CA-US); 2018+; (SYA-TYA); (F-M); NON; ALL; (2022-2024); 5Y.(txt-csv) |
| | | |

_Note each CDC product contains numerous instances of `Not Stated` categories where there are associated death counts but no population counts, making them unattributable to a specific demographic. To address this, we inflate the attributable deaths by this proportion and recalculate the rates based on the inflated death counts._
| Increment Year | Not Stated Category | File |
| :---------------:| :------------: | :--: |
| 2010-2020 | Age | (SD-CA-US); 1999-2020; NS; ALL; ALL; ALL; (2010-2020); 5Y.csv |
| 2010-2020 | Hispanic Origin | (SD-CA-US); 1999-2020; SYA; ALL; NS; ALL; (2010-2020); 5Y.csv |
| 2010-2020 | None | (SD-CA-US); 1999-2020; SYA; ALL; ALL; ALL; (2010-2020); 5Y.csv |
| | | |
| 2022-2024 | Age | (SD-CA-US); 2018+; NS; ALL; ALL; ALL; (2022-2024); 5Y.csv |
| 2022-2024 | Hispanic Origin | (SD-CA-US); 2018+; SYA; ALL; NS; ALL; (2022-2024); 5Y.csv |
| 2022-2024 | None | (SD-CA-US); 2018+; SYA; ALL; ALL; ALL; (2022-2024); 5Y.csv |
| | | |

## 4 Repository Location
The main classes, methods, and utilities associated with creating crude death rates are contained in **python/input_modules/death_rates.py**
