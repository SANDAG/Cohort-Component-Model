"""Get migration rates by single year of age, sex, and race/ethnicity."""

# TODO: (5-feature) Potentially implement smoothing function.

import numpy as np
import pandas as pd
import sqlalchemy as sql

import python.utils as utils


def get_migration_rates(year: int, population: pd.DataFrame) -> pd.DataFrame:
    """Create migration rates broken down by single year of age, sex, and race/ethnicity.

    For the launch year, merge the population dataset with the 5-year
    ACS PUMS count of in/out migrants for San Diego County. Calculate the
    crude migration rate within single year of age, sex, and race/ethnicity
    capping the rates at 20% within each category removing group quarters
    military and prison populations from the calculation.

    Post launch year, the launch year migration rates are scaled to match
    asserted migration control totals for ins/outs if they are provided.
    Otherwise, the function should not be called.

    Args:
        year: Increment year
        population (pd.DataFrame): Population data by single year of age, sex,
            and race/ethnicity

    Returns:
        pd.DataFrame: Migration rates by single year of age, sex, and
            race/ethnicity
    """
    # Migration rates calculated for the launch year
    if year == utils.LAUNCH_YEAR:
        return calculate_migration_rates(
            year=year,
            population=population,
            cap_rates=0.2,
        )

    # Migration rates are not calculated after the launch year
    # Post-launch rates are controlled to annual in/out totals if provided
    else:
        if utils.MIGRATION_CONTROLS is not None:
            # TODO: Re-calculating every increment post launch is inefficient
            rates = calculate_migration_rates(
                year=utils.LAUNCH_YEAR,  # type: ignore
                population=population,
                cap_rates=0.2,
            )

            return control_migration_rates(
                year=year, population=population, rates=rates
            )

        else:
            raise ValueError(
                "Function called post launch year but migration controls not provided."
            )


def calculate_migration_rates(
    year: int,
    population: pd.DataFrame,
    cap_rates: float,
) -> pd.DataFrame:
    """Calculate migration rates for a specific source year.

    Args:
        year: Source year for ACS PUMS migrants query
        population (pd.DataFrame): Population data by single year of age, sex,
            and race/ethnicity
        cap_rates (float): Maximum allowed migration rate (e.g., 0.2 for 20%)

    Returns:
        pd.DataFrame: Migration rates by single year of age, sex, and
            race/ethnicity
    """
    if cap_rates <= 0 or cap_rates >= 1:
        raise ValueError("cap_rates parameter must be between 0 and 1")

    with utils.CCM_ENGINE.connect() as connection:
        with open(utils.SQL_FOLDER / "pums_migrants.sql", "r") as file:
            pums_migrants = pd.read_sql_query(
                sql.text(file.read()), connection, params={"year": year}
            )
        if len(pums_migrants.index) == 0:
            raise ValueError(str(year) + ": not in ACS PUMS in/out migrants")

    df = (
        population.merge(
            right=pums_migrants,
            how="left",
            on=["age", "sex", "ethnicity"],
        )
        # The Military and Prison populations do not migrate
        .assign(pop_civ=lambda x: x["pop"] - x["gq_mil"] - x["gq_prison"])
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

    return df[["age", "sex", "ethnicity", "rate_in", "rate_out"]]


def control_migration_rates(
    year: int,
    population: pd.DataFrame,
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
        year: Increment year
        population (pd.DataFrame): Population data by single year of age, sex,
            and race/ethnicity
        rates (pd.DataFrame): Migration rates by single year of age, sex, and
            race/ethnicity
        cap_rates (float): Maximum allowed migration rate (e.g., 0.2 for 20%)

    Returns:
        pd.DataFrame: Migration rates controlled to in/out migrant totals by
            single year of age, sex, and race/ethnicity
    """
    if cap_rates <= 0 or cap_rates >= 1:
        raise ValueError("cap_rates parameter must be between 0 and 1")

    # Check the controls DataFrame is valid and return controls for the given year
    if utils.MIGRATION_CONTROLS is not None:
        controls = utils.MIGRATION_CONTROLS.loc[
            utils.MIGRATION_CONTROLS["year"] == year
        ]

        # Calculate the total in/out migrants from the rates and population
        # Note this uses the civilian population as opposed to the survived civilian population
        # Migration rates are applied to the survived civilian population to get true in/out migrants
        # Therefore this, along with the capped rates, will lead to a discrepancy
        # between the controlled rates and the actual in/out migrants
        df = (
            population[["age", "sex", "ethnicity", "pop", "gq_mil", "gq_prison"]]
            .merge(rates, how="left", on=["age", "sex", "ethnicity"])
            .fillna(0)
            .assign(
                pop_civ=lambda x: x["pop"] - x["gq_mil"] - x["gq_prison"],
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

        return df[["age", "sex", "ethnicity", "rate_in", "rate_out"]]
    else:
        raise ValueError("Migration controls are not defined in the configuration.")
