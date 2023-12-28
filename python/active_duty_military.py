"""Generate active-duty military population by race, sex, and single year of age."""

import pandas as pd
from python.utilities import distribute_excess


def get_active_duty_military(
    yr: int,
    launch_yr: int,
    pop_df: pd.DataFrame,
    acs5yr_pums_persons: pd.DataFrame,
    acs5yr_pums_ca_mil: pd.DataFrame,
    dmdc_location_report: pd.DataFrame,
    sdmac_report: pd.DataFrame,
) -> pd.DataFrame:
    """Get active-duty military population broken down by race, sex, and
    single year of age for the increment year. Note the active duty military
    population remains unchanged past the launch year.

    Note: There is concern about the plausibility of race, sex, age
    categories where the entire population is classified as active-duty
    military. If this becomes an issue in need of correction there are two
    recommended strategies. Use three non-overlapping 5-year ACS PUMS persons
    files to ensure distribution of military population across categories is
    plausible and/or alter the "excess population" distribution process to cap
    active-duty military at X% of total population within each category.

    Args:
        yr: Increment year
        launch_yr: Launch year
        pop_df (pd.DataFrame): Population data broken down by race, sex, and
            single year of age
        acs5yr_pums_persons (pd.DataFrame): 5-year ACS PUMS persons
        acs5yr_pums_ca_mil (pd.DataFrame): Total active-duty military
            population for the State of CA from 5-year ACS PUMS persons
        dmdc_location_report (pd.DataFrame): DMDC website location report
            https://dwp.dmdc.osd.mil/dwp/app/dod-data-reports/workforce-reports
        sdmac_report (pd.DataFrame): SDMAC Annual EIR data
            https://sdmac.org/reports/past-sdmac-economic-impact-reports

    Returns:
        pd.DataFrame: The total population data with active-duty military
            population total broken down by race, sex, and single year of age
    """
    # Active-duty military population set and controlled up to the launch year
    if yr <= launch_yr:
        # Must have 5-year ACS for the increment year
        if yr not in acs5yr_pums_persons["year"].unique():
            raise ValueError("Increment year not in ACS 5-year PUMS")

        # Merge the population dataset with the 5-year ACS PUMS
        # For the increment year to add active-duty military population
        df = (
            pop_df[["race", "sex", "age", "pop"]]
            .merge(
                right=acs5yr_pums_persons[acs5yr_pums_persons["year"] == yr][
                    ["race", "sex", "age", "pop_mil"]
                ],
                how="left",
                on=["race", "sex", "age"],
            )
            .fillna(0)
        )

        # Scale the active-duty ACS PUMS population by external control total
        # If increment year is prior to 2018 use DMDC Location Report
        if 2010 <= yr < 2018:
            # Must have DMDC Location report for the increment year
            if yr not in dmdc_location_report["year"].unique():
                raise ValueError("Increment year not in DMDC Location Report")
            elif yr not in acs5yr_pums_ca_mil["year"].unique():
                raise ValueError("Increment year not in ACS 5-year PUMS")
            else:
                # Scale the active-duty ACS PUMS population such that the total for the
                # State of California matches the active-duty total control from the
                # DMDC Location Report for the increment year
                scale_pop_mil_pct = (
                    dmdc_location_report[dmdc_location_report["year"] == yr][
                        "active duty - total"
                    ].iloc[0]
                    / acs5yr_pums_ca_mil[acs5yr_pums_ca_mil["year"] == yr][
                        "pop_ca_mil"
                    ].iloc[0]
                )
        # If increment year is >= 2018
        elif 2018 <= yr:
            # Must have SDMAC report for the increment year
            if yr not in sdmac_report["report"].unique():
                raise ValueError("Increment year not in SDMAC Report dataset")
            else:
                # Scale the active-duty ACS PUMS population such that the total for
                # San Diego County matches the active-duty total control from the
                # SDMAC report for the increment year
                scale_pop_mil_pct = (
                    sdmac_report[
                        (sdmac_report["report"] == yr)
                        & (sdmac_report["year"] == yr)
                        & (sdmac_report["site"] == "All")
                    ]["active duty"].iloc[0]
                    / df["pop_mil"].sum()
                )
        else:
            raise ValueError("Invalid increment year.")

        df["pop_mil"] = df["pop_mil"] * scale_pop_mil_pct

        # Distribute excess active-duty military from categories where
        # The active-duty military exceeds the total population
        # To categories where it is less than the total population using the
        # Distribution of active-duty military within categories where the
        # Active-duty military is less than the total population
        df["pop_mil"] = distribute_excess(df=df, subset="pop_mil", total="pop")

        return df[["race", "sex", "age", "pop", "pop_mil"]]

    # Active-duty military population held constant past the launch year
    else:
        return pop_df[["race", "sex", "age", "pop", "pop_mil"]]
