"""Methods for calculating household/population datasets."""

import logging

import numpy as np
import pandas as pd

import python.utils as utils

generator = np.random.default_rng(utils.RANDOM_SEED)
logger = logging.getLogger(__name__)


def calculate_population(
    population: pd.DataFrame,
    rates: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Calculate the group quarters, households, and household characteristics
    by single year of age, sex, and race/ethnicity.

    Takes the population and applies the group quarters formation rates to the
    population, excluding "Group Quarters - Military" and "Group Quarters -
    Institutional Correctional Facilities". Then applies the household
    formation rate to the remaining household population. Finally, applies the
    household characteristics rates to the formed households.

    All values are integerized to ensure whole number counts respecting
    logical consistency and regional totals.

    Args:
        population (pd.DataFrame): Population by single year of age, sex, and
            race/ethnicity within type
        rates (dict): Dictionary containing formation rates and household
            characteristics rates by single year of age, sex, and race/ethnicity

    Returns:
        pd.DataFrame: Population by single year of age, sex, and race/ethnicity
            within type along with formed households and their characteristics
    """
    result = (
        # Merge the population with the formation rates
        # It is assumed that the pop, gq_mil, and gq_prison fields are integer values
        population[["age", "sex", "ethnicity", "pop", "gq_mil", "gq_prison"]]
        .merge(rates["formation_gq_hh"], on=["age", "sex", "ethnicity"])
        .assign(
            # Apply Group Quarters Formation rates to the population
            # Excluding the "Group Quarters - Military" and "Group Quarters -
            # Institutional Correctional Facilities" populations
            gq_college=lambda x: x["rate_gq_college"]
            * (x["pop"] - x["gq_mil"] - x["gq_prison"]),
            gq_other=lambda x: x["rate_gq_other"]
            * (x["pop"] - x["gq_mil"] - x["gq_prison"]),
        )
    )

    # Integerize formed group quarters populations preserving integerized sum
    result["gq_college"] = utils.integerize_1d(
        result["gq_college"],
        control=round(result["gq_college"].sum()),
        methodology="weighted_random",
        generator=generator,
    )
    result["gq_other"] = utils.integerize_1d(
        result["gq_other"],
        control=int(round(result["gq_other"].sum())),
        methodology="weighted_random",
        generator=generator,
    )

    # Next, make sure the integerized formed group quarters populations
    # Do not exceed the total population row-wise, excluding the "Group
    # Quarters - Military" and "Group Quarters - Institutional Correctional
    #  Facilities" populations
    # Adjust the "Group Quarters - Other" population if it does
    result["pop_remainder"] = (
        result["pop"] - result["gq_mil"] - result["gq_prison"] - result["gq_college"]
    ).astype(int)

    result["gq_other"] = utils.reallocate_integers(
        df=result, subset="gq_other", total="pop_remainder"
    )

    # Calculate the household population as the remainder
    # And apply the household formation rate
    result = result.assign(
        hhp=lambda x: x["pop"]
        - x["gq_mil"]
        - x["gq_prison"]
        - x["gq_college"]
        - x["gq_other"],
        hh=lambda x: x["hhp"] * x["rate_hh"],
    )

    # Integerize formed households preserving integerized sum
    result["hh"] = utils.integerize_1d(
        result["hh"],
        control=round(result["hh"].sum()),
        methodology="weighted_random",
        generator=generator,
    )

    # Merge the population with Household Characteristics rates
    result = (
        result.merge(rates["hh_characteristics"], on=["age", "sex", "ethnicity"])
        # Apply Household Characteristics rates to the formed households
        .assign(
            hh_size1=lambda x: x["hh"] * x["rate_hh_size1"],
            hh_size2=lambda x: x["hh"] * x["rate_hh_size2"],
            hh_size3=lambda x: x["hh"] * x["rate_hh_size3"],
            hh_workers0=lambda x: x["hh"] * x["rate_hh_workers0"],
            hh_workers1=lambda x: x["hh"] * x["rate_hh_workers1"],
            hh_workers2=lambda x: x["hh"] * x["rate_hh_workers2"],
            hh_workers3=lambda x: x["hh"] * x["rate_hh_workers3"],
            hh_head_lf=lambda x: x["hh"] * x["rate_hh_head_lf"],
            hh_children=lambda x: x["hh"] * x["rate_hh_children"],
            hh_seniors=lambda x: x["hh"] * x["rate_hh_seniors"],
        )
    )

    # Integerize the household characteristics preserving their integerized sum(s)
    for col in [
        "hh_size1",
        "hh_size2",
        "hh_size3",
        "hh_workers0",
        "hh_workers1",
        "hh_workers2",
        "hh_workers3",
        "hh_head_lf",
        "hh_children",
        "hh_seniors",
    ]:
        result[col] = utils.integerize_1d(
            data=result[col],
            control=round(result[col].sum()),
            methodology="weighted_random",
            generator=generator,
        ).astype(int)

    # Then adjust the implied counts row-wise to ensure consistency with
    # The total household count within single year of age, sex, and race/ethnicity
    result[["hh_size1", "hh_size2", "hh_size3"]] = utils.reallocate_group_integers(
        df=result, cols=["hh_size1", "hh_size2", "hh_size3"], total="hh"
    )

    result[["hh_workers0", "hh_workers1", "hh_workers2", "hh_workers3"]] = (
        utils.reallocate_group_integers(
            df=result,
            cols=["hh_workers0", "hh_workers1", "hh_workers2", "hh_workers3"],
            total="hh",
        )
    )

    result["hh_head_lf"] = utils.reallocate_integers(
        df=result, subset="hh_head_lf", total="hh"
    )

    result["hh_children"] = utils.reallocate_integers(
        df=result, subset="hh_children", total="hh"
    )

    result["hh_seniors"] = utils.reallocate_integers(
        df=result, subset="hh_seniors", total="hh"
    )

    return result[
        [
            "age",
            "sex",
            "ethnicity",
            "pop",
            "gq_mil",
            "gq_prison",
            "gq_college",
            "gq_other",
            "hh",
            "hh_size1",
            "hh_size2",
            "hh_size3",
            "hh_workers0",
            "hh_workers1",
            "hh_workers2",
            "hh_workers3",
            "hh_head_lf",
            "hh_children",
            "hh_seniors",
        ]
    ]
