"""This module contains utility functions used in report generation."""

import os
import sys

import pandas as pd
import plotly.express as px
import sqlalchemy as sql

from sqlalchemy.engine import Engine
from sqlalchemy import text
from typing import List, Union, Optional
from plotly.graph_objects import Figure

# Add the parent directory to sys.path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
)
from utils import SQL_ENGINE

# Define mapping of 5-year age groups
MAP_5Y_AGE_GROUPS = {
    "Under 5": {"low": 0, "high": 4},
    "5 to 9": {"low": 5, "high": 9},
    "10 to 14": {"low": 10, "high": 14},
    "15 to 19": {"low": 15, "high": 19},
    "20 to 24": {"low": 20, "high": 24},
    "25 to 29": {"low": 25, "high": 29},
    "30 to 34": {"low": 30, "high": 34},
    "35 to 39": {"low": 35, "high": 39},
    "40 to 44": {"low": 40, "high": 44},
    "45 to 49": {"low": 45, "high": 49},
    "50 to 54": {"low": 50, "high": 54},
    "55 to 59": {"low": 55, "high": 59},
    "60 to 64": {"low": 60, "high": 64},
    "65 to 69": {"low": 65, "high": 69},
    "70 to 74": {"low": 70, "high": 74},
    "75 to 79": {"low": 75, "high": 79},
    "80 to 84": {"low": 80, "high": 84},
    "85+": {"low": 85, "high": 120},
}


def age_5y(age: float) -> str:
    """Convert age to 5-year age groups."""
    for age_group, bounds in MAP_5Y_AGE_GROUPS.items():
        if bounds["low"] <= age <= bounds["high"]:
            return age_group


def hh_metrics(category: str) -> str:
    """Map household categories to descriptive metric names."""
    if category == "Total Households":
        return "Sum of Households"
    elif category == "Households with Head in Labor Force":
        return "Pct of Total - Labor Force"
    elif category == "Households with Children":
        return "Pct of Total - Children"
    elif category == "Households with Seniors":
        return "Pct of Total - Seniors"
    elif category in [
        "Households with 1 Person",
        "Households with 2 Persons",
        "Households with 3+ Persons",
    ]:
        return "Pct of Total - Size"
    elif category in [
        "Households with 0 Workers",
        "Households with 1 Worker",
        "Households with 2 Workers",
        "Households with 3+ Workers",
    ]:
        return "Pct of Total - Workers"
    elif category == "Persons per Household":
        return "Mean Household Size"
    else:
        ValueError(f"Unknown household category: {category}")


def life_expectancy(q_x: List[float], age: int) -> int:
    """Calculate conditional life expectancy for a given age.

    This function uses the mortality probabilities (q_x) to calculate the
    conditional life expectancy at a specific age. The calculation is based on
    methodology from the United States Social Security Administration described
    here: https://www.ssa.gov/oact/NOTES/as116/as116_IV.html

    Args:
        q_x (List[float]): Single year of age mortality probabilities.
        age (int): Age x to calculate conditional life expectancy for.

    Returns: Conditional life expectancy at age x
    """
    l_x = [100000]  # initial population
    L_x = []  # person years lived
    for i in range(0, len(q_x)):
        # Calculate survivors for the next age
        l_x.append(l_x[i] * (1 - q_x[i]))

        if i == 0:
            continue
        else:
            # Calculate person years lived from age x to x+1
            # Assume deaths occur uniformly over the age interval
            L_x.append(l_x[i] + 0.5 * l_x[i - 1] * q_x[i - 1])

    # Calculate conditional life expectancy at age x
    return age + sum(L_x[age:]) / l_x[age]


def get_data(data_selector: str, run_id: int | None = None) -> dict:
    datasets = {
        "population": {"fp": "output/population.csv", "qry": "report/population.sql"},
        "components": {"fp": "output/components.csv", "qry": "report/components.sql"},
        "rates": {"fp": "output/rates.csv", "qry": "report/rates.sql"},
    }

    result = {}
    for dataset, locations in datasets.items():
        if data_selector == "CSV":
            fp = locations["fp"]
            if fp is not None:
                try:
                    df = pd.read_csv(fp)
                    result[dataset] = {True: df}
                except:
                    result[dataset] = {False: f"Failed to read CSV: {fp}"}
            else:
                result[dataset] = {False: f"No CSV exists"}
        elif data_selector == "SQL Database":
            if run_id is None:
                raise ValueError("Parameter: @run_id must be set to access database")
            else:
                try:
                    with SQL_ENGINE.connect() as connection:
                        with open(locations["qry"], "r") as query:
                            df = pd.read_sql_query(
                                sql.text(query.read().format(run_id=run_id)),
                                connection,
                            )
                            result[dataset] = {True: df}
                # if there is an error return a dictionary of {False: Message}
                except Exception as e:
                    result[dataset] = {
                        False: f"Failed to query SQL Database for '{dataset}: {e}"
                    }
    return result


# Function to check table existence
def get_metadata() -> dict:
    try:
        with SQL_ENGINE.connect() as connection:
            with open("report/metadata.sql", "r") as query:
                df = pd.read_sql_query(
                    sql.text(query.read()),
                    connection,
                )
                return {True: df}
    # if there is an error return a dictionary of {False: Message}
    except Exception as e:
        return {False: f"Failed to query SQL Database: {e}"}
