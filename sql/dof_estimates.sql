-- Get the San Diego County population estimates from CA DOF
-- https://dof.ca.gov/forecasting/demographics/estimates/
-- E-5 Population and Housing Estimates for Cities, Counties, and the State
-- Temporal resolution is January 1st population
SELECT
    [vintage_yr] AS [vintage], -- version goes back to 2013
    [est_yr] AS [year],
    [total_pop] AS [pop],
    [group_quarters] AS [gq]
FROM
    [socioec_data].[ca_dof].[population_housing_estimates]
WHERE
    [vintage_yr] IS NOT NULL -- data exists without version
    AND [area_type] = 'County'
    AND [area_name] = 'San Diego'
    AND [summary_type] = 'Total'