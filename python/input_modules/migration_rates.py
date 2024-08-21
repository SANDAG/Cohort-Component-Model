"""Get migration rates by race, sex, and single year of age."""

# TODO: (10-feature) Add function to allow for control totals at each increment for in/out migration.
# TODO: (5-feature) Potentially implement smoothing function within race and sex categories.

import pandas as pd
import numpy as np
import sqlalchemy as sql


def get_migration_rates(
    yr: int,
    launch_yr: int,
    pop_df: pd.DataFrame,
    pums_migrants: str,
    engine: sql.engine,
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
        pums_migrants (str): query to get 5-year ACS PUMS in/out
            migrants for San Diego County
        engine (sql.engine): SQLAlchemy MSSQL connection engine

    Returns:
        pd.DataFrame: Migration rates broken down by race, sex, and single
            year of age.
    """
    # Migration rates calculated from base year up to the launch year
    if yr <= launch_yr:
        # Load SQL queries and apply checks to datasets
        with engine.connect() as connection:
            # Load ACS PUMS persons
            with open(pums_migrants, "r") as query:
                pums_migrants_df = pd.read_sql_query(
                    query.read().format(yr=yr), connection
                )
            if len(pums_migrants_df.index) == 0:
                raise ValueError(str(yr) + ": not in ACS PUMS in/out migrants")

        # Merge base year and migrant datasets calculating crude migration rates
        # Removing active-duty military population from the calculation
        df = (
            pop_df.merge(
                right=pums_migrants_df,
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
