from python.base_yr import get_active_duty_mil, get_base_yr_2020
from python.birth_rates import get_birth_rates
from python.death_rates import get_death_rates, load_ss_life_tbl
from python.migration_rates import get_migration_rates
import json
import pandas as pd
import sqlalchemy as sql


# Read JSON configuration files
with open("config.JSON") as file:
    config = json.load(file)
with open("rates_map.JSON") as file:
    rates_map = json.load(file)


# Get SQL data sources
engine = sql.create_engine("mssql+pymssql://" + config["sql"]["server"] + "/")
with engine.connect() as connection:
    # get State of CA active-duty military ACS PUMS total
    with open(config["sql"]["acs5yr_pums_ca_mil"], "r") as query:
        acs5yr_pums_ca_mil = pd.read_sql_query(query.read(), connection)
    # get ACS PUMS in/out migrants for San Diego County
    with open(config["sql"]["acs5yr_pums_migrants"], "r") as query:
        acs5yr_pums_migrants = pd.read_sql_query(query.read(), connection)
    # get San Diego County ACS PUMS persons
    with open(config["sql"]["acs5yr_pums_persons"], "r") as query:
        acs5yr_pums_persons = pd.read_sql_query(query.read(), connection)
    # get San Diego County population estimates from CA DOF
    with open(config["sql"]["dof_estimates"], "r") as query:
        dof_estimates = pd.read_sql_query(query.read(), connection)
    # get San Diego County population projections from CA DOF
    with open(config["sql"]["dof_projections"], "r") as query:
        dof_projections = pd.read_sql_query(query.read(), connection)
    # get Census redistricting data
    with open(config["sql"]["census_redistricting"], "r") as query:
        census_redistricting = pd.read_sql_query(query.read(), connection)


# Get local csv data sources
dmdc_location_report = pd.read_csv(config["csv"]["dmdc_location_report"])
sdmac_report = pd.read_csv(config["csv"]["sdmac_report"])
ss_life_tbl = load_ss_life_tbl(config["csv"]["ss_life_table"])


# Initialize chosen base year dataset
# For base years >= 2020 use the blended base year approach
if 2020 <= config["interval"]["base"] < 2030:
    base_df = get_base_yr_2020(
        base_yr=config["interval"]["base"],
        acs5yr_pums_persons=acs5yr_pums_persons,
        dof_estimates=dof_estimates,
        dof_projections=dof_projections,
        census_redistricting=census_redistricting,
    )
# For base years >= 2010 (and < 2020) use the 2010 decennial Census
elif 2010 <= config["interval"]["base"] < 2020:
    raise ValueError("Base years prior to 2020 not available.")
else:
    raise ValueError("Invalid base year provided.")


# Break out the base year active-duty military population
# From the total population of the chosen base year dataset
base_df = get_active_duty_mil(
    base_yr=config["interval"]["base"],
    base_df=base_df,
    acs5yr_pums_persons=acs5yr_pums_persons,
    acs5yr_pums_ca_mil=acs5yr_pums_ca_mil,
    dmdc_location_report=dmdc_location_report,
    sdmac_report=sdmac_report,
)


# Get base-year crude birth, death, and migration rates
base_rates = {
    "births": get_birth_rates(
        base_yr=config["interval"]["base"], base_df=base_df, rates_map=rates_map
    ),
    "deaths": get_death_rates(
        base_yr=config["interval"]["base"], ss_life_tbl=ss_life_tbl, rates_map=rates_map
    ),
    "migration": get_migration_rates(
        base_yr=config["interval"]["base"],
        base_df=base_df,
        acs5yr_pums_migrants=acs5yr_pums_migrants,
    ),
}
