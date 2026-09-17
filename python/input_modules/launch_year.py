"""Generate launch year population by single year of age, sex, and ethnicity."""

import logging

import numpy as np
import pandas as pd
import sqlalchemy as sql

import python.tests as tests
import python.utils as utils

generator = np.random.default_rng(utils.RANDOM_SEED)
logger = logging.getLogger(__name__)


def run_launch_year() -> pd.DataFrame:
    """Orchestrator function to create the launch year population dataset.

    This module generates the launch year population dataset by population
    type, single year of age, sex, and race/ethnicity from SANDAG's Estimates
    Program and the California Department of Finance (DOF) age/sex/ethnicity
    controls.

    The final dataset should match the provided Estimates Program run values
    for population by type age/sex/ethnicity within the age groups defined by
    the Estimates Program but split out into single year of age using the same
    California DOF age/sex/ethnicity distribution used by SANDAG's Estimates
    Program.

    https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Age-Sex-Ethnicity

    Functionality is split apart for code encapsulation:
        _get_launch_inputs - Get SANDAG Estimates Program population by
            type, age_group, sex, and race/ethnicity and the California DOF
            age/sex/ethnicity distribution mapping age_group to single year of
            age.
        _validate_launch_inputs - Validate inputs from the above function
        _create_launch_outputs - Split SANDAG Estimates Program age_group into
            single year of age and integerize within each age_group
        _validate_launch_outputs - Validate the output from the above function
    """
    launch_inputs = _get_launch_inputs()
    _validate_launch_inputs(launch_inputs)

    launch_outputs = _create_launch_outputs(launch_inputs)
    _validate_launch_outputs(launch_outputs)

    return launch_outputs


def _get_launch_inputs() -> dict[str, pd.DataFrame]:
    """Load input datasets for launch year population generation."""
    # Load California DOF age/sex/ethnicity distribution
    with utils.CCM_ENGINE.connect() as connection:
        # Load California DOF age/sex/ethnicity distribution
        with open(
            utils.SQL_FOLDER / "launch" / "get_ase_distribution.sql", "r"
        ) as file:
            dof_ase = pd.read_sql_query(
                sql.text(file.read()), connection, params={"year": utils.LAUNCH_YEAR}  # type: ignore
            )

    # Load Estimates Program launch year population
    with utils.ESTIMATES_ENGINE.connect() as connection:
        with open(utils.SQL_FOLDER / "launch" / "get_estimates_ase.sql", "r") as file:
            estimates = pd.read_sql_query(
                sql.text(file.read()),
                connection,
                params={"run_id": utils.ESTIMATES_RUN_ID, "year": utils.LAUNCH_YEAR},  # type: ignore
            )

    return {"dof_ase": dof_ase, "estimates": estimates}


def _validate_launch_inputs(launch_inputs: dict[str, pd.DataFrame]) -> None:
    """Validate input datasets for launch year population generation."""
    # Validate the DOF age/sex/ethnicity distribution dataset
    tests.validate_data(
        table_name="California DOF Age/Sex/Ethnicity Distribution",
        data=launch_inputs["dof_ase"],
        row_count={"key_columns": {"age", "sex", "ethnicity"}},
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )

    # Validate the Estimates Program launch year population data
    tests.validate_data(
        table_name="Estimates Program Launch Year Population",
        data=launch_inputs["estimates"],
        row_count={"key_columns": {"pop_type", "age_group", "sex", "ethnicity"}},
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )


def _create_launch_outputs(launch_inputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Generate launch year population dataset."""
    dof_ase = launch_inputs["dof_ase"]
    estimates = launch_inputs["estimates"]

    # Merge the ASE distribution with the Estimates Program population
    # And split the Estimates age groups into single year of age
    launch_population = estimates.merge(
        dof_ase,
        on=["year", "age_group", "sex", "ethnicity"],
        how="inner",
    ).assign(population=lambda df: df["value"] * df["pct"])

    # Integerize the population values ensuring summations match
    # The original Estimates Program values within age_group
    for pop_type in launch_population["pop_type"].unique():
        for age_group in launch_population["age_group"].unique():
            for sex in launch_population["sex"].unique():
                for ethnicity in launch_population["ethnicity"].unique():
                    # Set filter of age group/sex/ethnicity combination
                    mask = (
                        (launch_population["pop_type"] == pop_type)
                        & (launch_population["age_group"] == age_group)
                        & (launch_population["sex"] == sex)
                        & (launch_population["ethnicity"] == ethnicity)
                    )

                    control = launch_population.loc[mask, "population"].sum()
                    if control == 0:
                        continue
                    else:
                        # Integerize the sex/ethnicity-specific population within this age group
                        # Ensuring the intergerized values sum to the original total from the Estiamtes Program
                        launch_population.loc[mask, "population"] = utils.integerize_1d(
                            data=launch_population.loc[mask, "population"].values,
                            control=control,
                            methodology="weighted_random",
                            generator=generator,
                        )

    # Reshape the dataset from long to wide by population type
    launch_population = (
        launch_population.pivot_table(
            index=["year", "age", "sex", "ethnicity"],
            columns="pop_type",
            values="population",
            fill_value=0,
        )
        .reset_index()
        .rename(
            columns={
                "Household Population": "hhp",
                "Group Quarters - College": "gq_college",
                "Group Quarters - Institutional Correctional Facilities": "gq_prison",
                "Group Quarters - Military": "gq_mil",
                "Group Quarters - Other": "gq_other",
            }
        )
        .assign(
            pop=lambda df: df["hhp"]
            + df["gq_college"]
            + df["gq_prison"]
            + df["gq_mil"]
            + df["gq_other"]
        )
    )

    return launch_population[
        [
            "age",
            "sex",
            "ethnicity",
            "pop",
            "hhp",
            "gq_college",
            "gq_prison",
            "gq_mil",
            "gq_other",
        ]
    ]


def _validate_launch_outputs(launch_population: pd.DataFrame) -> None:
    # Validate the launch year population data
    tests.validate_data(
        table_name="Launch Year Population",
        data=launch_population,
        row_count={"key_columns": {"age", "sex", "ethnicity"}},
        negative={"negative_ok": set()},
        null={"null_ok": set()},
    )
