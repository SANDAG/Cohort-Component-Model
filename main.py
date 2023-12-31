"""Entry point for running the Regional Cohort Component Model."""
import json
import os
import pandas as pd
import sqlalchemy as sql

# User-defined modules
from python.annual_cycle import increment_population
from python.calculate_population import (
    apply_controls,
    calculate_population,
    integerize_population,
)
from python.input_modules.active_duty_military import get_active_duty_military
from python.input_modules.base_yr import get_base_yr_2020
from python.input_modules.birth_rates import get_birth_rates
from python.input_modules.death_rates import get_death_rates, load_ss_life_tbl
from python.input_modules.formation_rates import get_formation_rates
from python.input_modules.hh_characteristics_rates import get_hh_characteristic_rates
from python.input_modules.migration_rates import get_migration_rates
from python.output_data import write_df, write_rates


# Set up configurations and datasets -----------------------------------------
# Load JSON configuration files ----
with open("config.JSON") as f:
    config = json.load(f)
for k, v in config["configurations"].items():
    with open(v) as f:
        config["configurations"][k] = json.load(f)

# Check if output files already exist ----
for k, v in config["output"]["files"].items():
    if os.path.isfile(v):
        if config["output"]["overwrite"]:
            os.remove(v)
        else:
            raise ValueError("Cannot overwrite existing output: " + v)

# Load csv data sources ----
for k, v in config["csv"].items():
    if k == "ss_life_table":
        config["csv"][k] = load_ss_life_tbl(v)
    else:
        config["csv"][k] = pd.read_csv(v)

# Load SQL data sources ----
engine = sql.create_engine("mssql+pymssql://" + config["sql"]["server"] + "/")
with engine.connect() as connection:
    for k, v in config["sql"]["datasets"].items():
        with open(v, "r") as query:
            config["sql"]["datasets"][k] = pd.read_sql_query(query.read(), connection)


# Initialize base year dataset -----------------------------------------------
# For launch years >= 2020 use the blended base year approach ----
if 2020 <= config["interval"]["launch"] < 2030:
    base_yr = 2020

    pop_df = get_base_yr_2020(
        launch_yr=config["interval"]["launch"],
        acs5yr_pums_persons=config["sql"]["datasets"]["acs5yr_pums_persons"],
        dof_estimates=config["sql"]["datasets"]["dof_estimates"],
        dof_projections=config["sql"]["datasets"]["dof_projections"],
        census_redistricting=config["sql"]["datasets"]["census_redistricting"],
    )

    print("Initialized: Base Year 2020")
# For launch years >= 2010 (and < 2020) use the 2010 decennial Census ----
elif 2010 <= config["interval"]["launch"] < 2020:
    raise ValueError("Launch years prior to 2020 not available.")
# Only valid for launch years 2010-2029 ----
else:
    raise ValueError("Invalid launch year provided.")


# Begin Annual Cycle ---------------------------------------------------------
# Loop increment years from base year to horizon year
for increment in range(base_yr, config["interval"]["horizon"] + 1):
    print("Starting Increment: ", str(increment))

    # Break out active-duty military population from total population ----
    pop_df = get_active_duty_military(
        yr=increment,
        launch_yr=config["interval"]["launch"],
        pop_df=pop_df,
        acs5yr_pums_persons=config["sql"]["datasets"]["acs5yr_pums_persons"],
        acs5yr_pums_ca_mil=config["sql"]["datasets"]["acs5yr_pums_ca_mil"],
        dmdc_location_report=config["csv"]["dmdc_location_report"],
        sdmac_report=config["csv"]["sdmac_report"],
    )

    # Calculate rates (rates calculated up to the launch year) ----
    if increment <= config["interval"]["launch"]:
        rates = {
            # Crude Birth Rates
            "births": get_birth_rates(
                yr=increment,
                launch_yr=config["interval"]["launch"],
                pop_df=pop_df,
                rates_map=config["configurations"]["rates_map"],
            ),
            # Crude Death Rates
            "deaths": get_death_rates(
                yr=increment,
                launch_yr=config["interval"]["launch"],
                ss_life_tbl=config["csv"]["ss_life_table"],
                rates_map=config["configurations"]["rates_map"],
            ),
            # Crude Migration Rates
            "migration": get_migration_rates(
                yr=increment,
                launch_yr=config["interval"]["launch"],
                pop_df=pop_df,
                acs5yr_pums_migrants=config["sql"]["datasets"]["acs5yr_pums_migrants"],
            ),
            # Crude Group Quarters and Household Formation Rates
            "formation_gq_hh": get_formation_rates(
                yr=increment,
                launch_yr=config["interval"]["launch"],
                acs5yr_pums_persons=config["sql"]["datasets"]["acs5yr_pums_persons"],
                sandag_estimates=config["configurations"]["controls"],
            ),
            # Household Characteristics Rates
            "hh_characteristics": get_hh_characteristic_rates(
                yr=increment,
                launch_yr=config["interval"]["launch"],
                acs5yr_pums_persons=config["sql"]["datasets"]["acs5yr_pums_persons"],
                sandag_estimates=config["configurations"]["controls"],
            ),
        }

    # TODO: (6,7,10-feature) adjustments to rates would be made post-launch year through horizon
    else:
        pass

    # Calculate households/population for the increment ----
    pop_df = calculate_population(pop_df=pop_df, rates=rates)

    # Apply Controls (controls applied up to the launch year) ----
    if increment <= config["interval"]["launch"]:
        pop_df = apply_controls(
            yr=increment,
            launch_yr=config["interval"]["launch"],
            pop_df=pop_df,
            sandag_estimates=config["configurations"]["controls"],
        )

    # Integerize calculated households/population ----
    pop_df = integerize_population(pop_df=pop_df)

    # Write out calculated households/population and rates ----
    write_df(yr=increment, df=pop_df, fn=config["output"]["files"]["population"])
    write_rates(yr=increment, rates=rates, fn=config["output"]["files"]["rates"])

    # Calculate Components of Change and create new population ----
    increment_data = increment_population(pop_df=pop_df, rates=rates)

    # Write out components of change ----
    write_df(
        yr=increment,
        df=increment_data["components"],
        fn=config["output"]["files"]["components"],
    )

    # Set population for next increment and finish annual cycle ----
    pop_df = increment_data["population"].copy()

print("Completed")
