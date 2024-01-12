-- Get the San Diego County population projections from CA DOF
-- https://dof.ca.gov/forecasting/demographics/projections/
-- Stratify by year, race, sex, age keeping race categories consistent with ACS
-- Temporal resolution is July 1st population
SELECT [year], [race], [sex], [age], SUM([pop]) AS [pop]
FROM (
	SELECT
		[fiscal_yr] AS [year],
		CASE	WHEN [race_code] = 1  then 'White alone'
				WHEN [race_code] = 2  then 'Black or African American alone'
				WHEN [race_code] = 3  then 'American Indian or Alaska Native alone'
				WHEN [race_code] = 4  then 'Asian alone'
				WHEN [race_code] = 5  then 'Native Hawaiian or Other Pacific Islander alone'
				WHEN [race_code] = 6  then 'Two or More Races'
				WHEN [race_code] = 7  then 'Hispanic'
		END AS [race],
		[sex],
		[age],
		[population] AS [pop]
	FROM
		[socioec_data].[ca_dof].[population_proj_2021_07_14]
	-- Vintage 2020 (2021.7.14)
	WHERE
        [county_fips_code] = 6073  -- San Diego County
) AS [tt]
GROUP BY [year], [race], [sex], [age]