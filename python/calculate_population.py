"""Methods for calculating household/population datasets."""

import logging
import numpy as np
import pandas as pd

import python.utils as utils

generator = np.random.default_rng(utils.RANDOM_SEED)
logger = logging.getLogger(__name__)


# Create mapping of columns to SANDAG Estimates Controls
# Order matters, the totals (pop, hh) within groups (population, households)
# Must occur prior to any other group members for scaling and integerization
FIELD_MAP = {
    "Population ": {"col": "pop", "control": "pop", "group": "population"},
    "Military": {"col": "pop_mil", "control": None, "group": "population"},
    "Group Quarters": {"col": "gq", "control": "gq", "group": "population"},
    "Household": {"col": "hh", "control": "hh", "group": "households"},
    "HH Head LF": {"col": "hh_head_lf", "control": None, "group": "households"},
    "HH Size 1": {"col": "size1", "control": "size1", "group": "households"},
    "HH Size 2": {"col": "size2", "control": "size2", "group": "households"},
    "HH Size 3+": {"col": "size3", "control": "size3", "group": "households"},
    "HH <18 1+": {"col": "child1", "control": "child1", "group": "households"},
    "HH 65+ 1+": {"col": "senior1", "control": None, "group": "households"},
    "HH Workers 0": {"col": "workers0", "control": "workers0", "group": "households"},
    "HH Workers 1": {"col": "workers1", "control": "workers1", "group": "households"},
    "HH Workers 2": {"col": "workers2", "control": "workers2", "group": "households"},
    "HH Workers 3+": {"col": "workers3", "control": "workers3", "group": "households"},
}


def apply_controls(
    yr: int,
    launch_yr: int,
    pop_df: pd.DataFrame,
    sandag_estimates: dict,
) -> pd.DataFrame:
    """Control the calculated population, group quarters, households, and
    household characteristics totals for each increment from the base year
    up to the launch year.

    Args:
        yr: Increment year
        launch_yr: Launch year
        pop_df (pd.DataFrame): Household/Population data by race, sex, and
            single year of age, output from the calculate_population method
        sandag_estimates (dict): loaded JSON control totals from historical
            SANDAG Estimates programs

    Returns:
        pd.DataFrame: The controlled household/population data
    """
    if yr <= launch_yr:
        # Control column totals to SANDAG Estimates Controls
        control_values = sandag_estimates[str(launch_yr)][str(yr)]
        # For each household/population field
        for k, v in FIELD_MAP.items():
            # If the field is controlled get the control value
            if v["control"] is not None:
                control_value = control_values[v["group"]][v["control"]]
                # If the control value was provided scale the field to match the control
                if control_value is not None:
                    scale_pct = control_value / pop_df[v["col"]].sum()
                    # Pass total households scaling to all related fields regardless if they are controlled or not
                    if v["control"] == "hh":
                        for sub_k, sub_v in FIELD_MAP.items():
                            if sub_v["group"] == "households":
                                pop_df[sub_v["col"]] = round(pop_df[sub_v["col"]] * scale_pct)
                    # Pass total population scaling to all related fields regardless if they are controlled or not
                    elif v["control"] == "pop":
                        for sub_k, sub_v in FIELD_MAP.items():
                            # Do not pass total population scaling to Military
                            if sub_k != "Military":
                                if sub_v["group"] == "population":
                                    pop_df[sub_v["col"]] = round(pop_df[sub_v["col"]] * scale_pct)
                    else:
                        pop_df[v["col"]] = round(pop_df[v["col"]] * scale_pct)
                else:
                    logger.warning("No household control total provided for: " + k)

        # Return controlled population
        return pop_df

    # No controls are applied after the launch year
    else:
        raise ValueError("Controls not applied past launch year")


def calculate_population(
    pop_df: pd.DataFrame,
    rates: dict,
) -> pd.DataFrame:
    """Calculate the group quarters, households, and household characteristics
    by race, sex, and single year of age.

    Takes the population and applies the group quarters formation rate to the
    total population, including the military population. Takes the population
    and applies the household formation rate to the total civilian
    (non-military) population. Finally, applies the household characteristics
    rates to the formed households.

    Args:
        pop_df (pd.DataFrame): Population data broken down by race, sex, and
            single year of age with the military population broken out from
            the total population
        rates (dict): Dictionary containing formation rates and household
            characteristics rates by race, sex, and single year of age

    Returns:
        pd.DataFrame: Population with group quarters, households, and
            household characteristics by race, sex, and single year of age.
    """
    # Apply GQ and HH Rates to get GQ and HHs
    # Then apply HH characteristics to created HHs
    df = (
        pop_df.merge(
            right=rates["formation_gq_hh"],
            how="left",
            on=["race", "sex", "age"],
        )
        .assign(
            gq=lambda x: round(x["pop"] * x["rate_gq"]),
            hh=lambda x: round((x["pop"] - x["pop_mil"]) * x["rate_hh"]),
        )
        .merge(
            right=rates["hh_characteristics"],
            how="left",
            on=["race", "sex", "age"],
        )
        .assign(
            hh_head_lf=lambda x: round(x["hh"] * x["rate_hh_head_lf"]),
            size1=lambda x: round(x["hh"] * x["rate_size1"]),
            size2=lambda x: round(x["hh"] * x["rate_size2"]),
            size3=lambda x: round(x["hh"] * x["rate_size3"]),
            child1=lambda x: round(x["hh"] * x["rate_child1"]),
            senior1=lambda x: round(x["hh"] * x["rate_senior1"]),
            workers0=lambda x: round(x["hh"] * x["rate_workers0"]),
            workers1=lambda x: round(x["hh"] * x["rate_workers1"]),
            workers2=lambda x: round(x["hh"] * x["rate_workers2"]),
            workers3=lambda x: round(x["hh"] * x["rate_workers3"]),
        )
        .fillna(0)
    )

    return df[
        [
            "race",
            "sex",
            "age",
            "pop",
            "pop_mil",
            "gq",
            "hh",
            "hh_head_lf",
            "child1",
            "senior1",
            "size1",
            "size2",
            "size3",
            "workers0",
            "workers1",
            "workers2",
            "workers3",
        ]
    ]


def integerize_population(
    pop_df: pd.DataFrame,
) -> pd.DataFrame:
    """Integerize the calculated population, group quarters, households, and
    household characteristics totals for each increment from the base year up
    to the horizon year.

    Note that after integerization, fields are reallocated, preserving the
    integer data type and sum, such that all constraints are respected.

    Args:
        pop_df (pd.DataFrame): Household/Population data by race, sex, and
            single year of age, output from the calculate_population method

    Returns:
        pd.DataFrame: The integerized calculated population
    """
    for k, v in FIELD_MAP.items():
        # Round fields to integer preserving sum
        if pop_df[v["col"]].dtype.kind != "i":
            pop_df[v["col"]] = utils.integerize_1d(
                data=pop_df[v["col"]], control=None, generator=generator
            )

        # Reallocate integers if values exceed totals
        if v["group"] == "households":
            # For total households the total population is the maximum
            if v["col"] == "hh":
                pop_df[v["col"]] = utils.reallocate_integers(
                    df=pop_df, subset=v["col"], total="pop"
                )
            # For all household related fields the total households is the maximum
            else:
                pop_df[v["col"]] = utils.reallocate_integers(
                    df=pop_df, subset=v["col"], total="hh"
                )
        # For all population related fields the total population is the maximum
        elif v["group"] == "population" and v["col"] != "pop":
            pop_df[v["col"]] = utils.reallocate_integers(
                df=pop_df, subset=v["col"], total="pop"
            )
        else:
            pass

    # Although not identified as related in the field mapping
    # Do not allow GQs + HHs > Total Population
    pop_df["pop_minus_hh"] = pop_df["pop"] - pop_df["hh"]

    pop_df["gq"] = utils.reallocate_integers(
        df=pop_df, subset="gq", total="pop_minus_hh"
    )

    pop_df.drop(labels="pop_minus_hh", axis=1, inplace=True)

    # Adjust groupings of HH fields with complete coverage of total households
    # Such that their summation matches the total households
    hh_field_groups = {
        "HH Size": {"cols": ["size1", "size2", "size3"], "total": "hh"},
        "HH Workers": {
            "cols": ["workers0", "workers1", "workers2", "workers3"],
            "total": "hh",
        },
    }

    for k, v in hh_field_groups.items():
        pop_df[v["cols"]] = utils.reallocate_group_integers(
            df=pop_df, cols=v["cols"], total=v["total"]
        )

    # Return integerized population
    return pop_df
