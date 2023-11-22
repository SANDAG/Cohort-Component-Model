-- 2020 Census: Redistricting File (Public Law 94-171) Dataset for California
-- https://www.census.gov/data/datasets/2020/dec/2020-census-redistricting-summary-file-dataset.html
-- Get total population stratified by race keeping race categories consistent with ACS
-- Temporal resolution is April 1st population
-- Note that Non-Hispanic White and Non-Hispanic Other are combined
with
    [tt]
    AS
    (
        SELECT
            [P0020001],
            [P0020002],
            [P0020005],
            [P0020006],
            [P0020007],
            [P0020008],
            [P0020009],
            [P0020010],
            [P0020011]
        FROM
            [census].[decennial].[pl_94_171_2020_ca]
        -- 2020 file
        WHERE
		[sumlev] = 050 -- County level
            AND [county] = '073'
        -- San Diego County
    )
    SELECT 'Total' AS [race], [P0020001] AS [pop]
    FROM [tt]
UNION ALL
    SELECT 'Hispanic' AS [race], [P0020002] AS [pop]
    FROM [tt]
UNION ALL
    SELECT 'White alone' AS [race], [P0020005] + [P0020010] AS [pop]
    FROM [tt]
-- NH White + NH Other
UNION ALL
    SELECT 'Black or African American alone' AS [race], [P0020006] AS [pop]
    FROM [tt]
UNION ALL
    SELECT 'American Indian or Alaska Native alone' AS [race], [P0020007] AS [pop]
    FROM [tt]
UNION ALL
    SELECT 'Asian alone' AS [race], [P0020008] AS [pop]
    FROM [tt]
UNION ALL
    SELECT 'Native Hawaiian and Other Pacific Islander alone' AS [race], [P0020009] AS [pop]
    FROM [tt]
UNION ALL
    SELECT 'Two or More Races' AS [race], [P0020011] AS [pop]
    FROM [tt]