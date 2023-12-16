"""Get group quarters and household formation rates by race, sex, and single year of age."""
# TODO: (5-feature) Potentially implement smoothing function within race and sex categories.
# TODO: (13-feature) Add CONCEP control totals to adjust household formation rates to match SANDAG estimates.

import pandas as pd
from python.utilities import distribute_excess


def get_formation_rates(
    yr: int,
    launch_yr: int,
    acs5yr_pums_persons: pd.DataFrame,
    dof_estimates: pd.DataFrame,
) -> pd.DataFrame:
    """Generate group quarters and household formation rates broken
    down by race, sex, and single year of age.

    Group quarter and household formation rates are calculated using the
    5-year ACS PUMS persons. Prior to calculation, the total number of group
    quarters are scaled to match the CA DOF Population Estimates.

    Note that formation rates for persons over 70 are calculated as a
    single composite rate for all persons over 70, where group quarters rates
    are calculated within sex and household formation rates within race and
    sex. These rates are then applied uniformly to all single year of age
    categories above 70.

    Args:
        yr: Increment year
        launch_yr: Launch year
        acs5yr_pums_persons (pd.DataFrame): 5-year ACS PUMS persons
        dof_estimates (pd.DataFrame): CA DOF Population Estimates

    Returns:
        pd.DataFrame: Group quarters and household formation rates broken down
            by race, sex, and single year of age
    """
    if yr <= launch_yr:
        if yr not in acs5yr_pums_persons["year"].unique():
            raise ValueError(str(yr) + ": not in ACS 5-year PUMS")

        # Select the 5-year ACS PUMS data
        pums_df = acs5yr_pums_persons[(acs5yr_pums_persons["year"] == yr)].copy()

        # Take total group quarters and apply regional scaling factor
        # Matching the DOF Estimates value for total group quarters
        # For the increment year (note that 2010-2012 uses 2013 data)
        # From the vintage associated with the chosen launch year
        if yr in [2010, 2011, 2012]:
            scale_gq_pct = (
                dof_estimates[
                    (dof_estimates["vintage"] == 2013) & (dof_estimates["year"] == yr)
                ]["pop"].iloc[0]
                / pums_df["pop_gq"].sum()
            )
        else:
            scale_gq_pct = (
                dof_estimates[
                    (dof_estimates["vintage"] == launch_yr)
                    & (dof_estimates["year"] == yr)
                ]["pop"].iloc[0]
                / pums_df["pop_gq"].sum()
            )

        pums_df["pop_gq"] = pums_df["pop_gq"] * scale_gq_pct

        # Distribute excess group quarters population from categories where
        # The group quarters population exceeds the total population
        # To categories where it is less than the total population using the
        # Distribution of group quarters population within categories where the
        # Group quarters population is less than the total population
        pums_df["pop_gq"] = distribute_excess(df=pums_df, subset="pop_gq", total="pop")

        # Calculate the over 70 Group Quarters Formation Rate by Sex
        rates_70plus_gq = (
            pums_df[pums_df["age"] > 70]
            .groupby(["sex"])[["pop_gq", "pop"]]
            .sum()
            .reset_index()
            .assign(rate_gq=lambda x: x["pop_gq"] / x["pop"])[["sex", "rate_gq"]]
        )

        # Calculate the over 70 Group Quarters Formation Rate by Race and Sex
        rates_70plus_hh_head = (
            pums_df[pums_df["age"] > 70]
            .groupby(["race", "sex"])[["pop_hh_head", "pop_hh"]]
            .sum()
            .reset_index()
            .assign(rate_hh=lambda x: x["pop_hh_head"] / x["pop_hh"])[
                ["race", "sex", "rate_hh"]
            ]
        )

        # For age categories over 70, assign all over 70 Formation rates
        # To all race, sex, and single year of age categories
        rates_70plus = (
            pums_df[pums_df["age"] > 70]
            .merge(right=rates_70plus_gq, how="left", on="sex")
            .merge(right=rates_70plus_hh_head, how="left", on=["race", "sex"])
            .fillna(0)[["race", "sex", "age", "rate_gq", "rate_hh"]]
        )

        # Calculate the <=70 Group Quarters Formation Rate
        rates_70under = (
            pums_df[pums_df["age"] <= 70]
            .assign(rate_gq=lambda x: x["pop_gq"] / x["pop"])
            .assign(rate_hh=lambda x: x["pop_hh_head"] / x["pop_hh"])
            .fillna(0)[["race", "sex", "age", "rate_gq", "rate_hh"]]
        )

        # Return Formation Rates
        return pd.concat([rates_70under, rates_70plus], ignore_index=True)

    # Formation rates are not calculated after the launch year
    else:
        raise ValueError("Formation rates not calculated past launch year")
