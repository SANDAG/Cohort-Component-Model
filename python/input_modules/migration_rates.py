"""Get migration rates by race, sex, and single year of age."""

# TODO: (5-feature) Potentially implement smoothing function within race and sex categories.

import numpy as np
import pandas as pd

import python.utils as utils


def get_migration_rates(yr: int, pop_df: pd.DataFrame) -> pd.DataFrame:
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
        pop_df (pd.DataFrame): Population data broken down by race, sex, and
            single year of age

    Returns:
        pd.DataFrame: Migration rates broken down by race, sex, and single
            year of age.
    """
    # Migration rates calculated from base year up to the launch year
    if yr <= utils.LAUNCH_YEAR:
        rates = calculate_migration_rates(
            yr=yr,
            pop_df=pop_df,
            cap_rates=0.2,
        )

    # Migration rates are not calculated after the launch year
    # Post-launch rates are controlled to annual in/out totals if provided
    # TODO: Re-calculating every increment post launch is inefficient
    else:

        if utils.MIGRATION_CONTROLS is not None:
            rates = calculate_migration_rates(
                yr=utils.LAUNCH_YEAR,
                pop_df=pop_df,
                cap_rates=0.2,
            )

            rates = control_migration_rates(yr=yr, pop_df=pop_df, rates=rates)

    return rates


def calculate_migration_rates(
    yr: int,
    pop_df: pd.DataFrame,
    cap_rates: float,
) -> pd.DataFrame:
    """Calculate migration rates for a specific source year.

    Args:
        yr: Source year for ACS PUMS migrants query
        pop_df (pd.DataFrame): Population data by race, sex, and age
        cap_rates (float): Maximum allowed migration rate (e.g., 0.2 for 20%)

    Returns:
        pd.DataFrame: Migration rates by race, sex, and age
    """
    if cap_rates <= 0 or cap_rates >= 1:
        raise ValueError("cap_rates parameter must be between 0 and 1")

    with utils.SQL_ENGINE.connect() as connection:
        with open(utils.SQL_FOLDER / "pums_migrants.sql", "r") as query:
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


def control_migration_rates(
    yr: int,
    pop_df: pd.DataFrame,
    rates: pd.DataFrame,
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
        cap_rates (float): Maximum allowed migration rate (e.g., 0.2 for 20%)

    Returns:
        pd.DataFrame: Migration rates controlled to in/out migrant totals by
            race, sex, and age
    """
    if cap_rates <= 0 or cap_rates >= 1:
        raise ValueError("cap_rates parameter must be between 0 and 1")

    # Check the controls DataFrame is valid and return controls for the given year
    controls = utils.MIGRATION_CONTROLS.loc[utils.MIGRATION_CONTROLS["year"] == yr]

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
