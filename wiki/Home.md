# SANDAG ESTIMATES & FORECASTS POPULATION COHORT COMPONENT MODEL

## 1 Overview

The Cohort Component Model is a demographic modeling system used to project the population and households of the region. The Cohort Component Method is used to develop SANDAG's Regional Forecast using assumptions regarding fertility, mortality, and migration that align with the future of the San Diego Metropolitan Area. 


## 2 Cohort Component Method
The Cohort Component Method stands as a prominent legacy modeling approach within the field of Demography. Numerous Metropolitan Planning Organizations and federal governments, like the US Census Bureau, have extensively employed this methodology for national, statewide, and local population projections. A notable advantage of the Cohort Component Method lies in its flexibility, allowing modelers to integrate diverse data sources and apply it across various projection scenarios and geographical scales. The model not only forecasts total population but also offers comprehensive insights into the demographic composition, including race, sex, and single year of age breakdowns. SANDAG's model extends the traditional framework to forecast household characteristics using population structure. It encompasses households, group quarter population, household size, the number of workers in households, households with kids/seniors, and householders (heads of households) in the labor force. The figure below shows the main logic of SANDAG's Cohort Component Model.

[[/images/Figure 1 - CCM Logic.PNG]]


## 3 Modules
SANDAG's Cohort Component Module consists of input data modules, the main forecast loop, and an integer rounding and reallocation utility. Detailed methodologies for each sub-module are specified in their relevant sub-sections.

#### Table 1: Input Modules
| Module | Description |
| :----------: | ----------- |
| [Base Year](https://github.com/SANDAG/Cohort-Component-Model/wiki/Base-Year-Population) | Generates base year population by race, sex, and single year of age. |
| [Active-Duty Military](https://github.com/SANDAG/Cohort-Component-Model/wiki/Active%E2%80%90Duty-Military) | Separates active-duty military population from total population by race, sex, and single year of age. |
| [Death (Mortality)](https://github.com/SANDAG/Cohort-Component-Model/wiki/Death-Rates) | Crude death rates by race, sex, and single year of age. |
| [Birth (Fertility)](https://github.com/SANDAG/Cohort-Component-Model/wiki/Birth-Rates) | Crude birth rates by race and single year of age. |
| [Migration](https://github.com/SANDAG/Cohort-Component-Model/wiki/Migration-Rates) | Crude in/out migration rates by race, sex, and single year of age. |
| [Formation Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Formation-Rates) | Crude group quarters and household formation rates by race, sex, and single year of age. |
| [Household Characteristics Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Household-Characteristics-Rates) | Crude household characteristics rates calculated within race, sex, and single year of age for each increment from the base year up to the launch year. |

#### Table 2: Calculators and Annual Cycle
| Module | Description |
| :----: | ----------- |
| [Population Calculator](https://github.com/SANDAG/Cohort-Component-Model/wiki/Population-Calculator) | Calculate group quarters, households, and household characteristics from population using calculated input module rates. |
| [Control Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Control-Population) | Control households, household characteristics, and population to asserted control totals (from SANDAG's Estimates Program) up to, and including, the launch year. |
| [Integerization and Reallocation](https://github.com/SANDAG/Cohort-Component-Model/wiki/Integerization-and-Reallocation) | Round fields to integers, preserving sums, reallocating integer values when necessary to preserve constraints. |
| [Components of Change](https://github.com/SANDAG/Cohort-Component-Model/wiki/Components-of-Change) | Calculate the Components of Change (Deaths, Births, In/Out Migration) and create input population for next increment. |
