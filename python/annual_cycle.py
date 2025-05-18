"""Methods to increment through the annual cycle."""

# TODO: (10-feature) Add function to allow for control totals at each increment for in/out migration.

from iteround import saferound
import numpy as np
import pandas as pd
from typing import Dict
from python.utils import reallocate_integers


def calculate_births(pop_df: pd.DataFrame, rate: pd.DataFrame) -> pd.DataFrame:
    """Calculate births by race, sex, and single year of age.

    Birth rates are applied to the total survived population (the
    military population plus the survived civilian population). Note that the
    survived civilian population is assigned birth rates for the next single
    year of age increment as the population ages through the annual cycle. The
    military population is note assumed to age as it is held constant.

    Args:
        pop_df (pd.DataFrame): Population data broken down by race, sex, and
            single year of age with the military population broken out from
            the total population and calculated deaths
        rate (pd.DataFrame): Birth rates by race, sex, and single year of age

    Returns:
        pd.DataFrame: Births by race, sex, and single year of age
    """
    # Merge population with Birth Rates
    # Apply Birth Rates to the Survived Population
    # Note the Civilian Population Ages +1 before applying Birth Rates
    df = (
        pop_df[["race", "sex", "age", "pop", "pop_mil", "deaths"]]
        .assign(
            pop_civ_surv=lambda x: x["pop"] - x["pop_mil"] - x["deaths"],
            age_civ_surv=lambda x: np.clip(a=(x["age"] + 1), a_min=None, a_max=110),
            pop_surv=lambda x: x["pop"] - x["deaths"],
        )
        .groupby(["race", "sex", "age", "age_civ_surv"])
        .sum()
        .reset_index()
        .merge(right=rate, how="left", on=["race", "sex", "age"])
        .merge(
            right=rate,
            how="left",
            left_on=["race", "sex", "age_civ_surv"],
            right_on=["race", "sex", "age"],
            suffixes=["", "_civ_surv"],
        )
        .assign(
            births=lambda x: x["pop_mil"] * x["rate_birth"]
            + x["pop_civ_surv"] * x["rate_birth_civ_surv"]
        )
        .fillna(0)
    )

    # Integerize preserving sum of Births
    df["births"] = saferound(df["births"], 0)
    df["births"] = df["births"].astype(int)

    # Ensure Births <= Survived Population after Integerization
    df["births"] = reallocate_integers(df=df, subset="births", total="pop_surv")

    return df[["race", "sex", "age", "births"]]


def calculate_deaths(pop_df: pd.DataFrame, rate: pd.DataFrame) -> pd.DataFrame:
    """Calculate deaths by race, sex, and single year of age.

    Death rates are applied to the non-military civilian population as it is
    assumed the military population remains constant outside of pre-launch
    year controls.

    Args:
        pop_df (pd.DataFrame): Population data broken down by race, sex, and
            single year of age with the military population broken out from
            the total population
        rate (pd.DataFrame): Death rates by race, sex, and single year of age

    Returns:
        pd.DataFrame: Deaths by race, sex, and single year of age
    """
    # Merge Population with Death Rates
    # Apply Death Rates to the Non-Military Population
    df = (
        pop_df[["race", "sex", "age", "pop", "pop_mil"]]
        .merge(right=rate, how="left", on=["race", "sex", "age"])
        .assign(pop_civ=lambda x: x["pop"] - x["pop_mil"])
        .assign(deaths=lambda x: x["pop_civ"] * x["rate_death"])
    )

    # Integerize preserving sum of Deaths
    df["deaths"] = saferound(df["deaths"], 0)
    df["deaths"] = df["deaths"].astype(int)

    # Ensure Deaths <= Non-Military Population after Integerization
    df["deaths"] = reallocate_integers(df=df, subset="deaths", total="pop_civ")

    return df[["race", "sex", "age", "deaths"]]


def calculate_migration(pop_df: pd.DataFrame, rate: pd.DataFrame) -> pd.DataFrame:
    """Calculate migration by race, sex, and single year of age.

    Migration rates are applied to the survived civilian population. Note that
    the survived civilian population is assigned migration rates for the next
    single year of age increment as the population ages through the annual
    cycle.

    Args:
        pop_df (pd.DataFrame): Population data broken down by race, sex, and
            single year of age with the military population broken out from
            the total population and calculated deaths
        rate (pd.DataFrame): Migration rates by race, sex, and single year of
            age

    Returns:
        pd.DataFrame: In/Out Migration by race, sex, and single year of age
    """
    # Merge population with Migration Rates
    # Apply Migration Rates to the Survived Civilian Population
    # Note the Civilian Population Ages +1 before applying Birth Rates
    df = (
        pop_df[["race", "sex", "age", "pop", "pop_mil", "deaths"]]
        .assign(
            pop_civ_surv=lambda x: x["pop"] - x["pop_mil"] - x["deaths"],
            age_civ_surv=lambda x: np.clip(a=(x["age"] + 1), a_min=None, a_max=110),
        )
        .groupby(["race", "sex", "age", "age_civ_surv"])
        .sum()
        .reset_index()
        .merge(
            right=rate,
            how="left",
            left_on=["race", "sex", "age_civ_surv"],
            right_on=["race", "sex", "age"],
            suffixes=["", "_y"],
        )
        .assign(ins=lambda x: x["pop_civ_surv"] * x["rate_in"])
        .assign(outs=lambda x: x["pop_civ_surv"] * x["rate_out"])
    )

    # Integerize preserving sums of Ins/Outs
    df["ins"] = saferound(df["ins"], 0)
    df["ins"] = df["ins"].astype(int)
    df["outs"] = saferound(df["outs"], 0)
    df["outs"] = df["outs"].astype(int)

    # Ensure Outs <= Survived Population after Integerization
    df["outs"] = reallocate_integers(df=df, subset="outs", total="pop_civ_surv")

    return df[["race", "sex", "age", "ins", "outs"]]


def create_newborns(pop_df: pd.DataFrame, male_pct: float) -> pd.DataFrame:
    """Create newborn population by race and sex (all are age 0).

    Args:
        pop_df (pd.DataFrame): Population data broken down by race, sex, and
            single year of age with calculated births
        male_pct (float): Percentage of newborns assign to male sex

    Returns:
        pd.DataFrame: Newborn population by race and sex (all are age 0)
    """
    df = (
        pop_df[["race", "births"]]
        .groupby("race")
        .sum()
        .reset_index()
        .merge(
            pop_df[pop_df["age"] == 0][["race", "sex", "age"]], how="right", on="race"
        )
        .fillna(0)
    )

    df["pop"] = np.where(
        df["sex"] == "M", df["births"] * male_pct, df["births"] * (1 - male_pct)
    )

    df["pop"] = saferound(df["pop"], 0)

    return df[["race", "sex", "age", "pop"]]


def increment_population(
    pop_df: pd.DataFrame, rates: dict
) -> Dict[pd.DataFrame, pd.DataFrame]:
    """Calculate components of change and create input population for next
    increment.

    Args:
        pop_df (pd.DataFrame): Population data broken down by race, sex, and
            single year of age with the military population broken out from
            the total population
        rates (dict): Dictionary containing death, birth, and migration rates
            by race, sex, and single year of age

    Returns:
        Dict[pd.DataFrame, pd.DataFrame]: Dictionary with two DAtaFrame
            elementes. The first containing the components of change for the
            current population. The second containing the input population for
            the next increment.
    """
    # Calculate Components of Change; Deaths, Births, and Migration
    pop_df = pop_df.merge(
        right=calculate_deaths(pop_df, rate=rates["deaths"]),
        how="left",
        on=["race", "sex", "age"],
    )

    pop_df = pop_df.merge(
        right=calculate_births(pop_df=pop_df, rate=rates["births"]),
        how="left",
        on=["race", "sex", "age"],
    )

    pop_df = pop_df.merge(
        right=calculate_migration(pop_df=pop_df, rate=rates["migration"]),
        how="left",
        on=["race", "sex", "age"],
    )

    # Calculate the newborn population for the next increment
    newborns = create_newborns(pop_df=pop_df, male_pct=0.512)

    # Create the incremented population
    # Calculate total population and increment age
    pop_inc = (
        pop_df.assign(
            pop=lambda x: x["pop"] - x["deaths"] + x["ins"] - x["outs"],
            age=lambda x: np.clip(a=(x["age"] + 1), a_min=None, a_max=110),
        )
        .groupby(["race", "sex", "age"])
        .sum()
        .reset_index()
    )

    # Shift the Military Population back in age increment
    # The Military Population is held constant
    # Ensure the Military Population is not greater than the Population
    pop_inc = pop_inc.sort_values(by=["race", "sex", "age"]).reset_index()
    pop_inc["pop_mil"] = pop_inc["pop_mil"].shift(periods=-1, fill_value=0)
    pop_inc["pop_mil"] = reallocate_integers(df=pop_inc, subset="pop_mil", total="pop")

    # Add the newborns into the dataset setting their Military Population to 0
    pop_inc = pd.concat([newborns.assign(pop_mil=0), pop_inc])

    # Return the Components of Change and the incremented Population
    return {
        "components": pop_df[["race", "sex", "age", "deaths", "births", "ins", "outs"]],
        "population": pop_inc[["race", "sex", "age", "pop", "pop_mil"]],
    }
