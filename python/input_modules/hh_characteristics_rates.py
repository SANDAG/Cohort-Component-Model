"""Get household characteristics rates by age, sex, and race/ethnicity."""

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


def run_hh_characteristics_rates(
    year: int, population: pd.DataFrame, rates: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """Orchestrator function to calculate household characteristics rates.

    This modules generates household characteristics rates broken down by
    single year of age, sex, and race/ethnicity using ACS PUMS data and
    SANDAG's Estimates PRogram. Rates are calculated within age groups and
    then applied uniformly to all single years of age within age groups.

    For each characteristics, if there exists a SANDAG estimates, the total
    number of households within that characteristics category is scaled to
    match the values from SANDAG's Estimates Program for the launch year.

    The final rates, when applied to the launch year households, should yield
    household characteristics counts identical to SANDAG's Estimates PRogram
    for the launch year.

    Functionality is split apart for code encapsulation:
        _get_hh_characteristics_rates_inputs - Get household characteristics
            rates by age group, sex, and ethnicity from the ACS 5-year PUMS
            and the total household characteristics controls from SANDAG's
            Estimates Program
        _validate_hh_characteristics_rates_inputs - Validate inputs from the
            above function
        _create_hh_characteristics_rates_outputs - Placeholder
        _validate_hh_characteristics_rates_outputs - Validate the output from
            the above function
    """
    if year == utils.LAUNCH_YEAR:
        logger.info("Calculating household characteristics rates for launch year")

        hh_characteristics_rates_inputs = _get_hh_characteristics_rates_inputs(year)
        _validate_hh_characteristics_rates_inputs(hh_characteristics_rates_inputs)

        hh_characteristics_rates_outputs = _create_hh_characteristics_rates_outputs(
            hh_characteristics_rates_inputs, population, rates
        )
        _validate_hh_characteristics_rates_outputs(hh_characteristics_rates_outputs)

        return hh_characteristics_rates_outputs
    else:
        raise ValueError(
            "Household characteristics rates can only be run for the launch year."
        )


def _get_hh_characteristics_rates_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Load input datasets for household characteristics rates."""
    with utils.ESTIMATES_ENGINE.connect() as connection:
        with open(
            utils.SQL_FOLDER
            / "hh_characteristics_rates"
            / "get_hh_characteristics_rates.sql",
            "r",
        ) as file:
            hh_characteristics_rates = utils.read_sql_query_fallback(
                sql=sql.text(file.read()),
                con=connection,
                params={
                    "run_id": utils.ESTIMATES_RUN_ID,
                    "year": year,
                },  # type: ignore
            )

        with open(
            utils.SQL_FOLDER
            / "hh_characteristics_rates"
            / "get_total_hh_characteristics.sql",
            "r",
        ) as file:
            total_hh_characteristics = pd.read_sql_query(
                sql=sql.text(file.read()),
                con=connection,
                params={
                    "run_id": utils.ESTIMATES_RUN_ID,
                    "year": year,
                },  # type: ignore
            )

    return {
        "hh_characteristics_rates": hh_characteristics_rates,
        "total_hh_characteristics": total_hh_characteristics,
    }


def _validate_hh_characteristics_rates_inputs(
    hh_characteristics_rates_inputs: dict[str, pd.DataFrame],
) -> None:
    """Validate the input datasets for household characteristics rates."""
    # Validate the household characteristics rates
    tests.validate_data(
        table_name="Input Household Characteristics Rates",
        data=hh_characteristics_rates_inputs["hh_characteristics_rates"],
        row_count={"key_columns": {"age_group", "sex", "ethnicity"}},
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )

    # Validate the total HH count
    tests.validate_data(
        table_name="Total Household Characteristics Counts",
        data=hh_characteristics_rates_inputs["total_hh_characteristics"],
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )


def _create_hh_characteristics_rates_outputs(
    hh_characteristics_rates_inputs: dict[str, pd.DataFrame],
    population: pd.DataFrame,
    rates: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Create outputs for household characteristics rates."""
    hh_characteristics_rates = hh_characteristics_rates_inputs[
        "hh_characteristics_rates"
    ]
    total_hh_characteristics = hh_characteristics_rates_inputs[
        "total_hh_characteristics"
    ]

    # Create a single year of age mapping from age groups
    sya_map = pd.DataFrame(
        (
            {"age": age, "age_group": age_group}
            for age_group, bounds in utils.AGE_MAPPING.items()
            for age in range(bounds["min"], bounds["max"] + 1)
        )
    )

    # Take the population and formation rate DataFrames
    # And calculate households within single year of age, sex, and race/ethnicity
    households = (
        population[["age", "sex", "ethnicity", "hhp"]].merge(
            rates["formation_gq_hh"], on=["age", "sex", "ethnicity"]
        )
        # The Household Formation rates for launch year guarantee integer household counts
        .assign(hh=lambda x: (x["hhp"] * x["rate_hh"]).astype(int))
    )

    # Distribute Household Characteristics rates to single year of age
    # And assign to the households DataFrame by age, sex, and race/ethnicity
    # Scale rates to match total household characteristics from SANDAG's Estimates Program
    # And adjust the rates ensuring they are integers and consistent with household counts
    hh_rates = (
        # Merge the household DataFrame with the household formation rates
        # Expanded to single year of age uniformly within each age group
        households.merge(
            hh_characteristics_rates.merge(sya_map, on="age_group"),
            on=["age", "sex", "ethnicity"],
        ).assign(
            # First calculate implied totals using the rates
            hh_head_lf=lambda x: x["hh"] * x["rate_hh_head_lf"],
            hh_size1=lambda x: x["hh"] * x["rate_hh_size1"],
            hh_size2=lambda x: x["hh"] * x["rate_hh_size2"],
            hh_size3=lambda x: x["hh"] * x["rate_hh_size3"],
            hh_workers0=lambda x: x["hh"] * x["rate_hh_workers0"],
            hh_workers1=lambda x: x["hh"] * x["rate_hh_workers1"],
            hh_workers2=lambda x: x["hh"] * x["rate_hh_workers2"],
            hh_workers3=lambda x: x["hh"] * x["rate_hh_workers3"],
            hh_children=lambda x: x["hh"] * x["rate_hh_children"],
            hh_seniors=lambda x: x["hh"] * x["rate_hh_seniors"],
        )
    )

    # Then adjust the implied counts to match the total counts
    # Ensuring individual counts are integerized
    for col in [
        "hh_head_lf",
        "hh_size1",
        "hh_size2",
        "hh_size3",
        "hh_workers0",
        "hh_workers1",
        "hh_workers2",
        "hh_workers3",
        "hh_children",
        "hh_seniors",
    ]:
        # For fields without SANDAG Estimates controls round summation to integer
        # And control to that value
        if col in ["hh_head_lf", "hh_children", "hh_seniors"]:
            hh_rates[col] = utils.integerize_1d(
                data=hh_rates[col],
                control=round(hh_rates[col].sum()),
                methodology="weighted_random",
                generator=generator,
            ).astype(int)
        # For fields with SANDAG Estimates controls
        # Control to the SANDAG Estimates total
        else:
            hh_rates[col] = utils.integerize_1d(
                data=hh_rates[col],
                control=total_hh_characteristics[col].sum(),  # type: ignore
                methodology="weighted_random",
                generator=generator,
            ).astype(int)

    # Then adjust the implied counts row-wise to ensure consistency with
    # The total household count within single year of age, sex, and race/ethnicity
    hh_rates["hh_head_lf"] = utils.reallocate_integers(
        df=hh_rates, subset="hh_head_lf", total="hh"
    )

    hh_rates[["hh_size1", "hh_size2", "hh_size3"]] = utils.reallocate_group_integers(
        df=hh_rates, cols=["hh_size1", "hh_size2", "hh_size3"], total="hh"
    )

    hh_rates[["hh_workers0", "hh_workers1", "hh_workers2", "hh_workers3"]] = (
        utils.reallocate_group_integers(
            df=hh_rates,
            cols=["hh_workers0", "hh_workers1", "hh_workers2", "hh_workers3"],
            total="hh",
        )
    )

    hh_rates["hh_children"] = utils.reallocate_integers(
        df=hh_rates, subset="hh_children", total="hh"
    )

    hh_rates["hh_seniors"] = utils.reallocate_integers(
        df=hh_rates, subset="hh_seniors", total="hh"
    )

    # Finally, re-calculate the rates avoiding divide by zero errors
    hh_rates = hh_rates.assign(
        rate_hh_head_lf=lambda x: x["hh_head_lf"] / x["hh"].replace({0: 1}),
        rate_hh_size1=lambda x: x["hh_size1"] / x["hh"].replace({0: 1}),
        rate_hh_size2=lambda x: x["hh_size2"] / x["hh"].replace({0: 1}),
        rate_hh_size3=lambda x: x["hh_size3"] / x["hh"].replace({0: 1}),
        rate_hh_workers0=lambda x: x["hh_workers0"] / x["hh"].replace({0: 1}),
        rate_hh_workers1=lambda x: x["hh_workers1"] / x["hh"].replace({0: 1}),
        rate_hh_workers2=lambda x: x["hh_workers2"] / x["hh"].replace({0: 1}),
        rate_hh_workers3=lambda x: x["hh_workers3"] / x["hh"].replace({0: 1}),
        rate_hh_children=lambda x: x["hh_children"] / x["hh"].replace({0: 1}),
        rate_hh_seniors=lambda x: x["hh_seniors"] / x["hh"].replace({0: 1}),
    )

    # Return the final household characteristics rates DataFrame
    return hh_rates[
        [
            "age",
            "sex",
            "ethnicity",
            "rate_hh_head_lf",
            "rate_hh_size1",
            "rate_hh_size2",
            "rate_hh_size3",
            "rate_hh_workers0",
            "rate_hh_workers1",
            "rate_hh_workers2",
            "rate_hh_workers3",
            "rate_hh_children",
            "rate_hh_seniors",
        ]
    ]


def _validate_hh_characteristics_rates_outputs(
    hh_characteristics_rates_outputs: pd.DataFrame,
) -> None:
    """Validate the output household characteristics rates dataset."""
    # Validate the output household characteristics rates
    tests.validate_data(
        table_name="Output Household Characteristics Rates",
        data=hh_characteristics_rates_outputs,
        row_count={"key_columns": {"age", "sex", "ethnicity"}},
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )
