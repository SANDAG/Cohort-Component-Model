"""Get household characteristics rates by race, sex, and single year of age."""
# TODO: (5-feature) Potentially implement smoothing function within race and sex categories.

import numpy as np
import pandas as pd
from python.utilities import adjust_sum, distribute_excess
import warnings


def get_hh_characteristic_rates(
    yr: int,
    launch_yr: int,
    acs5yr_pums_persons: pd.DataFrame,
    sandag_estimates: dict,
) -> pd.DataFrame:
    """Generate household characteristics rates broken down by race, sex, and
    single year of age.

    Household characteristic rates are calculated using the 5-year ACS PUMS
    persons. Prior to calculation, the total number of households and all
    household-related variables are scaled to match SANDAG estimates. For each
    characteristic, if there exists a SANDAG estimate, the total number of
    households within the characteristic category is scaled to match SANDAG
    estimates.

    For race, sex, and single year of age categories with less than twenty
    households, household characteristic rates within race, sex, and more
    aggregate age categories are used.

    Args:
        yr: Increment year
        launch_yr: Launch year
        acs5yr_pums_persons (pd.DataFrame): 5-year ACS PUMS persons
        sandag_estimates (dict): loaded JSON control totals from historical
            SANDAG Estimates programs

    Returns:
        pd.DataFrame: Household characteristics rates broken down by race,
            sex, and single year of age
    """
    if yr <= launch_yr:
        if yr not in acs5yr_pums_persons["year"].unique():
            raise ValueError(str(yr) + ": not in ACS 5-year PUMS")

        # Select the 5-year ACS PUMS data
        pums_df = acs5yr_pums_persons[(acs5yr_pums_persons["year"] == yr)].copy()

        # Get SANDAG Estimates household controls for the increment
        # Year from the vintage associated with the launch year
        controls = sandag_estimates[str(launch_yr)][str(yr)]["households"]

        # Create mapping of household attributes to ACS PUMS columns and SANDAG Estimates
        # Include whether attribute is controlled and whether to create crude rate
        hh_attributes = {
            "hh": {"col": "pop_hh_head", "control": "total", "rate": None},
            "laborforce": {
                "col": "hh_head_lf",
                "control": None,
                "rate": "rate_hh_head_lf",
            },
            "size1": {"col": "size1", "control": "size1", "rate": "rate_size1"},
            "size2": {"col": "size2", "control": "size2", "rate": "rate_size2"},
            "size3": {"col": "size3", "control": "size3", "rate": "rate_size3"},
            "child1": {"col": "child1", "control": "child1", "rate": "rate_child1"},
            "senior1": {"col": "senior1", "control": None, "rate": "rate_senior1"},
            "workers0": {
                "col": "workers0",
                "control": "workers0",
                "rate": "rate_workers0",
            },
            "workers1": {
                "col": "workers1",
                "control": "workers1",
                "rate": "rate_workers1",
            },
            "workers2": {
                "col": "workers2",
                "control": "workers2",
                "rate": "rate_workers2",
            },
            "workers3": {
                "col": "workers3",
                "control": "workers3",
                "rate": "rate_workers3",
            },
        }

        # Apply total households scaling factor to all household attributes
        control_hh = controls["hh"]
        if control_hh is not None:
            scale_hh_pct = control_hh / pums_df["pop_hh_head"].sum()
            for k, v in hh_attributes.items():
                pums_df[v["col"]] = pums_df[v["col"]] * scale_hh_pct
        else:
            warnings.warn("No household control total provided.", UserWarning)

        # Apply household characteristics scaling factors and calculate crude rates
        # Assumed that control totals are consistent with total households control
        for k, v in hh_attributes.items():
            if k != "hh":
                if v["control"] is not None:
                    control = controls[k]
                    if control is not None:
                        scale_pct = control / pums_df[v["col"]].sum()
                        pums_df[v["col"]] = pums_df[v["col"]] * scale_pct
                        # Distribute excess if any characteristic exceeds total households
                        pums_df[v["col"]] = distribute_excess(
                            df=pums_df, subset=v["col"], total="pop_hh_head"
                        )
                if v["rate"] is not None:
                    pums_df[v["rate"]] = pums_df[v["col"]] / pums_df["pop_hh_head"]

        # Calculate rates within age groups to apply when households are < 20 (excluding 0s)
        age_groups = pd.concat(
            [
                pd.DataFrame(data={"age_group": 1, "age": list(range(0, 16))}),
                pd.DataFrame(data={"age_group": 2, "age": list(range(16, 18))}),
                pd.DataFrame(data={"age_group": 3, "age": list(range(18, 25))}),
                pd.DataFrame(data={"age_group": 4, "age": list(range(25, 35))}),
                pd.DataFrame(data={"age_group": 5, "age": list(range(35, 50))}),
                pd.DataFrame(data={"age_group": 6, "age": list(range(50, 60))}),
                pd.DataFrame(data={"age_group": 7, "age": list(range(60, 71))}),
                # Note maximum age of 110 in defining age groups
                pd.DataFrame(data={"age_group": 8, "age": list(range(71, 111))}),
            ],
            ignore_index=True,
        )

        age_rates = (
            pums_df.merge(right=age_groups, how="left", on="age")
            .groupby(["race", "sex", "age_group"])
            .sum()
        )

        for k, v in hh_attributes.items():
            if k != "hh":
                age_rates[v["rate"] + "_age"] = (
                    age_rates[v["col"]] / age_rates["pop_hh_head"]
                )

        # Merge Age Group Rates into the Rate DataFrame
        pums_df = pums_df.merge(right=age_groups, how="left", on="age").merge(
            right=age_rates, on=["race", "sex", "age_group"], suffixes=["", "_y"]
        )

        # Set Rate to Age Group Rate if households < 20 (excluding 0s)
        for k, v in hh_attributes.items():
            if k != "hh":
                if v["rate"] is not None:
                    pums_df[v["rate"]] = np.where(
                        (pums_df["pop_hh_head"] > 0) & (pums_df["pop_hh_head"] < 20),
                        pums_df[v["rate"] + "_age"],
                        pums_df[v["rate"]],
                    )

        # Ensure rates do not sum > 1 within logical groupings (size and workers)
        groupings = [
            ["rate_size1", "rate_size2", "rate_size3"],
            ["rate_workers0", "rate_workers1", "rate_workers2", "rate_workers3"],
        ]

        for group in groupings:
            pums_df[group] = adjust_sum(df=pums_df, cols=group, sum=1, option="equals")

        # Return crude household characteristics rates
        rates = []
        for k, v in hh_attributes.items():
            if v["rate"] is not None:
                rates.append(v["rate"])

        return pums_df[["race", "sex", "age", *rates]]

    # Household characteristics rates are not calculated after the launch year
    else:
        raise ValueError(
            "Household characteristics rates not calculated past launch year"
        )
