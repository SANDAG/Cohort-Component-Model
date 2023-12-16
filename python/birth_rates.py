"""Get birth rates by race and single year of age."""
# TODO: (7-feature) Add function to allow for input % adjustments to birth rates.
# TODO: (5-feature) Potentially implement smoothing function within race categories.

import pandas as pd
import numpy as np


def get_birth_rates(
    yr: int, launch_yr: int, pop_df: pd.DataFrame, rates_map: dict
) -> pd.DataFrame:
    """Create birth rates broken down by race and single year of age.

    Birth rates are calculated using CDC WONDER Natality births for 5-year age
    groups ranging from ages 15 to 44 setting "Suppressed" raw births
    (values < 10) to values of 4.5 and dividing the raw births by three, as
    3-years of births are always from CDC WONDER. Births are merged with the
    base/launch year population (aggregated to 5-year age groups), inflated to
    account for the % of births attributed to "unknown" race/ethnicity groups,
    and then QC'ed to ensure no race or 5-year age group contains 0 births or
    births greater than the total population within the category.

    Note that no inflation factor is made to account for births assigned to
    under 15 or 45+ age groups that are excluded.

    Args:
        yr: Increment year
        launch_yr: Launch year
        pop_df (pd.DataFrame): Population data broken down by race, sex, and
            single year of age
        rates_map (dict): loaded JSON configuration birth/death rate map

    Returns:
        pd.DataFrame: Birth rates broken down by race and single year of age
    """
    # Birth rates calculated from base year up to the launch year
    if yr <= launch_yr:
        if str(yr) not in rates_map["births"].keys():
            raise ValueError("No birth rate mapping for: " + str(yr))

        births = pd.DataFrame()
        # For each WONDER births file path in the chosen base year
        for k, v in rates_map["births"][str(yr)].items():
            fp = "data/births/" + str(yr) + "/" + v

            # Get WONDER births data
            wonder_births = (
                pd.read_csv(
                    fp,
                    delimiter="\t",
                    usecols=["Age of Mother 9 Code", "Births"],
                    dtype={"Age of Mother 9 Code": str, "Births": str},
                )
                .rename(columns={"Age of Mother 9 Code": "age_5yr", "Births": "births"})
                .dropna(subset=["age_5yr"])
                .assign(race=k)
                .replace({"births": {"Suppressed": "4.5"}})
                .astype({"births": "float"})
                .assign(births=lambda x: x["births"] / 3)
            )

            births = pd.concat([births, wonder_births])

        # Create lower/upper boundaries for the 5-year age groups
        age_bounds = {
            "15-19": {"lower": 15, "upper": 19},
            "20-24": {"lower": 20, "upper": 24},
            "25-29": {"lower": 25, "upper": 29},
            "30-34": {"lower": 30, "upper": 34},
            "35-39": {"lower": 35, "upper": 39},
            "40-44": {"lower": 40, "upper": 44},
        }

        for k, v in age_bounds.items():
            births.loc[births["age_5yr"] == k, "age_lower"] = v["lower"]
            births.loc[births["age_5yr"] == k, "age_upper"] = v["upper"]

        # Merge births with population
        merged_births = (
            births.merge(
                right=pop_df.loc[
                    (pop_df["sex"] == "F") & (pop_df["age"].between(15, 44))
                ][["race", "age", "pop"]],
                on="race",
            )
            .query("age >= age_lower & age <= age_upper")
            .groupby(["race", "age_5yr", "age_lower", "age_upper"])
            .agg({"births": "max", "pop": "sum"})
            .reset_index()
        )

        # Inflate births by the % of "unknown" race/ethnicity births
        # Note: this is not done for births outside of the eligible age groups
        inflation_factor = 1 + (
            births.loc[births["race"].isin(["Missing Race", "Missing Ethnicity"])][
                "births"
            ].sum()
            / merged_births["births"].sum()
        )

        merged_births["births"] = merged_births["births"] * inflation_factor

        # Do not allow 0 births
        merged_births["births"] = np.where(
            merged_births["births"] == 0, 1, merged_births["births"]
        )

        # Ensure values in births field do not exceed population
        merged_births["births"] = np.where(
            merged_births["births"] > merged_births["pop"],
            merged_births["pop"],
            merged_births["births"],
        )

        # Calculate birth rates by race, sex, and single year of age
        rates = (
            merged_births.assign(rate=lambda x: x["births"] / x["pop"])[
                ["race", "age_lower", "age_upper", "rate"]
            ]
            .merge(
                right=pop_df.loc[
                    (pop_df["sex"] == "F") & (pop_df["age"].between(15, 44))
                ],
                on="race",
            )
            .query("age >= age_lower & age <= age_upper")[
                ["race", "sex", "age", "rate"]
            ]
        )

        # If increment year is 2010-2017
        # NHPI and More than one race birth rates do not exist, set to average
        # NHPI births are folded into Asian (overstating Asian birth rates)
        # More than one race folded into all categories (overstating all others)
        if 2010 <= yr <= 2017:
            avg_rates = (
                birth_rates.groupby(["sex", "age"]).agg({"rate": "mean"}).reset_index()
            )

            avg_rates["race"] = "More than one race"
            birth_rates = pd.concat([birth_rates, avg_rates])

            avg_rates["race"] = "Native Hawaiian and Other Pacific Islander alone"
            birth_rates = pd.concat([birth_rates, avg_rates])
        else:
            pass

        return rates

    # Birth rates are not calcualted after the launch year
    # TODO: (7-feature) Adjustments to birth rates would be made post-launch year through horizon
    else:
        raise ValueError("Birth rates not calculated past launch year")
