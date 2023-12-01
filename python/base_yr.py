"""Generate base year population by race, sex, and single year of age."""
# TODO: Add 2010-2019 base year generation using 2010 decennial Census.

import numpy as np
import pandas as pd


def get_active_duty_mil(
    base_yr: int,
    base_df: pd.DataFrame,
    acs5yr_pums_persons: pd.DataFrame,
    acs5yr_pums_ca_mil: pd.DataFrame,
    dmdc_location_report: pd.DataFrame,
    sdmac_report: pd.DataFrame,
) -> pd.DataFrame:
    """Add active-duty military population total to the base year total
    population data broken down by race, sex, and single year of age for the
    chosen base year.

    Note: There is concern about the plausibility of race, sex, age
    categories where the entire population is classified as active-duty
    military. If this becomes an issue in need of correction there are two
    recommended strategies. Use three non-overlapping 5-year ACS PUMS persons
    files to ensure distribution of military population across categories is
    plausible and/or alter the "excess population" distribution process to cap
    active-duty military at X% of total population within each category.

    Args:
        base_yr: Chosen base year
        base_df (pd.DataFrame): Base year population data broken down by
            race, sex, and single year of age
        acs5yr_pums_persons (pd.DataFrame): 5-year ACS PUMS persons
        acs5yr_pums_ca_mil (pd.DataFrame): Total active-duty military
            population for the State of CA from 5-year ACS PUMS persons
        dmdc_location_report (pd.DataFrame): DMDC website location report
            https://dwp.dmdc.osd.mil/dwp/app/dod-data-reports/workforce-reports
        sdmac_report (pd.DataFrame): SDMAC Annual EIR data
            https://sdmac.org/reports/past-sdmac-economic-impact-reports

    Returns:
        pd.DataFrame: The input base year total population data with
            the active-duty military population total broken down by race,
            sex, and single year of age
    """
    # Merge the base year dataset with the 5-year ACS PUMS
    # For the chosen base year to add active-duty military population
    df = base_df.merge(
        right=acs5yr_pums_persons[acs5yr_pums_persons["year"] == base_yr][
            ["race", "sex", "age", "pop_mil"]
        ],
        how="left",
        on=["race", "sex", "age"],
    ).fillna(0)

    # Scale the active-duty ACS PUMS population by external control total
    # If base year is prior to 2018
    if 2010 <= base_yr < 2018:
        # Scale the active-duty ACS PUMS population such that the total for the
        # State of California matches the active-duty total control from the
        # DMDC location report for the chosen base year
        scale_pop_mil_pct = (
            dmdc_location_report[dmdc_location_report["year"] == base_yr][
                "active duty - total"
            ].iloc[0]
            / acs5yr_pums_ca_mil[acs5yr_pums_ca_mil["year"] == base_yr][
                "pop_ca_mil"
            ].iloc[0]
        )
    elif 2018 <= base_yr < 2030:
        # Scale the active-duty ACS PUMS population such that the total for
        # San Diego County matches the active-duty total control from the
        # SDMAC report for the chosen base year
        scale_pop_mil_pct = (
            sdmac_report[
                (sdmac_report["report"] == base_yr)
                & (sdmac_report["year"] == base_yr)
                & (sdmac_report["site"] == "All")
            ]["active duty"].iloc[0]
            / df["pop_mil"].sum()
        )
    else:
        raise ValueError("Invalid base year.")

    df["pop_mil"] = df["pop_mil"] * scale_pop_mil_pct

    # Distribute excess active-duty military from categories where
    # The active-duty military exceeds the total population
    # To categories where it is less than the total population using the
    # Distribution of active-duty military within categories where the
    # Active-duty military is less than the total population
    excess_mil = (
        df[df["pop_mil"] > df["pop"]]["pop_mil"].sum()
        - df[df["pop_mil"] > df["pop"]]["pop"].sum()
    )

    while excess_mil > 0:
        df["pop_mil"] = np.where(df["pop_mil"] > df["pop"], df["pop"], df["pop_mil"])

        condition = df["pop_mil"] < df["pop"]

        df.loc[condition, "pop_mil"] = df.loc[condition]["pop_mil"] + (
            excess_mil
            * df.loc[condition]["pop_mil"]
            / df.loc[condition]["pop_mil"].sum()
        )

        excess_mil = (
            df[df["pop_mil"] > df["pop"]]["pop_mil"].sum()
            - df[df["pop_mil"] > df["pop"]]["pop"].sum()
        )

    df["pop_non_mil"] = df["pop"] - df["pop_mil"]
    return df[["race", "sex", "age", "pop", "pop_non_mil", "pop_mil"]]


def get_base_yr_2020(
    base_yr: int,
    acs5yr_pums_persons: pd.DataFrame,
    dof_estimates: pd.DataFrame,
    dof_projections: pd.DataFrame,
    census_redistricting: pd.DataFrame,
) -> pd.DataFrame:
    """Generate base year population data broken down by race, sex, and single
    year of age for base years from 2020-2029. Due to issues with the 2020
    Census a blended approach is used instead of just using the decennial Census.

    Calculate the average of 5-year ACS PUMS persons and CA DOF Population
    Projections for 2020. Scale the resulting population within race
    categories using the Census Redistricting file for 2020. Finally, control
    the total population by the CA DOF Population Estimates for the chosen
    base year.

    Args:
        base_yr (int): Chosen base year
        acs5yr_pums_persons (pd.DataFrame): 5-year ACS PUMS persons
        dof_estimates (pd.DataFrame): CA DOF Population Estimates
        dof_projections (pd.DataFrame): CA DOF Population Projections
        census_redistricting (pd.DataFrame): Census Redistricting File
            (Public Law 94-171) Dataset for California for 2020.

    Returns:
        pd.Dataframe: Base year population data broken down by race, sex, and
            single year of age
    """

    if 2020 not in acs5yr_pums_persons["year"].unique():
        raise ValueError("2020 not in ACS PUMS persons dataset")

    if base_yr not in dof_estimates["vintage"].unique():
        raise ValueError(str(base_yr) + ": Not in DOF Estimates dataset")

    if 2020 not in dof_projections["year"].unique():
        raise ValueError("2020 not in DOF Projections dataset")

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
    scale_race = df[["race", "pop_blended"]].groupby(by=["race"]).sum()
    scale_race = scale_race.merge(right=census_redistricting, how="left", on="race")
    scale_race["pct_race"] = scale_race["pop"] / scale_race["pop_blended"]
    df = df.merge(right=scale_race[["race", "pct_race"]], how="left", on="race")
    df["pop_blended"] = df["pop_blended"] * df["pct_race"]

    # Take the blended estimate and apply population-level scaling factor
    # Matching the DOF Estimates value for total population for the
    # Chosen base year
    scale_pop_pct = (
        dof_estimates[
            (dof_estimates["vintage"] == base_yr) & (dof_estimates["year"] == base_yr)
        ]["pop"].iloc[0]
        / df["pop_blended"].sum()
    )

    # Return blended estimate of population by race/sex/age
    df["pop"] = df["pop_blended"] * scale_pop_pct
    return df[["race", "sex", "age", "pop"]]
