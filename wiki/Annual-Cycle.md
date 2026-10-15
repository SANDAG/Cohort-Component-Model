The annual cycle serves as the primary forecast loop. It draws on data from the input modules, applies the relevant rates, and calculates the population used for the next forecast increment. During each cycle, the components of change (deaths, births, and in‑/out‑migrants) are computed, and the population is aged forward by one year.

# Inputs

| Input | Module Source | Usage |
| ----- | ------------- | ----- |
| Population from Current Increment | Self-referential | Initial input for the launch year is provided by the [Launch Year Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population) module. Population is then calculated for the next increment and used iteratively as input |
| Group Quarters Formation Rates | [Formation Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Formation-Rates) | Group quarters formation rates are applied to the population (excluding *College, Military, and Institutional Correctional Facilities* group quarters) to create the *Group Quarters - Other* population by single year of age, sex, and race/ethnicity |
| Household Formation Rates | [Formation Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Formation-Rates) | Household formation rates are applied to the household population to create the number of formed households by single year of age, sex, and race/ethnicity of the householder |
| Household Characteristics Rates | [Household Characteristics Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Household-Characteristics-Rates) | Household characteristics rates are applied to the formed households to create households by size, number of workers, etc... by single year of age, sex, and race/ethnicity of the householder |
| Death Rates | [Death Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Death-Rates) | Death rates by single year of age, sex, and race/ethnicity are applied to the population (excluding *College, Military, and Institutional Correctional Facilities* group quarters) to calculate deaths and the survived population by single year of age, sex, and race/ethnicity |
| Birth Rates | [Birth Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Birth-Rates) | Birth rates by single year of age, sex, and race/ethnicity are applied to the survived population to calculate births and the number of newborns by single year of age, sex, and race/ethnicity |
| Migration Rates | [Migration Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Migration-Rates) | In/out migration rates by single year of age, sex, and race/ethnicity are applied to the survived population to calculate in/out migrants by single year of age, sex, and race/ethnicity |

## Population from Current Increment
The output of this module is the population by single year of age, sex, and race/ethnicity for the next forecast increment along with the constant *College, Military, and Institutional Correctional Facilities* group quarters populations. This is then used iteratively as input in the primary forecast loop until the forecast reaches the horizon year. The initial input for the launch year is provided by the Launch Year Population module. See [Launch Year Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population).

## Group Quarters Formation Rates
Only the **Group Quarters - Other** population is calculated using group quarters formation rates applied to the population excluding *College, Military, and Institutional Correctional Facilities* group quarters. The *College, Military, and Institutional Correctional Facilities* group quarters are held constant through the duration of the forecast. See [Formation Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Formation-Rates).

## Household Formation Rates
Household formation rates are applied only to the household population (the total population excluding group quarters). See [Formation Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Formation-Rates).

## Death Rates
Death or mortality rates are applied to the population excluding *College, Military, and Institutional Correctional Facilities* group quarters. Deaths are calculated by single year of age, sex, and race/ethnicity to create the survived population that is eligible for birth and migration. See [Death Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Death-Rates).

## Birth Rates
Birth or fertility rates are applied to the survived population, which excludes *College, Military, and Institutional Correctional Facilities* group quarters and persons who have died after applying death rates. Newborns are calculated as age 0, assigned a sex using an asserted Male/Female split probability, and assumed to be the race/ethnicity of the mother. See [Birth Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Birth-Rates).

## Migration Rates
In/out migration rates are applied to the survived population, which excludes *College, Military, and Institutional Correctional Facilities* group quarters and persons who have died after applying death rates. See [Migration Rates](https://github.com/SANDAG/Cohort-Component-Model/wiki/Migration-Rates).

# Outputs
## Population for Next Increment
The population for the current increment by single year of age, sex, and race/ethnicity, and including the *College, Military, and Institutional Correctional Facilities* group quarters, is used to derive the *Group Quarters - Other* population and the number of formed households. Household characteristics rates are then applied to the formed households, generating the complete population for the current increment.

The current increment population is then survived, birthed, migrated, and aged one year producing both the next increment's population and the components of change: births, deaths, and migration. Birth and migration rates are applied up using the eligible survivors' next single year of age, capped at 99, rather than their current increment age. This output feeds back into the annual cycle and is iteratively processed until the forecast reaches the horizon year.

*See the **python/annual_cycle.py** and **python/calculate_population.py** files for underlying code used by the module.*