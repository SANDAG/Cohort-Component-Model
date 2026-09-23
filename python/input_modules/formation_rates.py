"""Get group quarters and household formation rates by age, sex, and race/ethnicity."""

# TODO: (5-feature) Potentially implement smoothing function within race and sex categories.
# TODO: Implement functionality for non-launch years if needed.

import logging

import numpy as np
import pandas as pd
import sqlalchemy as sql

import python.tests as tests
import python.utils as utils

generator = np.random.default_rng(utils.RANDOM_SEED)
logger = logging.getLogger(__name__)


def run_formation_rates(year: int, population: pd.DataFrame) -> pd.DataFrame:
    """Orchestrator function to calculate formation rates.

    This module generates groups quarters and household formation rates by
    single year of age, sex, and race/ethnicity using ACS PUMS data and
    SANADG's Estimates Program. Rates are calculated within age groups and
    then applied uniformly to all single years of age within those age groups.

    The Group Quarters formation rates are only calculated for College and
    Other group quarters categories as it is assumed that the Military and
    Insitutional Correctional Facilities group quarters population will remain
    fixed through the forecast.

    The Household formation rates are only applied to the household population,
    excluding those in Group Quarters.

    The final rates, when applied to the launch year population, should yield
    Group Quarters populations and total household counts identical to SANDAG's
    Estimates Program for the launch year.

    Functionality is plit apart for code encapsulation:
        _get_formation_inputs - Get Group Quarters formation rates by age
            group, sex, and ethnicity directly from SANDAG's Estimates Program,
            household formation rates by age group, sex, and ethnicity from the
            ACS 5-year PUMS, and the total households control from SANDAG's
            Estimates Program
        _validate_formation_inputs - Validate inputs from the above function
        _create_formation_outputs - Distribute Group Quarters formation rates
            and household formation rates to single years of age within each
            age group and control such that the resulting rates, when applied
            to the launch year population, yield Group Quarters population and
            total household values identical to SANDAG's Estimates Program
        _validate_formation_outputs - Validate the output from the above function
    """
    if year == utils.LAUNCH_YEAR:
        logger.info("Calculating formation rates for launch year")

        formation_inputs = _get_formation_inputs(year)
        _validate_formation_inputs(formation_inputs)

        formation_outputs = _create_formation_outputs(formation_inputs, population)
        _validate_formation_outputs(formation_outputs)

        return formation_outputs
    else:
        raise ValueError("Formation rates can only be run for the launch year.")


def _get_formation_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Load input datasets for formation rate generation."""
    with utils.ESTIMATES_ENGINE.connect() as connection:
        with open(
            utils.SQL_FOLDER / "formation_rates" / "get_gq_formation_rates.sql", "r"
        ) as file:
            gq_formation_rates = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=connection,
                params={
                    "run_id": utils.ESTIMATES_RUN_ID,
                    "year": year,
                },  # type: ignore
            )

        with open(
            utils.SQL_FOLDER / "formation_rates" / "get_hh_formation_rates.sql", "r"
        ) as file:
            hh_formation_rates = utils.read_sql_query_fallback(
                sql=sql.text(file.read()),
                con=connection,
                params={
                    "run_id": utils.ESTIMATES_RUN_ID,
                    "year": year,
                },  # type: ignore
            )

        with open(
            utils.SQL_FOLDER / "formation_rates" / "get_total_hh.sql", "r"
        ) as file:
            total_hh = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=connection,
                params={
                    "run_id": utils.ESTIMATES_RUN_ID,
                    "year": year,
                },  # type: ignore
            )

    return {
        "gq_formation_rates": gq_formation_rates,
        "hh_formation_rates": hh_formation_rates,
        "total_hh": total_hh,
    }


def _validate_formation_inputs(formation_inputs: dict[str, pd.DataFrame]) -> None:
    """Validate the input datasets for formation rate generation."""
    # Validate the GQ formation rates
    tests.validate_data(
        table_name="Input Group Quarters Formation Rates",
        data=formation_inputs["gq_formation_rates"],
        row_count={"key_columns": {"age_group", "sex", "ethnicity"}},
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )

    # Validate the HH formation rates
    tests.validate_data(
        table_name="Input Household Formation Rates",
        data=formation_inputs["hh_formation_rates"],
        row_count={"key_columns": {"age_group", "sex", "ethnicity"}},
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )

    # Validate the total HH count
    tests.validate_data(
        table_name="Total Household Count",
        data=formation_inputs["total_hh"],
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )


def _create_formation_outputs(
    formation_inputs: dict[str, pd.DataFrame],
    population: pd.DataFrame,
) -> pd.DataFrame:
    """Create the formation rates output DataFrame."""
    gq_formation_rates = formation_inputs["gq_formation_rates"]
    hh_formation_rates = formation_inputs["hh_formation_rates"]
    total_hh = formation_inputs["total_hh"]

    # Create a single year of age mapping from age groups
    sya_map = pd.DataFrame(
        (
            {"age": age, "age_group": age_group}
            for age_group, bounds in utils.AGE_MAPPING.items()
            for age in range(bounds["min"], bounds["max"] + 1)
        )
    )

    # Distribute Group Quarters rates to single year of age
    # And assign to the population DataFrame by age, sex, and race/ethnicity
    # Adjust rates such that when applied they equal the group quarters counts
    gq_rates = (
        # Merge the population DataFrame with the group quarters formation rates
        # Expanded to single year of age uniformly within each age group
        population.merge(
            gq_formation_rates.merge(sya_map, on="age_group"),
            on=["age", "sex", "ethnicity"],
        ).assign(
            # First calculate the implied group quarters using the rates
            implied_gq_college=lambda df: df["rate_gq_college"]
            * (df["pop"] - df["gq_mil"] - df["gq_prison"]),
            implied_gq_other=lambda df: df["rate_gq_other"]
            * (df["pop"] - df["gq_mil"] - df["gq_prison"]),
            # Then adjust the rates to match the actual group quarters
            rate_gq_college=lambda df: df["gq_college"]
            / df["implied_gq_college"].replace(0, 1)
            * df["rate_gq_college"],
            rate_gq_other=lambda df: df["gq_other"]
            / df["implied_gq_other"].replace(0, 1)
            * df["rate_gq_other"],
        )
    )[["age", "sex", "ethnicity", "rate_gq_college", "rate_gq_other"]]

    # Distribute household formation rates to single year of age
    # And scale rates to match total households from SANDAG's Estimates Program
    hh_rates = (
        # Merge the population DataFrame with the household formation rates
        # Expanded to single year of age uniformly within each age group
        population.merge(
            hh_formation_rates.merge(sya_map, on="age_group"),
            on=["age", "sex", "ethnicity"],
        ).assign(
            # First calculate the implied households using the rates
            # Only apply to the household population
            implied_hh=lambda df: (df["rate_hh"] * df["hhp"])
        )
    )

    # Then adjust the implied counts to match the total household count
    # Ensuring individual household counts are integerized
    hh_rates["implied_hh"] = utils.integerize_1d(
        data=hh_rates["implied_hh"],
        control=total_hh.sum().values[0],  # type: ignore
        methodology="weighted_random",
        generator=generator,
    )

    # Finally re-calculate the rates avoiding divide by zero errors
    hh_rates["rate_hh"] = np.where(
        hh_rates["hhp"] > 0,
        hh_rates["implied_hh"] / hh_rates["hhp"],
        0,
    )

    hh_rates = hh_rates[["age", "sex", "ethnicity", "rate_hh"]]

    # Return the final formation rates DataFrame
    return hh_rates.merge(gq_rates, on=["age", "sex", "ethnicity"])


def _validate_formation_outputs(formation_outputs: pd.DataFrame) -> None:
    """Validate the output dataset for formation rate generation."""
    # Validate the output formation rates
    tests.validate_data(
        table_name="OutputFormation Rates",
        data=formation_outputs,
        row_count={"key_columns": {"age", "sex", "ethnicity"}},
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )
