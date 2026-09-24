"""Entry point for running the Regional Cohort Component Model."""

import logging

import python.annual_cycle as annual_cycle
import python.calculate_population as calculate_population
import python.input_modules.birth_rates as birth_rates
import python.input_modules.death_rates as death_rates
import python.input_modules.formation_rates as formation_rates
import python.input_modules.hh_characteristics_rates as hh_characteristics_rates
import python.input_modules.launch_year as launch_year
import python.input_modules.migration_rates as migration_rates
import python.utils as utils

logger = logging.getLogger(__name__)


# Remove any existing output files from previous runs ------------------------
utils.wipe_output_files()


# Initialize launch year dataset ---------------------------------------------
logger.info("Initializing launch year population")
population = launch_year.run_launch_year()


# Begin Annual Cycle ---------------------------------------------------------
# Loop increment years from base year to horizon year
for increment in range(utils.LAUNCH_YEAR, utils.HORIZON_YEAR + 1):  # type: ignore
    logger.info("Starting Increment: " + str(increment))

    # Calculate rates (rates calculated up to the launch year) ----
    if increment == utils.LAUNCH_YEAR:
        logger.info("Calculating rates for launch year")

        rates = {
            # Crude Birth Rates
            "births": birth_rates.get_birth_rates(year=increment),
            # Crude Death Rates
            "deaths": death_rates.get_death_rates(
                year=increment, population=population
            ),
            # Crude Migration Rates
            "migration": migration_rates.get_migration_rates(
                year=increment, population=population
            ),
            # Crude Group Quarters and Household Formation Rates
            "formation_gq_hh": formation_rates.run_formation_rates(
                year=increment, population=population
            ),
        }

        # Household Characteristics Rates
        # These require Household Formation Rates to be calculated
        rates["hh_characteristics"] = (
            hh_characteristics_rates.run_hh_characteristics_rates(
                year=increment,
                population=population,
                rates=rates,
            )
        )

    else:
        logger.info("Calculating rates for increment year")

        if utils.FERTILITY_RATES is not None:
            rates["births"] = birth_rates.get_birth_rates(year=increment)
        if utils.MIGRATION_CONTROLS is not None:
            rates["migration"] = migration_rates.get_migration_rates(
                year=increment, population=population
            )
        if utils.MORTALITY_RATES is not None:
            rates["deaths"] = death_rates.get_death_rates(
                year=increment, population=population
            )

    # Calculate population for the increment ----
    logger.info("Calculating population, households, and household characteristics")
    population = calculate_population.calculate_population(
        population=population, rates=rates
    )

    # Write out calculated population and rates ----
    utils.write_df(
        year=increment, df=population, fp=utils.OUTPUT_FOLDER / "population.csv"
    )
    utils.write_rates(year=increment, rates=rates, fp=utils.OUTPUT_FOLDER / "rates.csv")

    # Calculate Components of Change and create new population ----
    logger.info("Calculating components of change and incremented population")
    increment_data = annual_cycle.increment_population(
        population=population, rates=rates
    )

    # Write out components of change ----
    utils.write_df(
        year=increment,
        df=increment_data["components"],  # type: ignore
        fp=utils.OUTPUT_FOLDER / "components.csv",
    )

    # Set population for next increment and finish annual cycle ----
    population = increment_data["population"].copy()  # type: ignore

logger.info("Completed")
