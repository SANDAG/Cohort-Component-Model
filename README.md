# Cohort Component Model

The Cohort Component Model (CCM) is a demographic modeling system used to project the population and households of the region. The Cohort Component Method is used to developed SANDAG's Regional Forecast using assumptions regarding fertility, mortality, migration and headship rates that align with the future economy of the San Diego Metropolitan Area. [For documentation see the project Wikipedia](https://github.com/SANDAG/Cohort-Component-Model/wiki).

## Setup
Clone the repository and ensure an installation of [Miniconda/Anaconda](https://docs.conda.io/projects/miniconda/en/latest/) exists. Use the **environment.yml** file in the root directory of the project to [create the Python virtual environment](https://docs.conda.io/projects/conda/en/4.6.1/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file) needed to run the project.

Set the configuration file **config.JSON** parameters specific to the model run of interest and run the **main.py** entry point file located in the project root directory.

## Configuration File Settings
*Note that the configuration file contains datasets stored on a SQL server instance accessed at runtime through queries. It is possible to provide query results as local datasets and migrate the SQL datasets to the **csv** section of the configuration file to remove the dependency on the SQL instance.*
```json
{
    "configurations": {
        "rates_map": "rates_map.JSON",  --  local birth/death rate files mapping
        "controls": "sandag_estimates.JSON"  -- SANDAG Estimates Control totals
    },
    "csv": {  -- local datasets
        "dmdc_location_report": "data/DMDC Website Location Report.csv",
        "sdmac_report": "data/SDMAC Report.csv",
        "ss_life_table": "data/Social Security Actuarial Life Table.csv"
    },
    "interval": {
        "launch": 2020,  -- beginning of forecast (2010-2029)
        "horizon": 2050  -- end of forecast (horizon >= launch)
    },
    "output": {  -- output files and their write locations
        "overwrite": true,  -- boolean to overwrite output files
        "files": {
            "components": "output/components.csv",
            "population": "output/population.csv",
            "rates": "output/rates.csv"
        }
    },
    "sql": {  -- datasets stored on SQL server
        "server": "",  -- server name
        "datasets": {
            "acs5yr_pums_ca_mil": "sql/acs5yr_pums_ca_mil.sql",
            "acs5yr_pums_migrants": "sql/acs5yr_pums_migrants.sql",
            "acs5yr_pums_persons": "sql/acs5yr_pums_persons.sql",
            "census_redistricting": "sql/census_redistricting.sql",
            "dof_estimates": "sql/dof_estimates.sql",
            "dof_projections": "sql/dof_projections.sql"
        }
    }
}
```