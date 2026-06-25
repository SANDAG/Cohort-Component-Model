"""Get migration rates by race, sex, and single year of age."""

# TODO: (5-feature) Potentially implement smoothing function within race and sex categories.

import numpy as np
import pandas as pd

import python.utils as utils


def get_migration_rates(
    yr: int,
    launch_yr: int,
    pop_df: pd.DataFrame,
    pums_migrants: str,
    controls: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Create migration rates broken down by race, sex, and single year of age.

    For each year up to launch, merge the population dataset with the 5-year
    ACS PUMS count of in/out migrants for San Diego County. Calculate the
    crude migration rate within race, sex, and single year of age capping the
    rates at 20% within each category removing active-duty military population
    from the calculation.

    Post launch year, the launch year migration rates are scaled to match
    asserted migration control totals for ins/outs if they are provided.

    Args:
        yr: Increment year
        launch_yr: Launch year
        pop_df (pd.DataFrame): Population data broken down by race, sex, and
            single year of age
        pums_migrants (str): query to get 5-year ACS PUMS in/out
            migrants for San Diego County
        controls (pd.DataFrame | None): Optional migration control totals for post-launch
            years. If provided, migration rates will be adjusted to match these
            totals for in/out migrants.

    Returns:
        pd.DataFrame: Migration rates broken down by race, sex, and single
            year of age.
    """
    # Migration rates calculated from base year up to the launch year
    if yr <= launch_yr:
        rates = calculate_migration_rates(
            yr=yr,
            pop_df=pop_df,
            pums_migrants=pums_migrants,
            cap_rates=0.2,
        )

    # Migration rates are not calculated after the launch year
    # Post-launch rates are controlled to annual in/out totals if provided
    # TODO: Re-calculating every increment post launch is inefficient
    else:

        if controls is not None:
            rates = calculate_migration_rates(
                yr=launch_yr,
                pop_df=pop_df,
                pums_migrants=pums_migrants,
                cap_rates=0.2,
            )

            rates = control_migration_rates(
                yr=yr, pop_df=pop_df, rates=rates, controls=controls
            )

    return rates


def calculate_migration_rates(
    yr: int,
    pop_df: pd.DataFrame,
    pums_migrants: str,
    cap_rates: float,
) -> pd.DataFrame:
    """Calculate migration rates for a specific source year.

    Args:
        yr: Source year for ACS PUMS migrants query
        pop_df (pd.DataFrame): Population data by race, sex, and age
        pums_migrants (str): SQL query path for ACS PUMS in/out migrants
        cap_rates (float): Maximum allowed migration rate (e.g., 0.2 for 20%)

    Returns:
        pd.DataFrame: Migration rates by race, sex, and age
    """
    if cap_rates <= 0 or cap_rates >= 1:
        raise ValueError("cap_rates parameter must be between 0 and 1")

    with utils.SQL_ENGINE.connect() as connection:
        with open(pums_migrants, "r") as query:
            pums_migrants_df = pd.read_sql_query(query.read().format(yr=yr), connection)
        if len(pums_migrants_df.index) == 0:
            raise ValueError(str(yr) + ": not in ACS PUMS in/out migrants")

    df = (
        pop_df.merge(
            right=pums_migrants_df,
            how="left",
            on=["race", "sex", "age"],
        )
        .assign(pop_civ=lambda x: x["pop"] - x["pop_mil"])
        .assign(
            rate_in=lambda x: np.where(
                x["pop_civ"] > 0,
                x["in"] / x["pop_civ"],
                0,
            )
        )
        .assign(
            rate_out=lambda x: np.where(
                x["pop_civ"] > 0,
                x["out"] / x["pop_civ"],
                0,
            )
        )
        .fillna(0)
    )

    # Guard against division edge cases that can produce +/-inf.
    df[["rate_in", "rate_out"]] = df[["rate_in", "rate_out"]].replace(
        [np.inf, -np.inf], 0
    )

    # Cap crude migration rates at the specified cap_rates value
    df["rate_in"] = np.where(df["rate_in"] > cap_rates, cap_rates, df["rate_in"])
    df["rate_out"] = np.where(df["rate_out"] > cap_rates, cap_rates, df["rate_out"])

    return df[["race", "sex", "age", "rate_in", "rate_out"]]


def check_migration_controls(yr: int, controls: pd.DataFrame) -> pd.DataFrame:
    """Check migration control totals."""
    # Ensure controls DataFrame contains required columns
    required_cols = {"year", "ins", "outs"}
    if not required_cols.issubset(controls.columns):
        raise ValueError("Migration controls must contain columns: (year, ins, outs)")

    # Check if increment year is provided in control totals and filter
    if yr not in controls["year"].unique():
        raise ValueError(f"Increment year {yr} not provided in migration controls")
    else:
        controls = controls.loc[controls["year"] == yr]

    # Check control totals are >= 0
    if controls["ins"].sum() < 0 or controls["outs"].sum() < 0:
        raise ValueError(f"Migration control totals for increment year {yr} are <0")

    return controls


def control_migration_rates(
    yr: int,
    pop_df: pd.DataFrame,
    rates: pd.DataFrame,
    controls: pd.DataFrame,
    cap_rates: float = 0.2,
) -> pd.DataFrame:
    """Control migration rates to in/out migration control totals.

    Calculates the total in/out migrants from input rates and population and
    scales migration rates to match input in/out migration control totals.
    Note this uses the civilian population as opposed to the survived civilian
    population whereas migration rates are applied to the survived civilian
    population to get true in/out migrants. This difference, combined with
    capping maximum rates within age/sex/ethnicity categories post-scaling
    will lead to a discrepancy between the controlled rates and the actual
    in/migrants control totals.

    Args:
        yr: Increment year
        pop_df (pd.DataFrame): Population data by race, sex, and age
        rates (pd.DataFrame): Migration rates by race, sex, and age
        controls (pd.DataFrame): In/out migrant control totals
        cap_rates (float): Maximum allowed migration rate (e.g., 0.2 for 20%)

    Returns:
        pd.DataFrame: Migration rates controlled to in/out migrant totals by
            race, sex, and age
    """
    if cap_rates <= 0 or cap_rates >= 1:
        raise ValueError("cap_rates parameter must be between 0 and 1")

    # Check the controls DataFrame is valid and return controls for the given year
    controls = check_migration_controls(yr=yr, controls=controls)

    # Calculate the total in/out migrants from the rates and population
    # Note this uses the civilian population as opposed to the survived civilian population
    # Migration rates are applied to the survived civilian population to get true in/out migrants
    # Therefore this, along with the capped rates, will lead to a discrepancy
    # between the controlled rates and the actual in/out migrants
    df = (
        pop_df[["race", "sex", "age", "pop", "pop_mil"]]
        .merge(rates, how="left", on=["race", "sex", "age"])
        .fillna(0)
        .assign(
            pop_civ=lambda x: x["pop"] - x["pop_mil"],
            ins=lambda x: x["rate_in"] * x["pop_civ"],
            outs=lambda x: x["rate_out"] * x["pop_civ"],
        )
    )

    # Scale the rates such that the ins/outs match the control totals
    df["rate_in"] = df["rate_in"] * (controls["ins"].sum() / df["ins"].sum())
    df["rate_out"] = df["rate_out"] * (controls["outs"].sum() / df["outs"].sum())

    # Cap crude migration rates at the specified cap_rates value
    df["rate_in"] = np.where(df["rate_in"] > cap_rates, cap_rates, df["rate_in"])
    df["rate_out"] = np.where(df["rate_out"] > cap_rates, cap_rates, df["rate_out"])

    return df[["race", "sex", "age", "rate_in", "rate_out"]]
