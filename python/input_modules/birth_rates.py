"""Get birth rates by race and single year of age."""

import logging
import pandas as pd
import numpy as np
import sqlalchemy as sql

import python.utils as utils

logger = logging.getLogger(__name__)


def get_birth_rates(yr: int, pop_df: pd.DataFrame) -> pd.DataFrame:
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
        pop_df (pd.DataFrame): Population data broken down by race, sex, and
            single year of age

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

        # === Merge births with location-specific populations ===

        # San Diego County: Use CCM population (pop_df)
        sd_births = births[births["location"] == "San Diego County"].copy()
        sd_merged = (
            sd_births.merge(
                right=pop_df.loc[
                    (pop_df["sex"] == "F") & (pop_df["age"].between(15, 44))
                ][["race", "age", "pop"]],
                on=["race", "age"],
            )
            .groupby(["year", "location", "race", "age_group", "hispanic_origin"])
            .agg({"births": "max", "pop": "sum"})
            .reset_index()
        )

        # California: Use DOF P3 projections
        ca_births = births[births["location"] == "California"].copy()
        with utils.SQL_ENGINE.connect() as con:
            with open(
                utils.ROOT_FOLDER / "sql" / "fertility" / "dof_projections_p3.sql"
            ) as file:
                ca_pop = pd.read_sql_query(
                    sql=sql.text(file.read()), con=con, params={"year": yr}
                )
                print("DOF P3 projections loaded from database:")

        ca_merged = (
            ca_births.merge(
                right=ca_pop[["race", "age", "pop"]],
                on=["race", "age"],
            )
            .groupby(["year", "location", "race", "age_group", "hispanic_origin"])
            .agg({"births": "max", "pop": "sum"})
            .reset_index()
        )

        # Combine all locations
        merged_births = pd.concat([sd_merged, ca_merged], ignore_index=True)

        # Calculate rates for 5-year age groups
        group_rates = pd.merge(
            merged_births, inflation_factor, on=["location", "year"]
        ).assign(
            births=lambda x: np.where(
                x["births"] * x["inflation_factor"] == 0,
                1,  # Minimum 1 birth
                np.minimum(
                    x["births"] * x["inflation_factor"], x["pop"]  # Cap at population
                ),
            ),
            rates=lambda x: x["births"] / x["pop"],
        )[
            ["location", "race", "age_group", "hispanic_origin", "rates"]
        ]

        # Merge group rates back to individual ages
        final = (
            births[["location", "race", "age", "age_group", "hispanic_origin"]]
            .drop_duplicates()
            .merge(group_rates, on=["location", "race", "age_group", "hispanic_origin"])
            .drop(columns=["age_group"])
        )

        # Pivot by location to get county, state as separate columns
        pivoted = (
            final.pivot_table(
                index=["race", "age", "hispanic_origin"],
                columns="location",
                values=["rates"],
                aggfunc="first",
            )
            .pipe(lambda df: df.set_axis(["_".join(col) for col in df.columns], axis=1))
            .reset_index()
        )

        # Retrieve fields
        county, state = (
            pivoted.get("rates_San Diego County", pd.Series(dtype=float)),
            pivoted.get("rates_California", pd.Series(dtype=float)),
        )

        # Apply geographic hierarchy: County > State
        pivoted["rates"] = np.where(
            (county.notna()) & (county > 0),
            county,
            np.where(
                (state.notna()) & (state > 0),
                state,
                np.nan,  # Use NaN for missing rates
            ),
        )

        # Check for any null values in the rates column
        # If California births are not availabe, add United States population and merge
        # with United States births
        if pivoted["rates"].isnull().any():
            raise ValueError(
                "Empty birth rates found after applying geographic"
                "hierarchy. Verify rates are available for San Diego County and California."
            )

        # Add sex column (all births are to females)
        rates = pivoted[["race", "age", "rates"]].assign(sex="F")

        result = rates.rename(columns={"rates": "rate_birth"})[
            ["race", "sex", "age", "rate_birth"]
        ].copy()

        return result

    else:
        raise ValueError("Birth rates not calculated past launch year")
