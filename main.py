"""Entry point for running the Regional Cohort Component Model."""

import logging

import python.utils as utils

from python.annual_cycle import increment_population
from python.calculate_population import (
    apply_controls,
    calculate_population,
    integerize_population,
)
from python.etl import run_etl
from python.input_modules.active_duty_military import get_active_duty_military
from python.input_modules.base_yr import get_base_yr_2020
from python.input_modules.birth_rates import get_birth_rates
from python.input_modules.death_rates import get_death_rates
from python.input_modules.formation_rates import get_formation_rates
from python.input_modules.hh_characteristics_rates import get_hh_characteristic_rates
from python.input_modules.migration_rates import get_migration_rates

logger = logging.getLogger(__name__)


# Remove any existing output files from previous runs ------------------------
utils.wipe_output_files()


# Initialize base year dataset -----------------------------------------------
logger.info("Initializing base year")

# For launch years >= 2020 use the blended 2020 base year approach ----
if utils.BASE_YEAR == 2020:
    pop_df = get_base_yr_2020()
else:
    raise ValueError("Base years besides 2020 are not available.")


# Begin Annual Cycle ---------------------------------------------------------
# Loop increment years from base year to horizon year
for increment in range(utils.BASE_YEAR, utils.HORIZON_YEAR + 1):
    logger.info("Starting Increment: " + str(increment))

    # Break out active-duty military population from total population ----
    pop_df = get_active_duty_military(yr=increment, pop_df=pop_df)

    # Calculate rates (rates calculated up to the launch year) ----
    if increment <= utils.LAUNCH_YEAR:
        rates = {
            # Crude Birth Rates
            "births": get_birth_rates(yr=increment, pop_df=pop_df),
            # Crude Death Rates
            "deaths": get_death_rates(yr=increment, pop_df=pop_df),
            # Crude Migration Rates
            "migration": get_migration_rates(yr=increment, pop_df=pop_df),
            # Crude Group Quarters and Household Formation Rates
            "formation_gq_hh": get_formation_rates(yr=increment),
            # Household Characteristics Rates
            "hh_characteristics": get_hh_characteristic_rates(yr=increment),
        }

    else:
        if utils.MIGRATION_CONTROLS is not None:
            rates["migration"] = get_migration_rates(yr=increment, pop_df=pop_df)

    # Calculate households/population for the increment ----
    pop_df = calculate_population(pop_df=pop_df, rates=rates)

    # Apply Controls (controls applied up to the launch year) ----
    if increment <= utils.LAUNCH_YEAR:
        pop_df = apply_controls(yr=increment, pop_df=pop_df)

    # Integerize calculated households/population ----
    # Sort before integerizing to ensure consistent ordering
    pop_df = pop_df.sort_values(by=["race", "sex", "age"]).reset_index(drop=True)
    pop_df = integerize_population(pop_df=pop_df)

    # Write out calculated households/population and rates ----
    utils.write_df(yr=increment, df=pop_df, fp=utils.OUTPUT_FOLDER / "population.csv")
    utils.write_rates(yr=increment, rates=rates, fp=utils.OUTPUT_FOLDER / "rates.csv")

    # Calculate Components of Change and create new population ----
    increment_data = increment_population(pop_df=pop_df, rates=rates)

    # Write out components of change ----
    utils.write_df(
        yr=increment,
        df=increment_data["components"],  # type: ignore
        fp=utils.OUTPUT_FOLDER / "components.csv",
    )

    # Set population for next increment and finish annual cycle ----
    pop_df = increment_data["population"].copy()  # type: ignore
logger.info("Completed")

if utils.LOAD_TO_DATABASE:
    # Run the ETL process
    run_etl()
