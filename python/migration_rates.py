"""Get migration rates by race, sex, and single year of age."""
# TODO: (10-feature) Add function to allow for control totals at each increment for in/out migration.
# TODO: (5-feature) Potentially implement smoothing function within race and sex categories.

import pandas as pd
import numpy as np


def get_migration_rates(
    yr: int, launch_yr: int, pop_df: pd.DataFrame, acs5yr_pums_migrants: pd.DataFrame
) -> pd.DataFrame:
    """Create migration rates broken down by race, sex, and single year of age.

    Merge the population dataset with the 5-year ACS PUMS count of in/out
    migrants for San Diego County. Calculate the crude migration rate within
    race, sex, and single year of age capping the rates at 20% within each
    category removing active-duty military population from the calculation.

    Args:
        yr: Increment year
        launch_yr: Launch year
        pop_df (pd.DataFrame): Population data broken down by race, sex, and
            single year of age
        acs5yr_pums_migrants (pd.DataFrame): 5-year ACS PUMS in/out migrants
            for San Diego County

    Returns:
        pd.DataFrame: Migration rates broken down by race, sex, and single
            year of age.
    """
    # Migration rates calculated from base year up to the launch year
    if yr <= launch_yr:
        if yr not in acs5yr_pums_migrants["year"].unique():
            raise ValueError(str(yr) + ": not in ACS 5-year PUMS Migrants")

        # Merge base year and migrant datasets calculating crude migration rates
        # Removing active-duty military population from the calculation
        df = (
            pop_df.merge(
                right=acs5yr_pums_migrants[acs5yr_pums_migrants["year"] == yr],
                how="left",
                on=["race", "sex", "age"],
            )
            .assign(rate_in=lambda x: x["in"] / (x["pop"] - x["pop_mil"]))
            .assign(rate_out=lambda x: x["out"] / (x["pop"] - x["pop_mil"]))
            .fillna(0)  # fill NAs with 0s (0% migration rates)
        )

        # Cap crude migration rates at 20%
        df["rate_in"] = np.where(df["rate_in"] > 0.2, 0.2, df["rate_in"])
        df["rate_out"] = np.where(df["rate_out"] > 0.2, 0.2, df["rate_out"])

        return df[["race", "sex", "age", "rate_in", "rate_out"]]

    # Migration rates are not calculated after the launch year
    # TODO: (10-feature) Adjustments to migration rates would be made post-launch year through horizon
    else:
        raise ValueError("Migration rates not calculated past launch year")
