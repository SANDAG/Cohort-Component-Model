"""Generate base year population by race, sex, and single year of age."""
# TODO: Add 2010 base year generation using 2010 decennial Census.

import numpy as np
import pandas as pd


def get_base_yr_2020(
    launch_yr: int,
    acs5yr_pums_persons: pd.DataFrame,
    dof_estimates: pd.DataFrame,
    dof_projections: pd.DataFrame,
    census_redistricting: pd.DataFrame,
) -> pd.DataFrame:
    """Generate base year 2020 population data broken down by race, sex, and
    single year of age for launch years from 2020-2029. Due to issues with the
    2020 Census a blended approach is used instead of just using the decennial
    Census.

    Calculate the average of 5-year ACS PUMS persons and CA DOF Population
    Projections for 2020. Scale the resulting population within race
    categories using the Census Redistricting file for 2020. Finally, control
    the total population by the CA DOF Population Estimates for 2020 using the
    CA DOF Population Estimates vintage from the chosen launch year.

    Args:
        launch_yr (int): Launch year
        acs5yr_pums_persons (pd.DataFrame): 5-year ACS PUMS persons 2016-2020
        dof_estimates (pd.DataFrame): CA DOF Population Estimates
        dof_projections (pd.DataFrame): CA DOF Population Projections for 2020
        census_redistricting (pd.DataFrame): Census Redistricting File
            (Public Law 94-171) Dataset for California for 2020

    Returns:
        pd.Dataframe: Base year 2020 population data broken down by race,
            sex, and single year of age
    """

    if 2020 not in acs5yr_pums_persons["year"].unique():
        raise ValueError("2020 not in ACS 5-year PUMS")

    if launch_yr not in dof_estimates["vintage"].unique():
        raise ValueError("Launch year not in DOF Estimates")

    if 2020 not in dof_projections["year"].unique():
        raise ValueError("2020 not in DOF Projections")

    # Create a blended estimate of the total population distribution for 2020
    # From the 5-year ACS PUMS persons file and the CA DOF population projections
    # The blended estimate uses the average of the PUMS and DOF population for age <= 90
    # And uses solely DOF population for age > 90 or where no PUMS data is available
    df = pd.merge(
        dof_projections[dof_projections["year"] == 2020],
        acs5yr_pums_persons[acs5yr_pums_persons["year"] == 2020],
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
    # Using the census redistricting file population by race
    scale_race = (
        df[["race", "pop_blended"]]
        .groupby(by=["race"])
        .sum()
        .merge(right=census_redistricting, how="left", on="race")
        .assign(pct_race=lambda x: x["pop"] / x["pop_blended"])
    )

    df = df.merge(right=scale_race[["race", "pct_race"]], how="left", on="race")
    df["pop_blended"] = df["pop_blended"] * df["pct_race"]

    # Take the blended estimate and apply population-level scaling factor
    # Matching the 2020 DOF Estimates value for total population
    # From the vintage associated with the chosen launch year
    scale_pop_pct = (
        dof_estimates[
            (dof_estimates["vintage"] == launch_yr) & (dof_estimates["year"] == 2020)
        ]["pop"].iloc[0]
        / df["pop_blended"].sum()
    )

    # Return blended estimate of population by race/sex/age
    df["pop"] = df["pop_blended"] * scale_pop_pct
    return df[["race", "sex", "age", "pop"]]
