"""Get birth rates by race and single year of age."""

import logging
import pandas as pd
import numpy as np
import sqlalchemy as sql

import python.utils as utils

from python.tests import validate_data

logger = logging.getLogger(__name__)


def get_birth_rates(yr: int) -> pd.DataFrame:
    """Create birth rates broken down by race and single year of age.

    Birth rates are provided using CDC WONDER Natality births for 5-year age
    groups ranging from ages 15 to 44 then inflated to account for the % of births
    attributed to:
        1) Ages 15 and under
        2) Ages 45 and over
        3) "Unknown", "Not Stated", "Not Available", or "Not Reported" race/ethnicity groups

    Args:
        yr: Increment year

    Returns:
        pd.DataFrame: Birth rates broken down by race and single year of age
    """
    # Birth rates calculated from base year up to the launch year
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
                "Empty birth rates found after applying geographic"
                "hierarchy. Verify rates are available for geographies."
            )

        # Validate output has correct structure
        validate_data(
            table_name=f"Birth Rates (year {yr})",
            # Rename columns to test against the expected naming convention for fertility data
            data=df[["race", "sex", "age", "rate_birth"]].rename(
                columns={"sex": "sex_births", "age": "age_births"}
            ),
            row_count={"key_columns": {"race", "sex_births", "age_births"}},
            negative={"negative_ok": set()},
            null={"null_ok": set()},
        )

        return df

    else:
        raise ValueError("Birth rates not calculated past launch year")
