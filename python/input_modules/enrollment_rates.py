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


def run_enrollment_rates(year: int) -> pd.DataFrame:
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
    the household population to create regional enrollment by enrollment
    category, with the "Group Quarters - College" population added to the
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
        _validate_enrollment_inputs(enrollment_inputs)

        enrollment_outputs = _create_enrollment_outputs(enrollment_inputs)
        _validate_enrollment_outputs(enrollment_outputs)

        return enrollment_outputs
    else:
        raise ValueError("Enrollment rates can only be run for the launch year")


def _get_enrollment_inputs(year: int) -> dict[str, pd.DataFrame]:
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
        cde_enrollment = pd.DataFrame()

    return {
        "acs_enrollment": acs_enrollment,
        "eligible_population": eligible_population,
        "cde_enrollment": cde_enrollment,
    }


def _validate_enrollment_inputs(
    enrollment_inputs: dict[str, pd.DataFrame],
) -> None:
    """Validate the input datasets for school enrollment rates."""
    # Validate ACS enrollment counts
    tests.validate_data(
        table_name="Input ACS Enrollment Counts",
        data=enrollment_inputs["acs_enrollment"],
        negative={},
        null={"null_ok": {"tk_reallocation", "enrollment_category"}},
    )
    # Validate ACS enrollment eligible population
    tests.validate_data(
        table_name="Input ACS Enrollment Eligible Population",
        data=enrollment_inputs["eligible_population"],
        row_count={"key_columns": {"age"}},
        negative={},
        null={},
    )
    # Validate CDE enrollment counts
    if not enrollment_inputs["cde_enrollment"].empty:
        tests.validate_data(
            table_name="Input CDE Enrollment Counts",
            data=enrollment_inputs["cde_enrollment"],
            negative={},
            null={},
        )


def _create_enrollment_outputs(
    enrollment_inputs: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Create the output DataFrame for enrollment rates."""
    acs_enrollment = enrollment_inputs["acs_enrollment"]
    eligible_population = enrollment_inputs["eligible_population"]
    cde_enrollment = enrollment_inputs["cde_enrollment"]

    # If the CDE enrollment data is available
    if not cde_enrollment.empty:
        # Allocate Nursery school/preschool enrollment to Kindergarten
        # For 4 and 5 year olds such that the total Kindergarten enrollment
        # Is at least as large as the total CDE TK + Kindergarten enrollment
        # Or until there is no more Nursery school/preschool enrollment to allocate
        for age in [4, 5]:
            cde_total = (
                cde_enrollment.loc[cde_enrollment["Age Group"] == age][
                    ["Grade TK", "Grade K"]
                ]
                .sum()
                .sum()
            )

            # If the Kindergarten enrollment is less than the total CDE enrollment
            # Then add the minimum of the difference and the available Nursery school/preschool enrollment
            k_total = acs_enrollment.loc[
                (acs_enrollment["AGEP"] == age)
                & (acs_enrollment["tk_reallocation"] == "Kindergarten")
            ]["PWGTP"].sum()

            if k_total < cde_total:
                # Get the allocation adjustment
                nursery_total = acs_enrollment.loc[
                    (acs_enrollment["AGEP"] == age)
                    & (acs_enrollment["tk_reallocation"] == "Nursery school/preschool"),
                    "PWGTP",
                ].sum()
                allocation = min(cde_total - k_total, nursery_total)

                # Apply allocation adjustment to the enrollment
                acs_enrollment.loc[
                    (acs_enrollment["AGEP"] == age)
                    & (acs_enrollment["enrollment_category"] == "K-4th"),
                    "PWGTP",
                ] += allocation

    # Aggregate the ACS enrollment counts by age and enrollment category
    acs_enrollment = acs_enrollment.groupby(
        ["AGEP", "enrollment_category"], as_index=False
    )["PWGTP"].sum()

    # Merge the ACS enrollment counts with the eligible population
    # And calculate enrollment rates by age and enrollment category
    enrollment_rates = eligible_population.merge(
        acs_enrollment, how="left", left_on="age", right_on="AGEP"
    ).assign(
        # Avoid divide by zero setting the rate to 0 when the population is 0
        rate=lambda x: (x["PWGTP"] / x["pop"].replace(0, np.nan)).fillna(0)
    )

    # Ensure every age and enrollment category combination is present
    all_combinations = pd.MultiIndex.from_product(
        [
            eligible_population["age"].unique(),
            acs_enrollment["enrollment_category"].unique(),
        ],
        names=["age", "enrollment_category"],
    )

    enrollment_rates = (
        enrollment_rates.set_index(["age", "enrollment_category"])
        .reindex(all_combinations, fill_value=0)
        .reset_index()
    )

    return enrollment_rates[["age", "enrollment_category", "rate"]]


def _validate_enrollment_outputs(
    enrollment_outputs: pd.DataFrame,
) -> None:
    """Validate the output datasets for school enrollment rates."""
    # Validate ACS enrollment counts
    tests.validate_data(
        table_name="Output Enrollment Rates",
        data=enrollment_outputs,
        row_count={"key_columns": {"age", "enrollment_category"}},
        negative={},
        null={},
    )
