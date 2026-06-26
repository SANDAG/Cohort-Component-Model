"""Generate base year population by race, sex, and single year of age."""

import logging
import numpy as np
import pandas as pd

import python.utils as utils

logger = logging.getLogger(__name__)


def get_base_yr_2020() -> pd.DataFrame:
    """Generate base year 2020 population data broken down by race, sex, and
    single year of age for launch years from 2020-2029. Due to issues with the
    2020 Census a blended approach is used instead of just using the decennial
    Census.

    Calculate the average of 5-year ACS PUMS persons and CA DOF Population
    Projections for 2020 using the vintage from the chosen launch year. Scale
    the resulting population within race categories using the Census P5 table
    for 2020. Finally, control the total population by the CA DOF Population
    Estimates for 2020 using the CA DOF Population Estimates vintage from the
    chosen launch year.

    Returns:
        pd.Dataframe: Base year 2020 population data broken down by race,
            sex, and single year of age
    """
    # Load SQL queries and apply checks to datasets
    with utils.SQL_ENGINE.connect() as connection:
        # Load ACS PUMS persons
        with open(utils.SQL_FOLDER / "pums_persons.sql", "r") as query:
            pums_persons_df = pd.read_sql_query(
                query.read().format(yr=2020), connection
            )
            if len(pums_persons_df.index) == 0:
                raise ValueError("2020: not in ACS 5-year PUMS")

        # Load DOF Estimates
        with open(utils.SQL_FOLDER / "dof_estimates.sql", "r") as query:
            dof_estimates_df = pd.read_sql_query(query.read(), connection)
            if (
                utils.LAUNCH_YEAR
                not in dof_estimates_df["vintage"].astype(int).unique()
            ):
                raise ValueError("Launch year not in DOF Estimates")

        # Load DOF Projections
        with open(utils.SQL_FOLDER / "dof_projections.sql", "r") as query:
            dof_projections_df = pd.read_sql_query(query.read(), connection)
            dof_projections_yr = utils.LAUNCH_YEAR
            if 2020 not in dof_projections_df["year"].unique():
                raise ValueError("2020: not in DOF Projections")
            # If projections have not been released for the launch year
            # Use the most recent projection from the DOF and warn the user
            elif (
                utils.LAUNCH_YEAR
                not in dof_projections_df["vintage"].astype(int).unique()
            ):

                dof_projections_yr = max(
                    dof_projections_df["vintage"][
                        dof_projections_df["vintage"] <= utils.LAUNCH_YEAR
                    ].astype(int)
                )

                logger.warning(
                    """DOF projection unavailable for launch year. Default to most recent
                    DOF projection vintage year: """
                    + str(dof_projections_yr)
                )

        # Load 2020 Census P5 table
        with open(utils.SQL_FOLDER / "census_p5.sql", "r") as query:
            census_p5_df = pd.read_sql_query(query.read(), connection)

    # Create a blended estimate of the total population distribution for 2020
    # From the 5-year ACS PUMS persons file and the CA DOF population projections
    # The blended estimate uses the average of the PUMS and DOF population for age <= 90
    # And uses solely DOF population for age > 90 or where no PUMS data is available
    df = pd.merge(
        dof_projections_df[
            (dof_projections_df["vintage"].astype(int) == dof_projections_yr)
            & (dof_projections_df["year"] == 2020)
        ],
        pums_persons_df,
        how="left",
        on=["race", "sex", "age"],
        suffixes=("_dof", "_pums"),
    )

    df["pop_blended"] = np.where(
        (df["age"] > 90) | (df["pop_pums"].isna()),
        df["pop_dof"],
        (df["pop_dof"] + df["pop_pums"]) / 2,
    )

    # Take the blended estimate and apply race-level scaling factors
    # Using the Census P5 table population by race
    scale_race = (
        df[["race", "pop_blended"]]
        .groupby(by=["race"])
        .sum()
        .merge(right=census_p5_df, how="left", on="race")
        .assign(pct_race=lambda x: x["pop"] / x["pop_blended"])
    )

    df = df.merge(right=scale_race[["race", "pct_race"]], how="left", on="race")
    df["pop_blended"] = df["pop_blended"] * df["pct_race"]

    # Take the blended estimate and apply population-level scaling factor
    # Matching the 2020 DOF Estimates value for total population
    # From the vintage associated with the chosen launch year
    scale_pop_pct = (
        dof_estimates_df[
            (dof_estimates_df["vintage"].astype(int) == utils.LAUNCH_YEAR)
            & (dof_estimates_df["year"] == 2020)
        ]["pop"].iloc[0]
        / df["pop_blended"].sum()
    )

    # Return blended estimate of population by race/sex/age
    df["pop"] = df["pop_blended"] * scale_pop_pct

    return df[["race", "sex", "age", "pop"]]
