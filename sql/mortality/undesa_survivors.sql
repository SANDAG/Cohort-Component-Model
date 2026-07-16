/*
This query calculates age-specific crude deaths rates from the UNDESA Survivors Life Table.

The calculation takes a UNDESA dataset identifier indicating the version of the table to use.
It is expected that the Cohort Component Model will use the most recent available.

Given the year for which to calculate rates for, the query selects five years of rolling
data, calculates deaths as the difference in survivors between the current age and the 
next age, and returns five year average crude death rates for ages 85+ segmented by
sex. Although the calculation uses five years of data it is assigned the most recent
year present in the data, similar to how we call 5-year ACS tables by their most recent
year of data.
*/


DECLARE @undesa_id INTEGER = 2;  -- updated based on latest version of UN DESA
DECLARE @year INTEGER;

BEGIN

-- Add check with THROW statement if the UNDESA ID provided does not exist
IF NOT EXISTS (SELECT 1 FROM [socioec_data].[vital_statistics].[undesa] WHERE [undesa_id] = @undesa_id)
    THROW 50001, 'The provided UN DESA ID does not exist in this dataset', 1

-- Add check with THROW statement if the year provided does not exist in the dataset
IF NOT EXISTS (SELECT 1 FROM [socioec_data].[vital_statistics].[undesa_survivors] WHERE [undesa_id] = @undesa_id AND [year] = @year)
    THROW 50002, 'The provided year does not exist in the dataset corresponding to the provided UN DESA ID', 1

-- Add check with THROW statement if 5 years of rolling data is not available
IF (
    SELECT COUNT(DISTINCT [year]) 
    FROM [socioec_data].[vital_statistics].[undesa_survivors] 
    WHERE [undesa_id] = @undesa_id AND [year] BETWEEN @year - 4 AND @year
) < 5
    THROW 50003, 'Five year moving averages are not available for this year and UN DESA ID', 1

END;

-- Select UNDESA version and five years of rolling data
WITH [data] AS (
	SELECT
		[year]
		,CASE
			WHEN [age] = '100+' THEN 100
			ELSE CONVERT(INTEGER, [age])
		END AS [age]
		,CASE
			WHEN [sex] = 'Female' THEN 'F'
			WHEN [sex] = 'Male' THEN 'M'
		END AS [sex]
		,[survivors]
	FROM [socioec_data].[vital_statistics].[undesa_survivors]
	WHERE
		[undesa_id] = @undesa_id
		AND [year] BETWEEN @year-4 AND @year
),
-- Calculate deaths as difference in survivors from previous age group
[deaths_calculated] AS (
	SELECT
		[year]
		,[age]
		,[sex]
		,[survivors]
		,[survivors] - LEAD([survivors], 1) OVER (PARTITION BY [year], [sex] ORDER BY [age]) AS [deaths_single_year]
	FROM [data]
),
[rolling_totals] AS (
	SELECT
		[year]
		,[age]
		,[sex]
		,SUM([survivors]) OVER (
			PARTITION BY [sex], [age] 
			ORDER BY [year] 
			ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
		) AS [survivors_rolling_5yr]
		,SUM([deaths_single_year]) OVER (
			PARTITION BY [sex], [age] 
			ORDER BY [year]
			ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
		) AS [deaths_rolling_5yr]
	FROM [deaths_calculated]
)
-- Calculate five-year average crude death rates limited to ages 85+
SELECT
	@year AS [year]
	,[age]
	,[sex]
	,[deaths_rolling_5yr] / [survivors_rolling_5yr] AS [rates]
	,[survivors_rolling_5yr] AS [survivors]
	,[deaths_rolling_5yr] AS [deaths]
FROM [rolling_totals]
WHERE [year] = @year AND [age] BETWEEN 85 AND 99
ORDER BY [age], [sex]