/*
Get the regional age/sex/ethnicity controls used by the Estimates Program from
the California Department of Finance. Create single year of age distributions
within each age group/sex/ethnicity category such that the Cohort Component
Model can break out single year of age population within each category.

See https://github.com/SANDAG/Estimates-Program/blob/main/sql/ase/get_region_ase_total.sql
*/


-- Initialize parameters -----------------------------------------------------
DECLARE @year integer = :year;


-- Get age/sex/ethnicity controls from California DOF ------------------------
-- Intercensal 2010-2019 uses Estimates
IF @year BETWEEN 2010 AND 2019
BEGIN 
    WITH [intercensal_ase] AS (
        SELECT
            CASE WHEN [age] > 99 THEN 99 ELSE [age] END AS [age],
            CASE 
                WHEN [age] BETWEEN 0 AND 4 THEN 'Under 5'
                WHEN [age] BETWEEN 5 AND 9 THEN '5 to 9'
                WHEN [age] BETWEEN 10 AND 14 THEN '10 to 14'
                WHEN [age] BETWEEN 15 AND 17 THEN '15 to 17'
                WHEN [age] BETWEEN 18 AND 19 THEN '18 and 19'
                WHEN [age] BETWEEN 20 AND 24 THEN '20 to 24'
                WHEN [age] BETWEEN 25 AND 29 THEN '25 to 29'
                WHEN [age] BETWEEN 30 AND 34 THEN '30 to 34'
                WHEN [age] BETWEEN 35 AND 39 THEN '35 to 39'
                WHEN [age] BETWEEN 40 AND 44 THEN '40 to 44'
                WHEN [age] BETWEEN 45 AND 49 THEN '45 to 49'
                WHEN [age] BETWEEN 50 AND 54 THEN '50 to 54'
                WHEN [age] BETWEEN 55 AND 59 THEN '55 to 59'
                WHEN [age] BETWEEN 60 AND 61 THEN '60 and 61'
                WHEN [age] BETWEEN 62 AND 64 THEN '62 to 64'
                WHEN [age] BETWEEN 65 AND 69 THEN '65 to 69'
                WHEN [age] BETWEEN 70 AND 74 THEN '70 to 74'
                WHEN [age] BETWEEN 75 AND 79 THEN '75 to 79'
                WHEN [age] BETWEEN 80 AND 84 THEN '80 to 84'
                WHEN [age] >= 85 THEN '85 and Older'
                ELSE NULL
            END AS [age_group],
            [sex],
            CASE
                WHEN [race/ethnicity] = 'Hispanic (any race)' THEN 'Hispanic'
                WHEN [race/ethnicity] = 'White, Non-Hispanic' THEN 'Non-Hispanic, White'
                WHEN [race/ethnicity] = 'Black, Non-Hispanic' THEN 'Non-Hispanic, Black'
                WHEN [race/ethnicity] = 'American Indian or Alaska Native, Non-Hispanic' THEN 'Non-Hispanic, American Indian or Alaska Native'
                WHEN [race/ethnicity] = 'Asian, Non-Hispanic' THEN 'Non-Hispanic, Asian'
                WHEN [race/ethnicity] = 'Native Hawaiian or Pacific Islander, Non-Hispanic' THEN 'Non-Hispanic, Hawaiian or Pacific Islander'
                WHEN [race/ethnicity] = 'Multiracial (two or more of above races), Non-Hispanic' THEN 'Non-Hispanic, Two or More Races'
                ELSE NULL
            END AS [ethnicity],
            [population]
        FROM [socioec_data].[ca_dof].[estimates_intercensal_ase]
        WHERE 
            [estimates_id] = 26  -- Intercensal ASE 2010-2020 years: January 2025
            AND [fips] = '06073'
            AND [year] = @year
    ),
    [values] AS (
        SELECT
            [age],
            [age_group],
            [sex],
            [ethnicity],
            SUM([population]) AS [population]
        FROM [intercensal_ase]
        GROUP BY
            [age],
            [age_group],
            [sex],
            [ethnicity]
    )
    SELECT
        @year AS [year],
        [age],
        [age_group],
        [sex],
        [ethnicity],
        1.0 * [population] / SUM([population]) OVER (PARTITION BY [age_group], [sex], [ethnicity]) AS [pct]
    FROM [values]
    ORDER BY
        [age],
        [age_group],
        [sex],
        [ethnicity]
END
-- 2020+ uses Projections
ELSE IF @year >= 2020
BEGIN
    WITH [p3] AS (
        SELECT
            CASE WHEN [age] > 99 THEN 99 ELSE [age] END AS [age],
            CASE
                WHEN [age] BETWEEN 0 AND 4 THEN 'Under 5'
                WHEN [age] BETWEEN 5 AND 9 THEN '5 to 9'
                WHEN [age] BETWEEN 10 AND 14 THEN '10 to 14'
                WHEN [age] BETWEEN 15 AND 17 THEN '15 to 17'
                WHEN [age] BETWEEN 18 AND 19 THEN '18 and 19'
                WHEN [age] BETWEEN 20 AND 24 THEN '20 to 24'
                WHEN [age] BETWEEN 25 AND 29 THEN '25 to 29'
                WHEN [age] BETWEEN 30 AND 34 THEN '30 to 34'
                WHEN [age] BETWEEN 35 AND 39 THEN '35 to 39'
                WHEN [age] BETWEEN 40 AND 44 THEN '40 to 44'
                WHEN [age] BETWEEN 45 AND 49 THEN '45 to 49'
                WHEN [age] BETWEEN 50 AND 54 THEN '50 to 54'
                WHEN [age] BETWEEN 55 AND 59 THEN '55 to 59'
                WHEN [age] BETWEEN 60 AND 61 THEN '60 and 61'
                WHEN [age] BETWEEN 62 AND 64 THEN '62 to 64'
                WHEN [age] BETWEEN 65 AND 69 THEN '65 to 69'
                WHEN [age] BETWEEN 70 AND 74 THEN '70 to 74'
                WHEN [age] BETWEEN 75 AND 79 THEN '75 to 79'
                WHEN [age] BETWEEN 80 AND 84 THEN '80 to 84'
                WHEN [age] >= 85 THEN '85 and Older'
                ELSE NULL
            END AS [age_group],
            [sex],
            CASE
                WHEN [race/ethnicity] = 'Hispanic (any race)' THEN 'Hispanic'
                WHEN [race/ethnicity] = 'White, Non-Hispanic' THEN 'Non-Hispanic, White'
                WHEN [race/ethnicity] = 'Black, Non-Hispanic' THEN 'Non-Hispanic, Black'
                WHEN [race/ethnicity] = 'American Indian or Alaska Native, Non-Hispanic' THEN 'Non-Hispanic, American Indian or Alaska Native'
                WHEN [race/ethnicity] = 'Asian, Non-Hispanic' THEN 'Non-Hispanic, Asian'
                WHEN [race/ethnicity] = 'Native Hawaiian or Pacific Islander, Non-Hispanic' THEN 'Non-Hispanic, Hawaiian or Pacific Islander'
                WHEN [race/ethnicity] = 'Multiracial (two or more of above races), Non-Hispanic' THEN 'Non-Hispanic, Two or More Races'
                ELSE NULL
            END AS [ethnicity],
            [population]
        FROM [socioec_data].[ca_dof].[projections_p3]
        WHERE 
            [projections_id] = 16  -- Vintage 2026 (2026.03.13)
            AND [fips] = '06073'
            AND [year] = @year
    ),
    [values] AS (
        SELECT
            [age],
            [age_group],
            [sex],
            [ethnicity],
            SUM([population]) AS [population]
        FROM [p3]
        GROUP BY
            [age],
            [age_group],
            [sex],
            [ethnicity]
    )
    SELECT
        @year AS [year],
        [age],
        [age_group],
        [sex],
        [ethnicity],
        1.0 * [population] / SUM([population]) OVER (PARTITION BY [age_group], [sex], [ethnicity]) AS [pct]
    FROM [values]
    ORDER BY
        [age],
        [age_group],
        [sex],
        [ethnicity]
END