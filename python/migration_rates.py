"""Get migration rates by race, sex, and single year of age."""
# TODO: Add function to allow for control totals at each increment for in/out migration.
# TODO: Potentially implement smoothing function within race and sex categories.

import pandas as pd
import numpy as np


def get_migration_rates(
    base_yr: int, base_df: pd.DataFrame, acs5yr_pums_migrants: pd.DataFrame
) -> pd.DataFrame:
    """Create migration rates broken down by race, sex, and single year of age.

    Merge the base year population dataset with the base year 5-year ACS PUMS
    count of in/out migrants for San Diego County. Calculate the crude
    migration rate within race, sex, and single year of age capping the rates
    at 20% within each category.

    Args:
        base_yr (int): Chosen base year
        base_df (pd.DataFrame): Base year population data broken down by
            race, sex, and single year of age
        acs5yr_pums_migrants (pd.DataFrame): 5-year ACS PUMS in/out migrants
            for San Diego County

    Returns:
        pd.DataFrame: Migration rates broken down by race, sex, and single
            year of age.
    """

    if base_yr not in acs5yr_pums_migrants["year"].unique():
        raise ValueError(str(base_yr) + ": Not in ACS PUMS 5-Year Migrant dataset")

    # Merge base year and migrant datasets calculating crude migration rates
    df = (
        base_df.merge(
            right=acs5yr_pums_migrants[acs5yr_pums_migrants["year"] == base_yr],
            how="left",
            on=["race", "sex", "age"],
        )
        .assign(rate_in=lambda x: x["in"] / x["pop_non_mil"])
        .assign(rate_out=lambda x: x["out"] / x["pop_non_mil"])
        .fillna(0)  # fill NAs with 0s (0% migration rates)
    )

    # Cap crude migration rates at 20%
    df["rate_in"] = np.where(df["rate_in"] > 0.2, 0.2, df["rate_in"])
    df["rate_out"] = np.where(df["rate_out"] > 0.2, 0.2, df["rate_out"])

    return df[["race", "sex", "age", "rate_in", "rate_out"]]
