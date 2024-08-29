-- Get the San Diego County population projections from CA DOF
-- https://dof.ca.gov/forecasting/demographics/projections/
-- Stratify by year, race, sex, age keeping race categories consistent with ACS
-- Only interested in base year 2020 data for launch years >= 2020
-- Temporal resolution is July 1st population
WITH [projections] AS (
    SELECT
        SUBSTRING(REPLACE([name], 'Vintage ', ''), 1, 4) AS [vintage],
        MAX([projections_id]) AS [projections_id]
        -- Take the most recent projection within each vintage
    FROM [socioec_data].[ca_dof].[projections]
    GROUP BY SUBSTRING(REPLACE([name], 'Vintage ', ''), 1, 4)
),
[formatted_data] AS (
    SELECT
        CONVERT(int, [vintage]) AS [vintage],
        CONVERT(int, [year]) AS [year],
        CASE WHEN [age] > 110 THEN 110 ELSE [age] END AS [age], -- maximum age is 110
        CASE WHEN [sex] = 'Female' THEN 'F' WHEN [sex] = 'Male' THEN 'M' ELSE NULL END AS [sex],
        CASE WHEN [race/ethnicity] = 'White, Non-Hispanic' THEN 'White alone'
             WHEN [race/ethnicity] = 'Black, Non-Hispanic' THEN 'Black or African American alone'
             WHEN [race/ethnicity] = 'American Indian or Alaska Native, Non-Hispanic' THEN 'American Indian or Alaska Native alone'
             WHEN [race/ethnicity] = 'Asian, Non-Hispanic' THEN 'Asian alone'
             WHEN [race/ethnicity] = 'Native Hawaiian or Pacific Islander, Non-Hispanic' THEN 'Native Hawaiian or Other Pacific Islander alone'
             WHEN [race/ethnicity] = 'Multiracial (two or more of above races), Non-Hispanic' THEN 'Two or More Races'
             WHEN [race/ethnicity] = 'Hispanic (any race)' THEN 'Hispanic'
             ELSE NULL END AS [race],
        [population] AS [pop]
    FROM [socioec_data].[ca_dof].[projections_p3]
    INNER JOIN [projections]
        ON [projections_p3].[projections_id] = [projections_p3].[projections_id]
    INNER JOIN [socioec_data].[ca_dof].[fips]
        ON [projections_p3].[fips] = [fips].[fips]
    WHERE
        [vintage] >= 2020 -- only used for launch years >= 2020
        AND [year] = 2020 -- only interested in this data for base year 2020
        AND [fips].[name] = 'San Diego County'
)
SELECT [vintage], [year], [age], [sex], [race], SUM([pop]) AS [pop]
FROM [formatted_data]
GROUP BY [vintage], [year], [age], [sex], [race]
ORDER BY [vintage], [year], [age], [sex], [race]