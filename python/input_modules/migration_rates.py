"""Get migration rates by single year of age, sex, and race/ethnicity."""

# TODO: (5-feature) Potentially implement smoothing function within race and sex categories.

import logging

import numpy as np
import pandas as pd
import sqlalchemy as sql

from functools import lru_cache

import python.tests as tests
import python.utils as utils

generator = np.random.default_rng(utils.RANDOM_SEED)
logger = logging.getLogger(__name__)


def run_migration_rates(year: int, population: pd.DataFrame) -> pd.DataFrame:
    """Orchestrator function to calculate migration rates.

    This module generates migration rates by single year of age, sex, and
    race/ethnicity using ACS PUMS data for San Diego County. For post-launch
    years, migration rates are scaled based on control totals, if provided.

    Migration rates are calculated from the ACS 5-year PUMS, excluding the
    Military and Institutional Correctional Facilities group quarters
    populations as it is assumed those populations will remain fixed through
    the forecast. Rates are calculated within age groups and then applied
    uniformly to all single years of age within those age groups.

    Functionality is split apart for code encapsulation:
        _get_migration_inputs - Get migration ins/outs and migration-eligible
            San Diego County resident population by age group, sex, and
            race/ethnicity from the ACS 5-year PUMS
        _validate_migration_inputs - Validate inputs from the above function
        _create_migration_outputs - Calculate migration rates and distribute
            to single years of age within each age group, capping rates as
            specified in the project utilities
        _control_migration_rates - Adjust post-launch migration rates to match
            asserted control totals for ins/outs, if provided
        _validate_migration_outputs - Validate the output migration rates
    """
    if year == utils.LAUNCH_YEAR:
        logger.info("Calculating migration rates for launch year")

        migration_inputs = _get_migration_inputs(year)
        _validate_migration_inputs(migration_inputs)

        migration_outputs = _create_migration_outputs(migration_inputs)
        _validate_migration_outputs(migration_outputs)

        return migration_outputs

    elif year > utils.LAUNCH_YEAR and utils.MIGRATION_CONTROLS is not None:
        logger.info("Calculating migration rates for post-launch year with controls")

        # Post-launch year migration rates are simply launch year rates
        # Controlled to match asserted in/out migration totals
        # Decorator ensures that repeated calls for launch year inputs
        # Are retrieved from the cache rather than recalculated each time
        migration_inputs = _get_migration_inputs(utils.LAUNCH_YEAR)
        _validate_migration_inputs(migration_inputs)

        migration_outputs = _create_migration_outputs(migration_inputs)
        migration_outputs = _control_migration_rates(
            year=year, population=population, migration_outputs=migration_outputs
        )
        _validate_migration_outputs(migration_outputs)

        return migration_outputs

    else:
        # No migration controls provided for post-launch year
        raise ValueError("No migration controls provided for post-launch year")


# Decorator to cache the results of the function to improve performance
# As it is called repeatedly for launch year inputs to scale to post-launch controls
@lru_cache(maxsize=1)
def _get_migration_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Load input datasets for migration rate generation."""
    with utils.CCM_ENGINE.connect() as connection:
        with open(
            utils.SQL_FOLDER / "migration_rates" / "get_eligible_population.sql", "r"
        ) as file:
            eligible_population = utils.read_sql_query_fallback(
                sql=sql.text(file.read()),
                con=connection,
                params={"year": year},
            )

        with open(
            utils.SQL_FOLDER / "migration_rates" / "get_migration_counts.sql", "r"
        ) as file:
            migration_counts = utils.read_sql_query_fallback(
                sql=sql.text(file.read()),
                con=connection,
                params={"year": year},
            )

    return {
        "eligible_population": eligible_population,
        "migration_counts": migration_counts,
    }


def _validate_migration_inputs(migration_inputs: dict[str, pd.DataFrame]) -> None:
    """Validate the migration input datasets."""
    # Validate the eligible population
    tests.validate_data(
        table_name="Input Eligible Migrant Population",
        data=migration_inputs["eligible_population"],
        row_count={"key_columns": {"age_group", "sex", "ethnicity"}},
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )

    # Validate the migration counts
    tests.validate_data(
        table_name="Input Migration Counts",
        data=migration_inputs["migration_counts"],
        row_count={"key_columns": {"age_group", "sex", "ethnicity"}},
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )


def _create_migration_outputs(
    migration_inputs: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Create migration outputs from the input datasets."""
    eligible_population = migration_inputs["eligible_population"]
    migration_counts = migration_inputs["migration_counts"]

    # Create a single year of age mapping from age groups
    sya_map = pd.DataFrame(
        (
            {"age": age, "age_group": age_group}
            for age_group, bounds in utils.AGE_MAPPING.items()
            for age in range(bounds["min"], bounds["max"] + 1)
        )
    )

    migration_outputs = (
        eligible_population.merge(
            migration_counts,
            on=["age_group", "sex", "ethnicity"],
            how="left",
        )
        .assign(
            # Calculate crude migration rates
            rate_in=lambda x: np.where(x["pop"] > 0, x["in"] / x["pop"], 0),
            rate_out=lambda x: np.where(x["pop"] > 0, x["out"] / x["pop"], 0),
        )
        .assign(
            # Cap crude migration rates at the specified maximum
            rate_in=lambda x: np.where(
                x["rate_in"] > utils.MAX_MIGRATION_RATE,
                utils.MAX_MIGRATION_RATE,
                x["rate_in"],
            ),
            rate_out=lambda x: np.where(
                x["rate_out"] > utils.MAX_MIGRATION_RATE,
                utils.MAX_MIGRATION_RATE,
                x["rate_out"],
            ),
        )
        # Map age groups to single year of age
        .merge(sya_map, on="age_group")
    )[["age", "sex", "ethnicity", "rate_in", "rate_out"]]

    return migration_outputs


def _validate_migration_outputs(migration_outputs: pd.DataFrame) -> None:
    """Validate the migration outputs DataFrame."""
    tests.validate_data(
        table_name="Output Migration Rates",
        data=migration_outputs,
        row_count={"key_columns": {"age", "sex", "ethnicity"}},
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )


def _control_migration_rates(
    year: int,
    population: pd.DataFrame,
    migration_outputs: pd.DataFrame,
) -> pd.DataFrame:
    """Control migration rates to in/out migration control totals.

    Calculates the total in/out migrants using launch year rates and the
    migration-eligible population at the current increment. It then scales
    the rates to match input in/out migration control totals, applying the
    maximum rate cap specified in the project utilities. Migration-eligible
    population is defined as the population excluding the Military and
    Institutional Correctional Facilities group quarters populations.

    Note, this calculation uses the migration-eligible population rather than
    the survived migration-eligible population, which is where the migration
    rates are ultimately applied. This, combined with the capping of maximum
    rates post-scaling, creates a slight discrepancy between the controlled
    rates when they are ultimately applied and the asserted in/out migration
    control totals.

    Args:
        year: Increment year
        population (pd.DataFrame): Population data by single year of age, sex,
            and race/ethnicity for the increment year
        migration_outputs (pd.DataFrame): Migration rates by single year of
            age, sex, and race/ethnicity calculated from the launch year

    Returns:
        pd.DataFrame: Migration rates controlled to in/out migrant totals by
            single year of age, sex, and race/ethnicity for the increment year
    """
    # Check the controls DataFrame is valid and return controls for the given year
    if utils.MIGRATION_CONTROLS is not None:
        controls = utils.MIGRATION_CONTROLS.loc[
            utils.MIGRATION_CONTROLS["year"] == year
        ]

        # Calculate the total in/out migrants from the rates and population
        controlled_rates = (
            population[["age", "sex", "ethnicity", "pop", "gq_mil", "gq_prison"]]
            .merge(migration_outputs, how="left", on=["age", "sex", "ethnicity"])
            .assign(
                pop_eligible=lambda x: x["pop"] - x["gq_mil"] - x["gq_prison"],
                ins=lambda x: x["rate_in"] * x["pop_eligible"],
                outs=lambda x: x["rate_out"] * x["pop_eligible"],
            )
        )

        # Scale the rates such that the ins/outs match the control totals
        controlled_rates["rate_in"] = controlled_rates["rate_in"] * (
            controls["ins"].sum() / controlled_rates["ins"].sum()
        )

        controlled_rates["rate_out"] = controlled_rates["rate_out"] * (
            controls["outs"].sum() / controlled_rates["outs"].sum()
        )

        # Cap crude migration rates at the asserted maximum value
        controlled_rates["rate_in"] = np.where(
            controlled_rates["rate_in"] > utils.MAX_MIGRATION_RATE,
            utils.MAX_MIGRATION_RATE,
            controlled_rates["rate_in"],
        )

        controlled_rates["rate_out"] = np.where(
            controlled_rates["rate_out"] > utils.MAX_MIGRATION_RATE,
            utils.MAX_MIGRATION_RATE,
            controlled_rates["rate_out"],
        )

        return controlled_rates[["age", "sex", "ethnicity", "rate_in", "rate_out"]]
    else:
        raise ValueError("Migration controls are not defined in the configuration.")
