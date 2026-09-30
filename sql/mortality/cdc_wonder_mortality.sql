/*
	This query loads and prepares CDC WONDER mortality data for a given year.
	The 1999-2020 requires the use of "All Races" "Not Hispanic or Latino" as
	a placeholder for both the "Non-Hispanic, Two or More Races" and
	"Non-Hispanic, Hawaiian or Pacific Islander" categories as they do not
	exist in the product.
*/

DECLARE @year INTEGER = :year;
DECLARE @msg nvarchar(49) = 'Data for CDC WONDER mortality year does not exist';
DECLARE @product NVARCHAR(9) = CASE
    WHEN @year >= 2021 THEN '2018+'
    WHEN @year <= 2020 THEN '1999-2020'
    ELSE NULL END;

-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [socioec_data].[vital_statistics].[cdc_wonder_mortality]
    WHERE [year] = @year
)
SELECT @msg AS [msg]
ELSE
BEGIN
	WITH [data] AS (
		SELECT
			[location]
			-- Convert age to numeric
			,CASE WHEN [age] = '85+' THEN '85' ELSE [age] END AS [age]
			,[sex]
			-- Convert race categories to consistent definition across products
			,CASE 
				WHEN [hispanic_origin] = 'Hispanic or Latino' THEN 'Hispanic'
				WHEN [race] = 'Asian' THEN 'Non-Hispanic, Asian'
				WHEN [race] = 'Asian or Pacific Islander' THEN 'Non-Hispanic, Asian'
				WHEN [race] = 'Black or African American' THEN 'Non-Hispanic, Black'
				WHEN [race] = 'American Indian or Alaska Native' THEN 'Non-Hispanic, American Indian or Alaska Native'
				WHEN [race] = 'More than one race' THEN 'Non-Hispanic, Two or More Races'
				WHEN [race] = 'White' THEN 'Non-Hispanic, White'
				WHEN [race] = 'Native Hawaiian or Other Pacific Islander' THEN 'Non-Hispanic, Hawaiian or Pacific Islander'
				-- "All Races" values are used only within the 1999-2020 product as a placeholder
				-- For "Non-Hispanic, Two or More Races" and "Non-Hispanic, Hawaiian or Pacific Islander"
				WHEN @product = '1999-2020' AND [race] = 'All Races' THEN 'All Races'
				ELSE [race]
			END AS [ethnicity]
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
			AND [year] = @year
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
			-- For "Non-Hispanic, Two or More Races" and "Non-Hispanic, Hawaiian or Pacific Islander"
			AND NOT (
				[product] = '2018+'
				AND [race] = 'All Races'
				AND [hispanic_origin] = 'Not Hispanic or Latino'
			)
	)
	SELECT
		[location]
		,[age]
		,[sex]
		,[ethnicity]
		,[deaths]
		,[pop]
	FROM [data]
	WHERE [ethnicity] != 'All Races'

	-- Following UNION statements use the "All Races" "Not Hispanic or Latino"
	-- To create "Non-Hispanic, Two or More Races" and "Non-Hispanic, Hawaiian or Pacific Islander"
	UNION ALL

	SELECT
		[location]
		,[age]
		,[sex]
		,'Non-Hispanic, Two or More Races' AS [ethnicity]
		,[deaths]
		,[pop]
	FROM [data]
	WHERE [ethnicity] = 'All Races'

	UNION ALL

	SELECT
		[location]
		,[age]
		,[sex]
		,'Non-Hispanic, Hawaiian or Pacific Islander' AS [ethnicity]
		,[deaths]
		,[pop]
	FROM [data]
	WHERE [ethnicity] = 'All Races'

	ORDER BY
		[location]
		,[age]
		,[sex]
		,[ethnicity]
END;