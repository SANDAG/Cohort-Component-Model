-- Get the San Diego County population estimates from CA DOF
-- https://dof.ca.gov/forecasting/demographics/estimates/
-- E-5 Population and Housing Estimates for Cities, Counties, and the State
-- Temporal resolution is January 1st population
SELECT
    REPLACE([estimates].[name], 'E-5: Vintage ', '') AS [vintage], -- vintage goes back to 2023
    [estimates_e5].[year],
    [total_population] AS [pop],
    [group_quarters] AS [gq]
FROM [socioec_data].[ca_dof].[estimates_e5]
    INNER JOIN [socioec_data].[ca_dof].[estimates]
    ON [estimates_e5].[estimates_id] = [estimates].[estimates_id]
    INNER JOIN [socioec_data].[ca_dof].[fips]
    ON [estimates_e5].[fips] = [fips].[fips]
WHERE
	[fips].[name] = 'San Diego County'
    AND [estimates_e5].[area_name] = 'County Total'
ORDER BY
	REPLACE([estimates].[name], 'E-5: Vintage ', ''),
	[estimates_e5].[year]