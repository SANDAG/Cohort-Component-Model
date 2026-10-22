"""Methods to increment through the annual cycle."""

from unittest import result

import numpy as np
import pandas as pd

import python.utils as utils

generator = np.random.default_rng(utils.RANDOM_SEED)


def calculate_births(population: pd.DataFrame, rate: pd.DataFrame) -> pd.DataFrame:
    """Calculate births by single year of age, sex, and race/ethnicity.

    Birth rates are applied to the total survived population excluding "Group
    Quarters - College", "Group Quarters - Military" and "Group Quarters -
    Institutional Correctional Facilities" populations. Note that the survived
    population is assigned birth rates for the next single year of age
    increment as the population ages through the annual cycle.

    Args:
        population (pd.DataFrame): Population data broken down by single year
            of age, sex, and race/ethnicity with calculated deaths
        rate (pd.DataFrame): Birth rates by single year of age, sex, and
            race/ethnicity

    Returns:
        pd.DataFrame: Births by single year of age, sex, and race/ethnicity
    """
    # Merge population with Birth Rates
    # Apply Birth Rates to the Survived Population
    # Note the Population Ages +1 before applying Birth Rates
    births = (
        population[
            [
                "age",
                "sex",
                "ethnicity",
                "pop",
                "gq_college",
                "gq_mil",
                "gq_prison",
                "deaths",
            ]
        ]
        .assign(
            pop_surv=lambda x: x["pop"]
            - x["gq_college"]
            - x["gq_mil"]
            - x["gq_prison"]
            - x["deaths"],
            age_surv=lambda x: np.clip(a=(x["age"] + 1), a_min=None, a_max=99),
        )
        .groupby(["age", "sex", "ethnicity", "age_surv"])
        .sum()
        .reset_index()
        .merge(
            right=rate,
            how="left",
            left_on=["age_surv", "sex", "ethnicity"],
            right_on=["age", "sex", "ethnicity"],
            suffixes=["", "_y"],
        )
        .assign(births=lambda x: round(x["pop_surv"] * x["rate_birth"]))
        .fillna(0)
        .sort_values(by=["age", "sex", "ethnicity"])
        .reset_index(drop=True)
    )

    # Integerize preserving rounded sum of Births
    births["births"] = utils.integerize_1d(
        data=births["births"],
        control=round(births["births"].sum()),
        generator=generator,
        methodology="weighted_random",
    )

    return births[["age", "sex", "ethnicity", "births"]]


def calculate_deaths(population: pd.DataFrame, rate: pd.DataFrame) -> pd.DataFrame:
    """Calculate deaths by single year of age, sex, and race/ethnicity.

    Death rates are applied to the total population excluding "Group
    Quarters - College", "Group Quarters - Military", and "Group Quarters -
    Institutional Correctional Facilities" populations.

    Args:
        population (pd.DataFrame): Population by single year of age, sex, and
            race/ethnicity
        rate (pd.DataFrame): Death rates by single year of age, sex, and
            race/ethnicity

    Returns:
        pd.DataFrame: Deaths by single year of age, sex, and race/ethnicity
    """
    # Merge Population with Death Rates
    # Apply Death Rates to the Non-College/Military/Prison population
    deaths = (
        population[
            ["age", "sex", "ethnicity", "pop", "gq_college", "gq_mil", "gq_prison"]
        ]
        .merge(right=rate, how="left", on=["age", "sex", "ethnicity"])
        .assign(
            pop_eligible=lambda x: (
                x["pop"] - x["gq_college"] - x["gq_mil"] - x["gq_prison"]
            ).astype(int)
        )
        .assign(deaths=lambda x: x["pop_eligible"] * x["rate_death"])
        .sort_values(by=["age", "sex", "ethnicity"])
        .reset_index(drop=True)
    )

    # Integerize preserving rounded sum of Deaths
    deaths["deaths"] = utils.integerize_1d(
        data=deaths["deaths"],
        control=round(deaths["deaths"].sum()),
        generator=generator,
        methodology="weighted_random",
    )

    # Ensure Deaths <= Non-Military/Prison Population after Integerization
    deaths["deaths"] = utils.reallocate_integers(
        df=deaths, subset="deaths", total="pop_eligible"
    )

    return deaths[["age", "sex", "ethnicity", "deaths"]]


def calculate_migration(population: pd.DataFrame, rate: pd.DataFrame) -> pd.DataFrame:
    """Calculate migration by single year of age, sex, and race/ethnicity.

    Migration rates are applied to the survived population excluding "Group
    Quarters - College", "Group Quarters - Military", and "Group Quarters -
    Institutional Correctional Facilities" populations. Note that the survived
    population is assigned migration rates for the next single year of age
    increment as the population ages through the annual cycle.

    Args:
        population (pd.DataFrame): Population by single year of age, sex, and
            race/ethnicity with calculated deaths
        rate (pd.DataFrame): Migration rates by single year of age, sex, and
            race/ethnicity

    Returns:
        pd.DataFrame: In/Out migration by single year of age, sex, and
            race/ethnicity
    """
    # Merge population with Migration Rates
    # Apply Migration Rates to the Survived Population
    # Note the Population Ages +1 before applying Migration Rates
    migrants = (
        population[
            [
                "age",
                "sex",
                "ethnicity",
                "pop",
                "gq_college",
                "gq_mil",
                "gq_prison",
                "deaths",
            ]
        ]
        .assign(
            pop_surv=lambda x: (
                x["pop"] - x["gq_college"] - x["gq_mil"] - x["gq_prison"] - x["deaths"]
            ).astype(int),
            age_surv=lambda x: np.clip(a=(x["age"] + 1), a_min=None, a_max=99),
        )
        .groupby(["age", "sex", "ethnicity", "age_surv"])
        .sum()
        .reset_index()
        .merge(
            right=rate,
            how="left",
            left_on=["age_surv", "sex", "ethnicity"],
            right_on=["age", "sex", "ethnicity"],
            suffixes=["", "_y"],
        )
        .assign(ins=lambda x: x["pop_surv"] * x["rate_in"])
        .assign(outs=lambda x: x["pop_surv"] * x["rate_out"])
        .sort_values(by=["age", "sex", "ethnicity"])
        .reset_index(drop=True)
    )

    # Integerize preserving rounded sums of Ins/Outs
    # TODO: Consider controlling to migration controls here if provided for almost perfect match
    migrants["ins"] = utils.integerize_1d(
        data=migrants["ins"],
        control=round(migrants["ins"].sum()),
        generator=generator,
        methodology="weighted_random",
    )
    migrants["outs"] = utils.integerize_1d(
        data=migrants["outs"],
        control=round(migrants["outs"].sum()),
        generator=generator,
        methodology="weighted_random",
    )

    # Ensure Outs <= Survived Population after Integerization
    migrants["outs"] = utils.reallocate_integers(
        df=migrants, subset="outs", total="pop_surv"
    )

    return migrants[["age", "sex", "ethnicity", "ins", "outs"]]


def create_newborns(population: pd.DataFrame) -> pd.DataFrame:
    """Create newborn population by sex and race/ethnicity (all are age 0).

    Args:
        population (pd.DataFrame): Population by single year of age, sex, and
            race/ethnicity with calculated births

    Returns:
        pd.DataFrame: Newborn population by sex and race/ethnicity (all are age 0)
    """
    newborns = (
        population[["ethnicity", "births"]]
        .groupby("ethnicity")
        .sum()
        .reset_index()
        .merge(
            population[population["age"] == 0][["age", "sex", "ethnicity"]],
            how="right",
            on="ethnicity",
        )
        .fillna(0)
        .sort_values(by=["age", "sex", "ethnicity"])
        .reset_index(drop=True)
    )

    # Assign newborn population to sex using percentage of male newborns
    newborns["pop"] = np.where(
        newborns["sex"] == "Male",
        newborns["births"] * utils.MALE_PCT,
        newborns["births"] * (1 - utils.MALE_PCT),
    )

    # Integerize the newborn population preserving integerized sum
    newborns["pop"] = utils.integerize_1d(
        data=newborns["pop"],
        control=round(newborns["pop"].sum()),
        generator=generator,
        methodology="weighted_random",
    )

    return newborns[["age", "sex", "ethnicity", "pop"]]


def increment_population(
    year: int,
    population: pd.DataFrame,
    rates: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Calculate components of change and create input population for next
    increment.

    Args:
        year (int): Increment year
        population (pd.DataFrame): Population by single year of age, sex, and
            race/ethnicity
        rates (dict): Dictionary containing birth, death, and migration rates
            by single year of age, sex, and race/ethnicity

    Returns:
        dict[str, pd.DataFrame]: Dictionary with two DataFrame elements. The
            first containing the components of change for the current
            population and the second containing the population for the next
            increment
    """
    # Calculate Components of Change; Births, Deaths, and Migration
    # Deaths are calculated first as Births and Migration depend on the survived population
    # All calculations remove constant group quarters populations

    # Calculate Deaths
    population = population.merge(
        right=calculate_deaths(population=population, rate=rates["deaths"]),
        how="left",
        on=["age", "sex", "ethnicity"],
    )

    # Calculate Births
    population = population.merge(
        right=calculate_births(population=population, rate=rates["births"]),
        how="left",
        on=["age", "sex", "ethnicity"],
    )

    # Calculate In/Out Migrants
    population = population.merge(
        right=calculate_migration(population=population, rate=rates["migration"]),
        how="left",
        on=["age", "sex", "ethnicity"],
    )

    # Create the incremented population and age +1 year
    # Note this excludes the constant group quarters populations
    incremented_population = (
        population.assign(
            non_constant_gq_pop=lambda x: x["pop"]
            - x["gq_mil"]
            - x["gq_prison"]
            - x["gq_college"]
            - x["deaths"]
            - x["ins"]
            + x["outs"],
            age=lambda x: np.clip(a=(x["age"] + 1), a_min=None, a_max=99),
        )
        .groupby(["age", "sex", "ethnicity"])["non_constant_gq_pop"]
        .sum()
        .reset_index()
    )

    # Get the constant group quarters populations
    gq_population = population[
        ["age", "sex", "ethnicity", "gq_mil", "gq_prison", "gq_college"]
    ]

    # Check if the group quarters controls DataFrame is optionally provided
    # If so, get and apply controls for the next increment year
    if utils.GQ_CONTROLS is not None:
        controls = utils.GQ_CONTROLS.loc[utils.GQ_CONTROLS["year"] == (year + 1)]
        # Apply the group quarters controls
        for gq_type in ["gq_mil", "gq_prison", "gq_college"]:
            gq_adj = gq_population[["age", "sex", "ethnicity", gq_type]]
            gq_adj[gq_type + "_adj"] = (
                utils.integerize_1d(
                    gq_population[gq_type],
                    control=controls[gq_type].sum(),
                    methodology="weighted_random",
                    generator=generator,
                )
                - gq_adj[gq_type]
            )

            # Store adjustments made in the components of change
            population = population.merge(
                right=gq_adj[["age", "sex", "ethnicity", gq_type + "_adj"]],
                on=["age", "sex", "ethnicity"],
            )

            # Update the group quarters population
            gq_population = gq_population.merge(
                right=gq_adj[["age", "sex", "ethnicity", gq_type + "_adj"]],
                on=["age", "sex", "ethnicity"],
            )

            gq_population[gq_type] = (
                gq_population[gq_type + "_adj"] + gq_population[gq_type]
            )

            gq_population.drop(columns=[gq_type + "_adj"], inplace=True)
    else:
        # No adjustments made to constant group quarters populations
        population[["gq_mil_adj", "gq_prison_adj", "gq_college_adj"]] = 0

    # Add the constant group quarters populations back to the incremented population
    # And recalculate the total population field
    incremented_population = (
        incremented_population.merge(
            right=gq_population, how="left", on=["age", "sex", "ethnicity"]
        )
        .assign(
            pop=lambda x: x["non_constant_gq_pop"]
            + x["gq_mil"]
            + x["gq_prison"]
            + x["gq_college"]
        )
        .drop(columns=["non_constant_gq_pop"])
    )

    # Calculate the newborn population for the next increment
    newborns = create_newborns(population=population)
    incremented_population = pd.concat(
        [newborns.assign(gq_college=0, gq_mil=0, gq_prison=0), incremented_population]
    )

    # Return the Components of Change and the incremented Population
    return {
        "components": population[
            [
                "age",
                "sex",
                "ethnicity",
                "births",
                "deaths",
                "ins",
                "outs",
                "gq_mil_adj",
                "gq_prison_adj",
                "gq_college_adj",
            ]
        ],
        "population": incremented_population[
            ["age", "sex", "ethnicity", "pop", "gq_mil", "gq_prison", "gq_college"]
        ],
    }
