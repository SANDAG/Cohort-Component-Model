-- Get the San Diego County population estimates from CA DOF
-- https://dof.ca.gov/forecasting/demographics/estimates/
-- E-5 Population and Housing Estimates for Cities, Counties, and the State
-- Temporal resolution is January 1st population
SELECT
    [est_yr] AS [year],
    [total_pop] AS [pop]
FROM
    [socioec_data].[ca_dof].[population_housing_estimates]
WHERE
    [vintage_yr] = 2022 -- version
    AND [area_type] = 'County'
    AND [area_name] = 'San Diego'
    AND [summary_type] = 'Total'