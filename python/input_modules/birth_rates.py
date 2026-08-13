"""Get birth rates by race and single year of age."""

import logging
import pandas as pd
import numpy as np
import sqlalchemy as sql

import python.utils as utils

logger = logging.getLogger(__name__)


def get_birth_rates(yr: int) -> pd.DataFrame:
    """Create birth rates broken down by race and single year of age.

    Birth rates are calculated using CDC WONDER Natality births for 5-year age
    groups ranging from ages 15 to 44 setting "Suppressed" raw births
    (values < 10) to values of 4.5 and dividing the raw births by five, as
    5-years of births are always from CDC WONDER. Births are merged with the
    base/launch year population (aggregated to 5-year age groups), inflated to
    account for the % of births attributed to "unknown" race/ethnicity groups,
    and then QC'ed to ensure no race or 5-year age group contains 0 births or
    births greater than the total population within the category.

    Note that no inflation factor is made to account for births assigned to
    under 15 or 45+ age groups that are excluded.

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
                utils.ROOT_FOLDER / "sql" / "fertility" / "cdc_wonder_fertility.sql"
            ) as file:
                births = pd.read_sql_query(
                    sql=sql.text(file.read()), con=con, params={"year": yr}
                )
                print("CDC WONDER fertility data loaded from database:")

            # Load inflation factors
            with open(
                utils.ROOT_FOLDER
                / "sql"
                / "fertility"
                / "cdc_wonder_fertility_inflation.sql"
            ) as file:
                inflation_factor = pd.read_sql_query(
                    sql=sql.text(file.read()), con=con, params={"year": yr}
                )
                print("CDC WONDER fertility inflation factors loaded from database:")

        # Calculate rates for 5-year age groups
        group_rates = (
            pd.merge(births, inflation_factor, on=["location", "year"])
            .assign(
                rate=lambda x: x["rate"] * x["inflation_factor"],
            )[["location", "race", "age_group", "hispanic_origin", "rate"]]
            .drop_duplicates()  # Remove duplicate rows for each age_group
        )

        # Merge group rates back to individual ages
        result = (
            births[["location", "race", "age", "age_group", "hispanic_origin"]]
            .merge(group_rates, on=["location", "race", "age_group", "hispanic_origin"])
            .drop(columns=["age_group"])
            .loc[lambda x: x["location"] == "San Diego County", ["race", "age", "rate"]]
            .assign(sex="F")
            .rename(columns={"rate": "rate_birth"})
        )

        # Check for any null values in the rates column
        if result["rate_birth"].isnull().any():
            raise ValueError(
                "Empty birth rates found after applying geographic"
                "hierarchy. Verify rates are available for San Diego County."
            )

        return result

    else:
        raise ValueError("Birth rates not calculated past launch year")
