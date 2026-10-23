# SANDAG ESTIMATES & FORECASTS POPULATION COHORT COMPONENT MODEL

## Overview

The Cohort Component Model is a demographic modeling system used to project the population and households of the region. The Cohort Component Method is used to develop SANDAG's Regional Forecast using assumptions regarding fertility, mortality, and migration that align with the future of the San Diego Metropolitan Area. 


## Cohort Component Method
The Cohort Component Method stands as a prominent legacy modeling approach within the field of Demography. Numerous Metropolitan Planning Organizations and federal governments, like the US Census Bureau, have extensively employed this methodology for national, statewide, and local population projections. A notable advantage of the Cohort Component Method lies in its flexibility, allowing modelers to integrate diverse data sources and apply it across various projection scenarios and geographical scales. The model not only forecasts total population but also offers comprehensive insights into the demographic composition, including race, sex, and single year of age breakdowns. SANDAG's model extends the traditional framework to forecast household characteristics using population structure. It encompasses households, group quarter population, household size, the number of workers in households, households with kids/seniors, and householders (heads of households) in the labor force. The figure below shows the main logic of SANDAG's Cohort Component Model.

[[/images/Figure 1 - CCM Logic.PNG]]


## Modules
SANDAG's Cohort Component Module consists of input data modules and the main forecast loop. Detailed methodologies for each sub-module are specified in their relevant sub-sections.

#### Table 1: Input Modules
| Module | Description |
| :----------: | ----------- |
| [Launch Year](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population) | Generates launch year population by single year of age, sex, and race/ethnicity within population types (e.g. Household Population, Group Quarters - College, etc.) |
| [Death (Mortality)](https://github.com/SANDAG/Cohort-Component-Model/wiki/Death-Rates) | Crude death rates by single year of age, sex, and race/ethnicity |
| [Birth (Fertility)](https://github.com/SANDAG/Cohort-Component-Model/wiki/Birth-Rates) | Crude birth rates by single year of age, sex, and race/ethnicity |
| [Migration](https://github.com/SANDAG/Cohort-Component-Model/wiki/Migration-Rates) | Crude in/out migration rates by single year of age, sex, and race/ethnicity |
| [Formation Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Formation-Rates) | Crude group quarters and household formation rates by single year of age, sex, and race/ethnicity |
| [Household Characteristics Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Household-Characteristics-Rates) | Crude household characteristics rates calculated by single year of age, sex, and race/ethnicity |

#### Table 2: Annual Cycle and Model Outputs
| Module | Description |
| :----: | ----------- |
| [Annual Cycle](https://github.com/SANDAG/Cohort-Component-Model/wiki/Annual-Cycle) | Calculate group quarters, households, and household characteristics from population using calculated input module rates. Survive, birth, migrate, and age the population to the next increment calculating the Components of Change (Births, Deaths, and Migration). |
| [Model Outputs](https://github.com/SANDAG/Cohort-Component-Model/wiki/Model-Outputs) | Describes the four primary outputs of the Cohort Component Model for the launch year and each forecast increment. (1) The population by single year of age, sex, and race/ethnicity within population types (e.g. Household Population, Group Quarters - College, etc.) including the number of formed households and their characteristics. (2) The calculated input module rates used to create the complete population and survive, birth, and migrate the population. (3) The households and housing units by structure type. (4) The Components of Change (Births, Deaths, and Migration) calculated when moving to the next forecast increment. |

## Publications
### [A Comprehensive Evaluation of Population Forecast Error for San Diego County and Its Jurisdictions](https://read.dukeupress.edu/demography/article/63/4/1211/412368/A-Comprehensive-Evaluation-of-Population-Forecast)
SANDAG's Estimates & Forecasts team has published a manuscript in the *Journal of Demography* evaluating population forecast error across all regional forecasts produced by SANDAG from 1970-2025, which primarily relied on the Cohort Component Method.
