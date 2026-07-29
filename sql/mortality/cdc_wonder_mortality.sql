/*
	This query loads and prepares CDC WONDER mortality data for a given year.
	The year chosen selects the CDC product used. The 1999-2020 requires the
	use of "All Races" "Not Hispanic or Latino" as a placeholder for both the
	"Two or More Races" and "Native Hawaiian or Other Pacific Islander alone"
	categories as they do not exist in the product.
*/

DECLARE @year INTEGER = :year;
DECLARE @product NVARCHAR(9) = CASE
    WHEN @year >= 2021 THEN '2018+'
    WHEN @year <=2020 THEN '1999-2020'
    ELSE NULL END;

BEGIN
    -- Throw error if year doesn't exist
    IF NOT EXISTS (
      SELECT 1 FROM [socioec_data].[vital_statistics].[cdc_wonder_mortality] 
      WHERE [year] = @year
    )
    THROW 50002, 'The provided year does not exist in the CDC WONDER mortality dataset', 1;
END;

WITH [data] AS (
	SELECT
		[year]
		,[location]
		-- Convert age to numeric
		,CASE
			WHEN [age] = '85+' THEN '85'
			ELSE [age]
		END AS [age]
		-- Convert sex to single character
		,CASE [sex]
			WHEN 'Female' THEN 'F'
			WHEN 'Male' THEN 'M'
		END AS [sex]
		-- Convert race categories to consistent definition across products
		,CASE 
			WHEN [hispanic_origin] = 'Hispanic or Latino' THEN 'Hispanic'
			WHEN [race] = 'Asian' THEN 'Asian alone'
			WHEN [race] = 'Asian or Pacific Islander' THEN 'Asian alone'
			WHEN [race] = 'Black or African American' THEN 'Black or African American alone'
			WHEN [race] = 'American Indian or Alaska Native' THEN 'American Indian or Alaska Native alone'
			WHEN [race] = 'More than one race' THEN 'Two or More Races'
			WHEN [race] = 'White' THEN 'White alone'
			WHEN [race] = 'Native Hawaiian or Other Pacific Islander' THEN 'Native Hawaiian or Other Pacific Islander alone'
			-- "All Races" values are used only within the 1999-2020 product as a placeholder
			-- For "Two or More Races" and "Native Hawaiian or Other Pacific Islander alone"
			WHEN @product = '1999-2020' AND [race] = 'All Races' THEN 'All Races'
			ELSE [race]
		END AS [race]
		,CASE
			-- Population is suppressed at the county level in the 2018+ CDC WONDER product
			-- We are forced to use the population within the CCM software which is not a five year sum
			WHEN @product = '2018+' AND [location] = 'San Diego County' THEN [deaths]/5.0
			ELSE [deaths]/1.0
		END AS [deaths]
		,[pop]
	FROM [socioec_data].[vital_statistics].[cdc_wonder_mortality]
	WHERE
		[product] = @product
		-- Five year rolling sums used
		AND [period] = 'Five-Year'
		-- These values are only used in the inflation factor calculation
		AND [age] NOT IN (
			'All Stated Ages',
			'Not Stated'
		)
		-- These values are only used in the inflation factor calculation
		AND [hispanic_origin] NOT IN (
			'Hispanic or Latino; Not Hispanic or Latino',
			'All Origins',
			'Not Stated'
		)
		-- "All Races" values are used only within the 1999-2020 product as a placeholder
		-- For "Two or More Races" and "Native Hawaiian or Other Pacific Islander alone"
		AND NOT (
			[product] = '2018+'
			AND [race] = 'All Races'
			AND [hispanic_origin] = 'Not Hispanic or Latino'
		)
)
SELECT
	[year]
	,[location]
	,[age]
	,[sex]
	,[race]
	,[deaths]
	,[pop]
FROM [data]
WHERE [race] != 'All Races' AND [year] = @year 

-- Following UNION statements use the "All Races" "Not Hispanic or Latino"
-- To create "Two or More Races" and "Native Hawaiian or Other Pacific Islander alone"
UNION ALL

SELECT
	[year]
	,[location]
	,[age]
	,[sex]
	,'Two or More Races' AS [race]
	,[deaths]
	,[pop]
FROM [data]
WHERE [race] = 'All Races' AND [year] = @year AND [year] <= 2020

UNION ALL

SELECT
	[year]
	,[location]
	,[age]
	,[sex]
	,'Native Hawaiian or Other Pacific Islander alone' AS [race]
	,[deaths]
	,[pop]
FROM [data]
WHERE [race] = 'All Races' AND [year] = @year AND [year] <= 2020

ORDER BY
	[year]
	,[location]
	,[age]
	,[sex]
	,[race]