# Cohort Component Model

The Cohort Component Model (CCM) is a demographic modeling system used to project the population and households of the region. The Cohort Component Method is used to developed SANDAG's Regional Forecast using assumptions regarding fertility, mortality, migration and headship rates that align with the future economy of the San Diego Metropolitan Area. [For documentation see the project Wikipedia](https://github.com/SANDAG/Cohort-Component-Model/wiki).

## Setup
Clone the repository and ensure an installation of [Miniconda/Anaconda](https://docs.conda.io/projects/miniconda/en/latest/) exists. Use the **environment.yml** file in the root directory of the project to [create the Python virtual environment](https://docs.conda.io/projects/conda/en/4.6.1/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file) needed to run the project.

Set the configuration file **config.JSON** parameters specific to the model run of interest and run the **main.py** entry point file located in the project root directory.

## Configuration File Settings
*Note that the configuration file contains datasets stored on a SQL server instance accessed at runtime through queries. It is possible to provide query results as local datasets and migrate the SQL datasets to the **csv** section of the configuration file to remove the dependency on the SQL instance.*
```yaml
configurations:  # other configuration files
  rates_map: "rates_map.JSON"  # local birth/death rate files mapping
  controls: "sandag_estimates.JSON"  # SANDAG Estimates Control totals
csv:  # locally stored datasets (manually entered)
  dmdc_location_report: "data/DMDC Website Location Report.csv"  # Department of Defense DMDC Report data
  sdmac_report: "data/SDMAC Report.csv"  # Military SDMAC Report data
  ss_life_table: "data/Social Security Actuarial Life Table.csv"  # Social Security Life Table data
interval:  # forecast interval (base is assumed from launch)
  launch: 2020  # last year before forecast starts
  horizon: 2050  # forecast end year
output:  # output files
  overwrite: true  # boolean true/false switch to overwrite output files
  files:  # path and names of output files to write
    components: "output/components.csv"
    population: "output/population.csv"
    rates: "output/rates.csv"
sql:  # SQL server options
  server: ""  # SQL instance
  datasets:  # SQL queries to be used as datasets
    acs5yr_pums_ca_mil: "sql/acs5yr_pums_ca_mil.sql"  # State of California total military population
    acs5yr_pums_migrants: "sql/acs5yr_pums_migrants.sql"  # San Diego County in/out migration
    acs5yr_pums_persons: "sql/acs5yr_pums_persons.sql"  # San Diego county population
    census_redistricting: "sql/census_redistricting.sql"  # 2020 Census Redistricting file
    dof_estimates: "sql/dof_estimates.sql"  # California Department of Finance Estimates
    dof_projections: "sql/dof_projections.sql"  # California Department of Finance Projections
```