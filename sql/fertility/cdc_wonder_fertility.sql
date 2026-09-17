/* 
    This query loads and prepares the CDC WONDER fertility data for the given
    year by aligning fields with Cohort Component Model standards, removing
    ages <15 and >44 and "Not Stated Rows", and accounting for missing
    race/ethnicity categories in the 2007-2019 product using the "All Races"
    values for both "Non-Hispanic, Two or More Races" and
    "Non-Hispanic, Hawaiian or Pacific Islander".

    Note: This querly only handles years from 2012 onwards as that is the
    first five-year average available (2007-2012).
*/

DECLARE @year INTEGER = :year;
DECLARE @msg nvarchar(49) = 'Data for CDC WONDER fertility year does not exist';
DECLARE @product NVARCHAR(9) = CASE
    WHEN @year >= 2020 THEN '2020+'
    WHEN @year <= 2019 THEN '2007-2019'
    ELSE NULL END;

-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [socioec_data].[vital_statistics].[cdc_wonder_fertility]
    WHERE [year] = @year
)
SELECT @msg AS [msg]
ELSE
BEGIN
    WITH [data] AS (
        SELECT
            [location]
            ,[year]
            ,[age] AS [age_group]
            ,CASE 
                WHEN [hispanic_origin] = 'Hispanic or Latino' THEN 'Hispanic'
                WHEN [race] = 'Asian' THEN 'Non-Hispanic, Asian'
                WHEN [race] = 'Asian or Pacific Islander' THEN 'Non-Hispanic, Asian'
                WHEN [race] = 'Black or African American' THEN 'Non-Hispanic, Black'
                WHEN [race] = 'American Indian or Alaska Native' THEN 'Non-Hispanic, American Indian or Alaska Native'
                WHEN [race] = 'More than one race' THEN 'Non-Hispanic, Two or More Races'
                WHEN [race] = 'White' THEN 'Non-Hispanic, White'
                WHEN [race] = 'Native Hawaiian or Other Pacific Islander' THEN 'Non-Hispanic, Hawaiian or Pacific Islander'
                -- "All Races" values are used only before 2020 as a placeholder
                -- For "Non-Hispanic, Two or More Races" and "Non-Hispanic, Hawaiian or Pacific Islander"
                WHEN [product] = '2007-2019' AND [race] = 'All Races' THEN 'All Races'
                ELSE [race]
            END AS [ethnicity]
            -- Source rates are expressed per 1,000 women 
            -- (e.g., 50 births / 1,000 women = 0.05, but displayed as 50)
            -- Divide by 1000 to convert back to decimal proportion
            ,[rate] / 1000.0 AS [rate]
        FROM [socioec_data].[vital_statistics].[cdc_wonder_fertility] AS [fertility]
        -- For years >= 2022, actual race-specific files with sufficient data exist
        WHERE 
			[product] = @product
			-- Five year rolling sums used
			AND [period] = 'Five-Year'
            -- Births in there age categories are included in the inflation calculation
            AND [age] NOT IN ('Under 15 years', '45-49 years', '50 years and over')
            -- Birth from "Not Stated" records are included in the inflation calculation
            AND [hispanic_origin] != 'Not Stated' 
            AND [race] != 'Not Stated'
            AND [year] = @year
    ),
    [ethnicity_expanded] AS (
        SELECT 
            [location]
            ,[age_group]
            ,[ethnicity]
            ,[rate]
        FROM [data]
        WHERE [ethnicity] != 'All Races'
        -- Following UNION statements use the "All Races"
        -- To create "Non-Hispanic, Two or More Races" and "Non-Hispanic, Hawaiian or Pacific Islander"
        UNION ALL

        SELECT
            [location]
            ,[age_group]
            ,'Non-Hispanic, Two or More Races' AS [ethnicity]
            ,[rate]
        FROM [data]
        WHERE [ethnicity] = 'All Races' AND [year] <= 2019

        UNION ALL

        SELECT
            [location]
            ,[age_group]
            ,'Non-Hispanic, Hawaiian or Pacific Islander' AS [ethnicity]
            ,[rate]
        FROM [data]
        WHERE [ethnicity] = 'All Races' AND [year] <= 2019
    )
    SELECT 
        [location]
        ,[single_age].[age]
        ,'Female' AS [sex]
        ,[ethnicity]
        ,[rate]
    FROM [ethnicity_expanded]
    CROSS JOIN (
        VALUES 
            ('15-19 years', 15), ('15-19 years', 16), ('15-19 years', 17), ('15-19 years', 18), ('15-19 years', 19),
            ('20-24 years', 20), ('20-24 years', 21), ('20-24 years', 22), ('20-24 years', 23), ('20-24 years', 24),
            ('25-29 years', 25), ('25-29 years', 26), ('25-29 years', 27), ('25-29 years', 28), ('25-29 years', 29),
            ('30-34 years', 30), ('30-34 years', 31), ('30-34 years', 32), ('30-34 years', 33), ('30-34 years', 34),
            ('35-39 years', 35), ('35-39 years', 36), ('35-39 years', 37), ('35-39 years', 38), ('35-39 years', 39),
            ('40-44 years', 40), ('40-44 years', 41), ('40-44 years', 42), ('40-44 years', 43), ('40-44 years', 44)
    ) AS [single_age]([age_group], [age])
    WHERE 
        [ethnicity_expanded].[age_group] = [single_age].[age_group]
    ORDER BY 
        [location]
        ,[single_age].[age]
        ,[ethnicity] 
END;