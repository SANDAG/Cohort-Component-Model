/* This query loads and prepares the CDC WONDER mortality data for the given year by 
renaming fields to match the CCM fields, removing "Not Stated" rows, and supplementing 
data to create new race categories for years 2020 and earlier.
*/

DECLARE @year INTEGER;

BEGIN

-- Add check with THROW statement if the year provided does not exist in the dataset
IF NOT EXISTS (SELECT 1 FROM [socioec_data].[vital_statistics].[cdc_wonder_mortality] WHERE [year] = @year)
    THROW 50002, 'The provided year does not exist in the CDC WONDER mortality dataset', 1

END;


WITH [base] AS (
    SELECT [product]
          ,[location]
          ,[period]
          ,[year]
          -- Convert age to numeric
          ,CASE [age]
          WHEN '85+' THEN '85'
            ELSE [age]
          END AS [age]
          -- Convert sex to single character
          ,CASE [sex]
            WHEN 'Female' THEN 'F'
            WHEN 'Male' THEN 'M'
          END AS [sex]
          ,[hispanic_origin]
          -- Convert races categories
          ,CASE 
            WHEN [hispanic_origin] = 'Hispanic or Latino' THEN 'Hispanic'
            WHEN [race] = 'Asian' THEN 'Asian alone'
            WHEN [race] = 'Asian or Pacific Islander' THEN 'Asian alone'
            WHEN [race] = 'Black or African American' THEN 'Black or African American alone'
            WHEN [race] = 'American Indian or Alaska Native' THEN 'American Indian or Alaska Native alone'
            WHEN [race] = 'More than one race' THEN 'Two or More Races'
            WHEN [race] = 'White' THEN 'White alone'
            WHEN [race] = 'Native Hawaiian or Other Pacific Islander' THEN 'Native Hawaiian or Other Pacific Islander alone'
            -- Duplicate race categories for 2020 and earlier
            WHEN [year] <= 2020 AND [mortality].[race] = 'All Races' THEN [splitter].[new_race]
            ELSE [race]
          END AS [race]
          -- Convert 2022+ San Diego County 5-year average deaths to annual deaths
          -- Population for 2022+ county level is suppressed and will be replaced
          -- with yearly CCM population estimates which require annual death counts to
          -- calculate rates
          ,CASE 
            WHEN [year] >= 2022 and [location] = 'San Diego County' THEN [deaths] / 5
            ELSE [deaths] / 1
          END AS [deaths]
          ,[pop]
      FROM [socioec_data].[vital_statistics].[cdc_wonder_mortality] AS [mortality]
      -- Duplicate 'All Races' records into NHPI and MOR for years <= 2020 only
      -- For years >= 2022, actual race-specific files with sufficient data exist
      LEFT JOIN (
          VALUES 
            ('Native Hawaiian or Other Pacific Islander alone'),
            ('Two or More Races')
      ) AS [splitter]([new_race]) ON [mortality].[year] <= 2020 AND [mortality].[race] = 'All Races' AND [mortality].[hispanic_origin] != 'Hispanic or Latino'
      WHERE [age] NOT IN ('Not Stated', 'All Stated Ages') AND [hispanic_origin] != 'Not Stated' 
) SELECT 
    [product]
    ,[location]
    ,[period]
    ,[year]
    ,[age]
    ,[sex]
    ,[hispanic_origin]
    ,[race]
    ,[deaths]
    ,[pop]
FROM [base]
WHERE [race] != 'All Races' AND [year] = @year
ORDER BY [product], [location], [year], [age], [sex], [hispanic_origin], [race] 