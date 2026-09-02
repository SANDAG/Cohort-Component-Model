"""Get birth rates by single year of age and race."""

import logging

import pandas as pd
import numpy as np
import sqlalchemy as sql

import python.tests as tests
import python.utils as utils

logger = logging.getLogger(__name__)


def calculate_birth_rates(yr: int) -> pd.DataFrame:
    """Calculate fertility rates broken down by single year of age, sex, and race.

    Fertility rates are provided using CDC WONDER Natality births for 5-year age
    groups ranging from ages 15 to 44 then inflated to account for the % of births
    attributed to:
        1) Ages 15 and under
        2) Ages 45 and over
        3) "Unknown", "Not Stated", "Not Available", or "Not Reported" race/ethnicity groups

    Args:
        yr (int): Increment year

    Returns:
        pd.DataFrame: Fertility rates broken down by single year of age, sex, and race
    """
    # Fertility rates calculated from base year up to the launch year
    if yr <= utils.LAUNCH_YEAR:

        with utils.SQL_ENGINE.connect() as con:

            # Load CDC WONDER data from database for the specific year only
            with open(
                utils.SQL_FOLDER / "fertility" / "cdc_wonder_fertility.sql"
            ) as file:
                births = pd.read_sql_query(
                    sql=sql.text(file.read()), con=con, params={"year": yr}
                )
                logger.info("CDC WONDER fertility data loaded from database")

            # Load inflation factors
            with open(
                utils.SQL_FOLDER / "fertility" / "cdc_wonder_fertility_inflation.sql"
            ) as file:
                inflation_factor = pd.read_sql_query(
                    sql=sql.text(file.read()), con=con, params={"year": yr}
                )
                logger.info(
                    "CDC WONDER fertility inflation factors loaded from database"
                )

        # Calculate inflated rates for individual ages
        result = (
            pd.merge(births, inflation_factor, on=["location", "year"])
            .assign(
                rate=lambda x: x["rate"] * x["inflation_factor"],
                sex="F",
            )
            .rename(columns={"rate": "rate_birth"})[
                ["location", "race", "age", "hispanic_origin", "rate_birth", "sex"]
            ]
        )

        # Pivot by location to get county, state, national as separate columns
        pivoted = (
            result.pivot_table(
                index=["age", "race", "sex", "hispanic_origin"],
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
            pivoted[["age", "race", "sex", "rate_birth"]]
            .sort_values(by=["sex", "race", "age"])
            .reset_index(drop=True)
        )

        # Check for any null values in the rates column
        if df["rate_birth"].isnull().any():
            raise ValueError(
                "Empty fertility rates found after applying geographic"
                "hierarchy. Verify rates are available for geographies."
            )

        # Validate output has correct structure
        tests.validate_data(
            table_name=f"Fertility Rates (year {yr})",
            # Rename columns to test against the expected naming convention for fertility data
            data=df[["race", "age", "rate_birth"]].rename(
                columns={"age": "age_births"}
            ),
            row_count={"key_columns": {"race", "age_births"}},
            negative={"negative_ok": set()},
            null={"null_ok": set()},
        )

        return df

    else:
        raise ValueError("Fertility rates not calculated past launch year")


def get_birth_rates(yr: int) -> pd.DataFrame:
    """Create fertility rates broken down by single year of age, sex, and race.

    For each year up to launch, calculate the crude fertility rate within single year of age, sex,
    and race. For post-launch years, if fertility controls are provided, use the year-specific rates.

    Args:
        yr (int): Increment year

    Returns:
        pd.DataFrame: Fertility rates broken down by single year of age, sex, and race
            with columns (age, sex, race, rate_birth).
    """

    # Fertility rates calculated from base year up to the launch year
    if yr <= utils.LAUNCH_YEAR:
        rates = calculate_birth_rates(yr=yr)

    # Post-launch year
    else:
        # If fertility rates are provided, use them
        if utils.FERTILITY_RATES is not None:
            # Filter to the specific year
            rates = utils.FERTILITY_RATES.loc[
                utils.FERTILITY_RATES["year"] == yr
            ].copy()

            # Drop year column to match expected output format
            rates = rates.drop(columns=["year"])
        else:
            # No rates provided or year not in CSV - hold jump-off rates constant
            rates = calculate_birth_rates(yr=utils.LAUNCH_YEAR)

    return rates[["race", "sex", "age", "rate_birth"]]
