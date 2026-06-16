"""Get migration rates by race, sex, and single year of age."""

# TODO: (10-feature) Add function to allow for control totals at each increment for in/out migration.
# TODO: (5-feature) Potentially implement smoothing function within race and sex categories.

import pandas as pd
import numpy as np
import sqlalchemy as sql
import yaml

from python.utils import ROOT_FOLDER, integerize_1d, reallocate_integers


def get_migration_rates(
    yr: int,
    launch_yr: int,
    pop_df: pd.DataFrame,
    pums_migrants: str,
    engine: sql.Engine,
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
        engine (sql.Engine): SQLAlchemy MSSQL connection engine

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

def get_migration_controls(df: pd.DataFrame) -> dict:
    """Convert migration controls CSV data into yearly control dictionary.

    Expected columns are: year, in, out
    """
    with open(ROOT_FOLDER / "config.yml") as f:
        config = yaml.safe_load(f)

    start_yr = config["interval"]["launch"]
    end_yr = config["interval"]["horizon"]

    if start_yr > end_yr:
        raise ValueError("Invalid migration controls interval: start_yr > end_yr")

    required_cols = {"year", "ins", "outs"}
    if not required_cols.issubset(df.columns):
        raise ValueError("Migration controls CSV must contain columns: year, in, out")

    if df["year"].dropna().duplicated().any():
        raise ValueError("Migration controls CSV contains duplicate year values")

    required_years = {str(yr) for yr in range(start_yr, end_yr + 1)}
    provided_years = {str(int(yr)) for yr in df["year"].dropna()}
    missing_years = sorted(required_years - provided_years, key=int)

    if missing_years:
        missing_years_str = ", ".join(missing_years)
        raise ValueError(
            "Migration controls CSV is missing years required by config interval "
            f"[{start_yr}, {end_yr}]: {missing_years_str}"
        )

    controls = {}
    for _, row in df.iterrows():
        if pd.isna(row["year"]):
            raise ValueError("Migration controls CSV contains missing year values")

        year = str(int(row["year"]))
        in_control = row["ins"]
        out_control = row["outs"]

        controls[year] = {
            "in": None if pd.isna(in_control) else int(in_control),
            "out": None if pd.isna(out_control) else int(out_control),
        }

    return controls

def apply_migration_controls(
    df: pd.DataFrame,
    yr: int,
    migration_controls: dict | None,
    generator: np.random.Generator,
) -> pd.DataFrame:
    """Apply optional yearly in/out migration control totals.

    Args:
        df (pd.DataFrame): Input DataFrame
        yr (int): Year for which to apply migration controls
        migration_controls (dict | None): Dictionary containing migration control totals
        generator (np.random.Generator): Random number generator

    Returns:
        pd.DataFrame: DataFrame with applied migration controls
    """
    if migration_controls is None:
        return df

    year_controls = migration_controls.get(str(yr))
    if not year_controls:
        return df

    control_in = year_controls.get("in")
    control_out = year_controls.get("out")

    if control_in is not None:
        control_in = int(control_in)
        if control_in < 0:
            raise ValueError("Migration control totals must be non-negative")

        df["ins"] = integerize_1d(
            data=df["ins"],
            control=control_in, 
            generator=generator,
        )

    if control_out is not None:
        control_out = int(control_out)
        out_capacity = int(df["pop_civ_surv"].sum())
        if control_out > out_capacity:
            raise ValueError(
                f"{yr}: out-migration control ({control_out}) exceeds survived civilian population ({out_capacity})"
            )

        if control_out < 0:
            raise ValueError("Migration control totals must be non-negative")

        df["outs"] = integerize_1d(
            data=df["outs"],
            control=control_out,
            generator=generator,
        )

        df["outs"] = reallocate_integers(df=df, subset="outs", total="pop_civ_surv")

    return df
