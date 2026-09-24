"""Methods to increment through the annual cycle."""

import numpy as np
import pandas as pd

import python.utils as utils

generator = np.random.default_rng(utils.RANDOM_SEED)


def calculate_births(population: pd.DataFrame, rate: pd.DataFrame) -> pd.DataFrame:
    """Calculate births by single year of age, sex, and race/ethnicity.

    Birth rates are applied to the total survived population excluding "Group
    Quarters - Military" and "Group Quarters - Insitutional Correctional
    Facilities" populations. Note that the survived population is assigned
    birth rates for the next single year of age increment as the population
    ages through the annual cycle.

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
        population[["age", "sex", "ethnicity", "pop", "gq_mil", "gq_prison", "deaths"]]
        .assign(
            pop_surv=lambda x: x["pop"] - x["gq_mil"] - x["gq_prison"] - x["deaths"],
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

    # Integerize preserving integerized sum of Births
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
    Quarters - Military" and "Group Quarters - Insitutional Correctional
    Facilities" populations.

    Args:
        population (pd.DataFrame): Population by single year of age, sex, and
            race/ethnicity
        rate (pd.DataFrame): Death rates by single year of age, sex, and
            race/ethnicity

    Returns:
        pd.DataFrame: Deaths by single year of age, sex, and race/ethnicity
    """
    # Merge Population with Death Rates
    # Apply Death Rates to the Non-Military/Prison population
    deaths = (
        population[["age", "sex", "ethnicity", "pop", "gq_mil", "gq_prison"]]
        .merge(right=rate, how="left", on=["age", "sex", "ethnicity"])
        .assign(
            pop_eligible=lambda x: (x["pop"] - x["gq_mil"] - x["gq_prison"]).astype(int)
        )
        .assign(deaths=lambda x: x["pop_eligible"] * x["rate_death"])
        .sort_values(by=["age", "sex", "ethnicity"])
        .reset_index(drop=True)
    )

    # Integerize preserving integerized sum of Deaths
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
    Quarters - Military" and "Group Quarters - Insitutional Correctional
    Facilities" populations. Note that the survived population is assigned
    migration rates for the next single year of age increment as the
    population ages through the annual cycle.

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
        population[["age", "sex", "ethnicity", "pop", "gq_mil", "gq_prison", "deaths"]]
        .assign(
            pop_surv=lambda x: (
                x["pop"] - x["gq_mil"] - x["gq_prison"] - x["deaths"]
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

    # Integerize preserving integerized sums of Ins/Outs
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
    population: pd.DataFrame,
    rates: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Calculate components of change and create input population for next
    increment.

    Args:
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
    # Deaths are calculated first as Births and Migration depend on the
    # survived population

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

    # Calculate the newborn population for the next increment
    newborns = create_newborns(population=population)

    # Create the incremented population total population and age +1 year
    incremented_population = (
        population.assign(
            pop=lambda x: x["pop"] - x["deaths"] + x["ins"] - x["outs"],
            age=lambda x: np.clip(a=(x["age"] + 1), a_min=None, a_max=99),
        )
        .groupby(["age", "sex", "ethnicity"])
        .sum()
        .reset_index()
    )

    # Shift the "Group Quarters - Military" and "Group Quarters - Insitutional
    # Correctional Facilities" populations back in age increment as both are
    # held constant in the forecast
    incremented_population = incremented_population.sort_values(
        by=["age", "sex", "ethnicity"]
    ).reset_index()

    incremented_population["gq_mil"] = incremented_population["gq_mil"].shift(
        periods=-1, fill_value=0
    )

    incremented_population["gq_prison"] = incremented_population["gq_prison"].shift(
        periods=-1, fill_value=0
    )

    # Ensure the "Group Quarters - Military" and "Group Quarters - Insitutional
    # Correctional Facilities" populations are not greater than the total
    # population in each single year of age, sex, and ethnicity group

    # Check Military first is not greater than total population
    incremented_population["gq_mil"] = utils.reallocate_integers(
        df=incremented_population, subset="gq_mil", total="pop"
    )

    # Then check Prison population is not greater than the total population
    # Subtracting the Military population
    incremented_population["pop_no_mil"] = (
        incremented_population["pop"] - incremented_population["gq_mil"]
    ).astype(int)
    incremented_population["gq_prison"] = utils.reallocate_integers(
        df=incremented_population, subset="gq_prison", total="pop_no_mil"
    )
    # Drop the temporary column used for reallocation
    incremented_population = incremented_population.drop(columns=["pop_no_mil"])

    # Add the newborns into the dataset
    incremented_population = pd.concat(
        [newborns.assign(gq_mil=0, gq_prison=0), incremented_population]
    )

    # Return the Components of Change and the incremented Population
    return {
        "components": population[
            ["age", "sex", "ethnicity", "births", "deaths", "ins", "outs"]
        ],
        "population": incremented_population[
            ["age", "sex", "ethnicity", "pop", "gq_mil", "gq_prison"]
        ],
    }
