/* 
    This query loads and prepares the DOF P3 projections data for the given year by 
    renaming fields to match the CCM fields. The query uses projections_id = 7 for years 
    2010-2019 and projections_id = 16 for years 2020 and on. Should more recent projections 
    be added, the query will need to be updated to replace the projections_id values for 
    2020 and on.
*/

DECLARE @year INTEGER = :year;

BEGIN
    -- Add check with THROW statement if the year provided does not exist in the dataset
    IF NOT EXISTS (SELECT 1 FROM [socioec_data].[ca_dof].[projections_p3] WHERE [year] = @year)
        THROW 50002, 'The provided year does not exist in the DOF P3 projections dataset', 1
END;

SELECT
    CASE [race/ethnicity]
        WHEN 'American Indian or Alaska Native, Non-Hispanic' THEN 'American Indian or Alaska Native alone'
        WHEN 'Asian, Non-Hispanic' THEN 'Asian alone'
        WHEN 'Black, Non-Hispanic' THEN 'Black or African American alone'
        WHEN 'Hispanic (any race)' THEN 'Hispanic'
        WHEN 'Native Hawaiian or Pacific Islander, Non-Hispanic' THEN 'Native Hawaiian or Other Pacific Islander alone'
        WHEN 'Multiracial (two or more of above races), Non-Hispanic' THEN 'Two or More Races'
        WHEN 'White, Non-Hispanic' THEN 'White alone'
        ELSE [race/ethnicity]
    END AS [race]
    ,[age]
    ,[year]
    ,SUM([population]) AS [pop]
FROM [socioec_data].[ca_dof].[projections_p3]
WHERE 
-- Projections_id = 7 contains data for 2010-2019
-- Projections_id = 16 contains data for 2020 and on
    (([projections_id] = 7 AND [year] <= 2019) OR 
        ([projections_id] = 16 AND [year] >= 2020))
    AND [sex] = 'Female' AND [age] BETWEEN 15 AND 44 
    AND [year] = @year
GROUP BY [year], [race/ethnicity], [age]
ORDER BY [year], [race], [age]