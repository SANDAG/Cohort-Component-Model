This module generates migration rates by single year of age, sex, and race/ethnicity for each increment year. Post-launch year rates are optionally adjusted from launch year rates to match asserted in/out migration control totals.

# Inputs
| Input | Module Source | Usage |
| ----- | ------------- | ----- |
| Eligible Launch Year Migrant Population | External (ACS) | The ACS 5-year PUMS provides eligible migrant population for San Diego County in the launch year by age/sex/ethnicity |
| Launch Year Migration In/Out Counts | External (ACS) | The ACS 5-year PUMS provides counts of in/out migrants to/from San Diego County for the launch year by age/sex/ethnicity |
| Increment Population | [Population Calculator](https://github.com/SANDAG/Cohort-Component-Model/wiki/Population-Calculator) | Calculated population for the increment year is used for post-launch increments to optionally control to asserted in/out migration totals |
| Migration Controls | User-Input (Optional) | Optional CSV file of asserted in/out migration totals for each increment year |

## Eligible Launch Year Migrant Population
The eligible launch year migrant population for San Diego County is calculated from the Census Bureau ACS 5-year PUMS by age group, sex, and ethnicity. This population is used in tandem with the launch year migration in/out counts to create migration rates by age group, sex, and ethnicity. Both *Group Quarters - Military* and *Group Quarters - Institutional Correctional Facilities* populations are considered ineligible for migration as the regional forecast assumes they remain constant for the entirety of the forecast.

## Launch Year Migration In/Out Counts
The launch year counts of in/out migrants to/from San Diego County are calculated from the Census Bureau ACS 5-year PUMS by age group, sex, and ethnicity. These counts are used in tandem with the launch year eligible migrant population to create migration rates by age group, sex, and ethnicity. Both *Group Quarters - Military* and *Group Quarters - Institutional Correctional Facilities* populations are excluded as the regional forecast assumes they remain constant for the entirety of the forecast.

## Increment Population
See [Population Calculator](https://github.com/SANDAG/Cohort-Component-Model/wiki/Population-Calculator).

## Migration Controls (Optional)
An optional user defined CSV file containing control totals for in/out migrants. If provided, the CSV should include one row per increment year, post-launch year, with ins/outs totals greater than or equal to zero. See the [README.md](https://github.com/SANDAG/Cohort-Component-Model/blob/main/README.md) for more information regarding the file structure and how to update the configuration file.

# Outputs
## Migration Rates
Migration rates are calculated from the Census Bureau ACS 5-year PUMS by age group, sex, and ethnicity and uniformly assigned across single year of age within each age group. The rates are artificially capped at a maximum of 20% within each single year of age, sex, and ethnicity category as a legacy carry-over from the [Series 15 Cohort Component Model](https://github.com/SANDAG/Cohort-Component-Model---SR15), per Population Reference Bureau recommendation, and was implemented due to small sample size issues within categories and the lack of a rate smoothing utility.

Post-launch year, rates are optionally scaled to match user-input asserted control totals for in/out migrants, if provided. Note, this calculation uses the migration-eligible population, defined as the population excluding Military and Institutional Correctional Facilities group quarters, rather than the survived migration-eligible population, which is where the migration rates are ultimately applied. This, combined with the capping of maximum rates post-scaling, creates a slight discrepancy between the controlled rates when they are ultimately applied and the asserted in/out migration control totals.

*See the **python/input_modules/migration_rates.py** file and **sql/migration_rates** folder for underlying code used by the module.*