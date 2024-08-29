-- 2020 Census: Redistricting File (Public Law 94-171) Dataset for California
-- https://www.census.gov/data/datasets/2020/dec/2020-census-redistricting-summary-file-dataset.html
-- Redistricting File translated into Census 2020 DHC Table p5
-- Get total population stratified by race keeping race categories consistent with ACS
-- Temporal resolution is April 1st population
with [p5] AS (
    SELECT
        CASE WHEN [label] = ' !!Total:'  THEN 'Total'
             WHEN [label] = ' !!Total:!!Hispanic or Latino:' THEN 'Hispanic'
             -- Note that Non-Hispanic White and Non-Hispanic Other are combined
             WHEN [label] IN (' !!Total:!!Not Hispanic or Latino:!!White alone', ' !!Total:!!Not Hispanic or Latino:!!Some Other Race alone') THEN 'White alone'
             WHEN [label] = ' !!Total:!!Not Hispanic or Latino:!!Black or African American alone' THEN 'Black or African American alone'
             WHEN [label] = ' !!Total:!!Not Hispanic or Latino:!!American Indian and Alaska Native alone'  THEN 'American Indian or Alaska Native alone'
             WHEN [label] = ' !!Total:!!Not Hispanic or Latino:!!Asian alone'  THEN 'Asian alone'
             WHEN [label] = ' !!Total:!!Not Hispanic or Latino:!!Native Hawaiian and Other Pacific Islander alone'  THEN 'Native Hawaiian or Other Pacific Islander alone'
             WHEN [label] = ' !!Total:!!Not Hispanic or Latino:!!Two or More Races'  THEN 'Two or More Races'
             ELSE NULL END AS [race],
        [value] AS [pop]
    FROM [census_2020].[dhc].[tables]
    INNER JOIN [census_2020].[dhc].[variables]
        ON [tables].[table_id] = [variables].[table_id]
    INNER JOIN [census_2020].[dhc].[values]
        ON [variables].[table_id] = [values].[table_id]
        AND [variables].[variable] = [values].[variable]
    WHERE [tables].[name] = 'P5'  -- HISPANIC OR LATINO ORIGIN BY RACE
)
SELECT [race], SUM([pop]) AS [pop]
FROM [p5]
WHERE [race] IS NOT NULL
GROUP BY [race]
ORDER BY [race]