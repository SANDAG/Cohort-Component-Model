"""Get birth rates by single year of age and race/ethnicity."""

import logging

import pandas as pd
import numpy as np
import sqlalchemy as sql

import python.tests as tests
import python.utils as utils

logger = logging.getLogger(__name__)


def run_fertility_rates(year: int) -> pd.DataFrame:
    """Orchestrator function to calculate fertility rates.

    This module generates fertility rates by single year of age, sex, and race/ethnicity
    using data from the Centers for Disease Control and Prevention (CDC) natality
    database.

    Functionality is split apart for code encapsulation:
        _get_fertility_inputs - Get fertility rates by age, sex, and ethnicity from CDC natality
            database
        _validate_fertility_inputs - Validate inputs from the above function
        _create_fertility_outputs - Calculate fertility rates by inflating births to account for the
            % of births attributed to:
                1) Ages 15 and under
                2) Ages 45 and over
                3) "Unknown", "Not Stated", "Not Available", or "Not Reported"
                  race/ethnicity groups
        _validate_fertility_outputs - Validate the output from the above function
    """
    if year == utils.LAUNCH_YEAR:
        logger.info("Calculating fertility rates for launch year")

        fertility_rates_inputs = _get_fertility_inputs(year)
        _validate_fertility_inputs(fertility_rates_inputs["fertility_inputs"])

        fertility_outputs = _create_fertility_outputs(fertility_rates_inputs)
        _validate_fertility_outputs(fertility_outputs)

        return fertility_outputs
    else:
        if utils.FERTILITY_RATES is not None:
            # Use the provided rates directly
            return utils.FERTILITY_RATES.loc[utils.FERTILITY_RATES["year"] == year][
                ["age", "sex", "ethnicity", "rate_birth"]
            ]
        else:
            raise ValueError("Fertility rates can only be run for the launch year.")


def _get_fertility_inputs(year: int) -> dict[str, pd.DataFrame]:
    """Retrieve fertility inputs from the CDC natality database for a given year.

    Args:
        year (int): Increment year

    Returns:
        dict[str, pd.DataFrame]: Dictionary containing fertility inputs and inflation
            factors by single year of age, sex, and race/ethnicity
    """
    with utils.CCM_ENGINE.connect() as connection:
        with open(utils.SQL_FOLDER / "fertility" / "cdc_wonder_fertility.sql") as file:
            fertility_inputs = utils.read_sql_query_fallback(
                max_lookback=1,
                sql=sql.text(file.read()),
                con=connection,
                params={"year": year},
            )
            logger.info("CDC WONDER fertility data loaded from database")
        # Load inflation factors
        with open(
            utils.SQL_FOLDER / "fertility" / "cdc_wonder_fertility_inflation.sql"
        ) as file:
            inflation_factor = utils.read_sql_query_fallback(
                max_lookback=1,
                sql=sql.text(file.read()),
                con=connection,
                params={"year": year},
            )
            logger.info("CDC WONDER fertility inflation factors loaded from database")

    return {
        "fertility_inputs": fertility_inputs,
        "fertility_inflation": inflation_factor,
    }


def _validate_fertility_inputs(fertility_inputs: pd.DataFrame) -> None:
    """Validate the fertility inputs.

    Args:
        fertility_inputs (pd.DataFrame): Fertility inputs by single year of age, sex,
            and race/ethnicity
    """
    # Loop through each location and validate the fertility inputs for that location
    for location in fertility_inputs["location"]:
        # Validate input has correct structure
        tests.validate_data(
            table_name="Input Fertility Rates",
            # Rename age column for test (birth data only 15-44)
            data=fertility_inputs[["age", "ethnicity", "rate"]]
            .rename(columns={"age": "age_births"})
            .loc[fertility_inputs["location"] == location],
            row_count={"key_columns": {"age_births", "ethnicity"}},
            negative={"negative_ok": set()},
            null={"null_ok": set()},
        )


def _create_fertility_outputs(
    fertility_inputs: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Create fertility outputs for a given year.

    Args:
        fertility_inputs (dict[str, pd.DataFrame]): Fertility inputs and inflation
            factors by single year of age, sex, and race/ethnicity

    Returns:
        pd.DataFrame: Fertility outputs by single year of age, sex, and race/ethnicity
    """
    fertility_data = fertility_inputs["fertility_inputs"]
    inflation_factor = fertility_inputs["fertility_inflation"]

    # Inflate the fertility rates with unassigned births
    result = (
        pd.merge(fertility_data, inflation_factor, on=["location"])
        .assign(rate=lambda x: x["rate"] * x["inflation_factor"])
        .rename(columns={"rate": "rate_birth"})[
            ["location", "age", "sex", "ethnicity", "rate_birth"]
        ]
    )

    # Pivot by location to get county, state, national as separate columns
    pivoted = (
        result.pivot_table(
            index=["age", "sex", "ethnicity"],
            columns="location",
            values=["rate_birth"],
            aggfunc="first",
        )
        .pipe(lambda df: df.set_axis(["_".join(col) for col in df.columns], axis=1))
        .reset_index()
    )

    # Retrieve fields
    county, state, national = (
        pivoted.get("rate_birth_San Diego County", pd.Series(dtype=float)),
        pivoted.get("rate_birth_California", pd.Series(dtype=float)),
        pivoted.get("rate_birth_United States", pd.Series(dtype=float)),
    )

    # Create Substitution methodology for null values based on geographic hierarchy
    # County > State > National
    pivoted["rate_birth"] = np.where(
        (county.notna()) & (county > 0),
        county,
        np.where(
            (state.notna()) & (state > 0),
            state,
            np.where(
                (national.notna()) & (national > 0),
                national,
                np.nan,
            ),
        ),
    )

    # Finalize combined dataset
    df = (
        pivoted[["age", "sex", "ethnicity", "rate_birth"]]
        .sort_values(by=["age", "sex", "ethnicity"])
        .reset_index(drop=True)
    )

    # Check for any null values in the rates column
    if df["rate_birth"].isnull().any():
        raise ValueError(
            "Empty fertility rates found after applying geographic"
            "hierarchy. Verify rates are available for geographies."
        )

    return df[["age", "sex", "ethnicity", "rate_birth"]]


def _validate_fertility_outputs(fertility_outputs: pd.DataFrame) -> None:
    """Validate the fertility outputs.

    Args:
        fertility_outputs (pd.DataFrame): Fertility outputs dataframe
    """
    # Validate output has correct structure
    tests.validate_data(
        table_name="Output Fertility Rates",
        # Rename age column for test (birth data only 15-44)
        data=fertility_outputs[["age", "ethnicity", "rate_birth"]].rename(
            columns={"age": "age_births"}
        ),
        row_count={"key_columns": {"age_births", "ethnicity"}},
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )
