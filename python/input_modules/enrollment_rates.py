"""Get school enrollment rates by single year of age."""

import logging

import numpy as np
import pandas as pd
import sqlalchemy as sql

from functools import lru_cache

import python.tests as tests
import python.utils as utils

generator = np.random.default_rng(utils.RANDOM_SEED)
logger = logging.getLogger(__name__)


def run_enrollment_rates(year: int) -> None:
    """Orchestrator function to calculate enrollment rates.

    This module generates school enrollment rates by single year of age using
    ACS PUMS data. Rates are calculated for K-4th, 5th-8th, 9th-12th, and
    College categories. For years 2023 and beyond, the California Department
    of Education enrollment data is used to adjust Nursery school/preschool
    persons into the Kindergarten category to account for universal TK and
    misspecified enrollment data.

    The rates are only calculated from the ACS PUMS household population as it
    is assumed that all "Group Quarters - College" population is enrolled in
    the College category while all other group quarters populations are
    excluded from school enrollment. Calculated rates are then only applied to
    the household population to create regional enrollment byh enrollment
    category with the "Group Quarters - College" population added to the
    College enrollment category.

    Functionality is split apart for code encapsulation:
        _get_enrollment_inputs - Get enrollment counts and eligible population
            by single year of age from the ACS 5-year PUMS along with the
            California Department of Education enrollment dataset
        _validate_enrollment_inputs - Validate inputs from the above function
        _create_enrollment_outputs - Adjust enrollment counts to account for
            universal TK (if applicable) and calculate enrollment rates by
            enrollment category by single year of age
        _validate_enrollment_outputs - Validate the output from the above function
    """
    if year == utils.LAUNCH_YEAR:
        logger.info("Calculating enrollment rates for launch year")

        enrollment_inputs = _get_enrollment_inputs(year)
        print(enrollment_inputs)
        _validate_enrollment_inputs(enrollment_inputs)

        # enrollment_outputs = _create_enrollment_outputs(enrollment_inputs, year)
        # _validate_enrollment_outputs(enrollment_outputs)

        # return enrollment_outputs
    else:
        raise ValueError("Enrollment rates can only be run for the launch year")


def _get_enrollment_inputs(year: int) -> dict[str, pd.DataFrame | None]:
    """Load input datasets for enrollment rate generation."""
    with utils.ESTIMATES_ENGINE.connect() as connection:
        with open(utils.SQL_FOLDER / "enrollment" / "get_acs_enrollment.sql") as file:
            acs_enrollment = utils.read_sql_query_fallback(
                max_lookback=1,
                sql=sql.text(file.read()),
                con=connection,
                params={"year": year},
            )

        with open(
            utils.SQL_FOLDER / "enrollment" / "get_eligible_population.sql"
        ) as file:
            eligible_population = utils.read_sql_query_fallback(
                max_lookback=1,
                sql=sql.text(file.read()),
                con=connection,
                params={"year": year},
            )

    if year >= 2023:
        # Read in the California Department of Education Excel Workbook
        cde_enrollment = pd.read_excel(
            utils.DATA_FOLDER
            / "enrollment"
            / "K-12 Enrollment by Age Group and Grade.xlsx",
            sheet_name=str(year),
            skiprows=3,
        )

    else:
        cde_enrollment = None

    return {
        "acs_enrollment": acs_enrollment,
        "eligible_population": eligible_population,
        "cde_enrollment": cde_enrollment,
    }
