/* 
    This query loads and prepares the CDC WONDER fertility data for the given year by 
    renaming fields to match the CCM fields, removing "Not Stated" rows, and supplementing 
    data to create new race categories for years 2020 and earlier.
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
    WHERE 
        [year] = @year
)
SELECT @msg AS [msg]
ELSE
BEGIN
    WITH [data] AS (
        SELECT [product]
            ,[location]
            ,[year]
            ,[age]
            ,[hispanic_origin]
            ,CASE 
                WHEN [hispanic_origin] = 'Hispanic or Latino' THEN 'Hispanic'
                WHEN [race] = 'Asian' THEN 'Asian alone'
                WHEN [race] = 'Asian or Pacific Islander' THEN 'Asian alone'
                WHEN [race] = 'Black or African American' THEN 'Black or African American alone'
                WHEN [race] = 'American Indian or Alaska Native' THEN 'American Indian or Alaska Native alone'
                WHEN [race] = 'More than one race' THEN 'Two or More Races'
                WHEN [race] = 'White' THEN 'White alone'
                WHEN [race] = 'Native Hawaiian or Other Pacific Islander' THEN 'Native Hawaiian or Other Pacific Islander alone'
                -- "All Races" values are used only before 2020 as a placeholder
                -- For "Two or More Races" and "Native Hawaiian or Other Pacific Islander alone"
                WHEN [product] = '2007-2019' AND [race] = 'All Races' THEN 'All Races'
                ELSE [race]
            END AS [race]
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
            AND [age] NOT IN ('Under 15 years', '45-49 years', '50 years and over')
            AND [hispanic_origin] != 'Not Stated' 
            AND [race] != 'Not Stated'
            AND [year] = @year
    ),
    [race_expanded] AS (
        SELECT 
            [location]
            ,[year]
            ,[age]
            ,[hispanic_origin]
            ,[race]
            ,[rate]
        FROM [data]
        WHERE [race] != 'All Races'
        -- Following UNION statements use the "All Races"
        -- To create "Two or More Races" and "Native Hawaiian or Other Pacific Islander alone"
        UNION ALL

        SELECT
            [location]
            ,[year]
            ,[age]
            ,[hispanic_origin]
            ,'Two or More Races' AS [race]
            ,[rate]
        FROM [data]
        WHERE [race] = 'All Races' AND [year] <= 2019

        UNION ALL

        SELECT
            [location]
            ,[year]
            ,[age]
            ,[hispanic_origin]
            ,'Native Hawaiian or Other Pacific Islander alone' AS [race]
            ,[rate]
        FROM [data]
        WHERE [race] = 'All Races' AND [year] <= 2019
    )
    SELECT 
        [location]
        ,[year]
        ,[single_age].[age_group]
        ,[single_age].[age]
        ,[hispanic_origin]
        ,[race]
        ,[rate]
    FROM [race_expanded]
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
        [race_expanded].[age] = [single_age].[age_group]
    ORDER BY 
        [location] 
        ,[year]
        ,[single_age].[age] 
        ,[hispanic_origin]
        ,[race] 
END;