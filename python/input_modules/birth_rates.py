"""Get birth rates by single year of age and race/ethnicity."""

import logging

import pandas as pd
import numpy as np
import sqlalchemy as sql

import python.tests as tests
import python.utils as utils

logger = logging.getLogger(__name__)


def calculate_birth_rates(year: int) -> pd.DataFrame:
    """Calculate fertility rates by single year of age, sex, and race/ethnicity.

    Fertility rates are provided using CDC WONDER Natality births for 5-year
    age groups ranging from ages 15 to 44 then inflated to account for the %
    of births attributed to:
        1) Ages 15 and under
        2) Ages 45 and over
        3) "Unknown", "Not Stated", "Not Available", or "Not Reported" race/ethnicity groups

    Args:
        year (int): Increment year

    Returns:
        pd.DataFrame: Fertility rates by single year of age, sex, and
            race/ethnicity
    """
    # Fertility rates calculated for the launch year
    if year == utils.LAUNCH_YEAR:
        with utils.CCM_ENGINE.connect() as con:
            # Load fertility rates
            with open(
                utils.SQL_FOLDER / "fertility" / "cdc_wonder_fertility.sql"
            ) as file:
                births = pd.read_sql_query(
                    sql=sql.text(file.read()), con=con, params={"year": year}
                )
                logger.info("CDC WONDER fertility data loaded from database")

            # Load inflation factors
            with open(
                utils.SQL_FOLDER / "fertility" / "cdc_wonder_fertility_inflation.sql"
            ) as file:
                inflation_factor = pd.read_sql_query(
                    sql=sql.text(file.read()), con=con, params={"year": year}
                )
                logger.info(
                    "CDC WONDER fertility inflation factors loaded from database"
                )

        # Inflate the fertility rates with unassigned births
        result = (
            pd.merge(births, inflation_factor, on=["location"])
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

        # Validate output has correct structure
        tests.validate_data(
            table_name=f"Fertility Rates (year {year})",
            # Rename age column for test (birth data only 15-44)
            data=df[["age", "ethnicity", "rate_birth"]].rename(
                columns={"age": "age_births"}
            ),
            row_count={"key_columns": {"age_births", "ethnicity"}},
            negative={"negative_ok": set()},
            null={"null_ok": set()},
        )

        return df[["age", "sex", "ethnicity", "rate_birth"]]

    else:
        raise ValueError("Fertility rates not calculated past launch year")


def get_birth_rates(year: int) -> pd.DataFrame:
    """Create fertility rates by single year of age, sex, and race/ethnicity.

    For the launch year, calculate the crude fertility rate within single year
    of age, sex, and race/ethnicity. Post launch year, if fertility rates are
    provided, use them. Otherwise, the function should not be called.

    Args:
        year (int): Increment year

    Returns:
        pd.DataFrame: Fertility rates by single year of age, sex, and
            race/ethnicity
    """
    # Fertility rates calculated for the launch year
    if year == utils.LAUNCH_YEAR:
        return calculate_birth_rates(year=year)

    # Fertility rates are not calculated past the launch year
    # Post-launch rates are used directly if provided
    else:
        if utils.FERTILITY_RATES is not None:
            # Use the provided rates directly
            return utils.FERTILITY_RATES.loc[utils.FERTILITY_RATES["year"] == year][
                ["age", "sex", "ethnicity", "rate_birth"]
            ]
        else:
            raise ValueError(
                "Function called post launch year but fertility rates not provided."
            )
