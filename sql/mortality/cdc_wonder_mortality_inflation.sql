/* This query calculates the CDC WONDER mortality inflation factors that will be used to
inflate deaths. The inflation factor is calculated as 1 + (Not Stated Deaths / 
Stated Deaths) for each location and sex. 
*/

WITH [base] AS (
    SELECT [product]
          ,[location]
          ,[period]
          ,[year]
          ,[age]
          -- Convert sex to single character
          ,CASE [sex]
            WHEN 'Female' THEN 'F'
            WHEN 'Male' THEN 'M'
          END AS [sex]
          ,[hispanic_origin]
          -- Convert 2022+ San Diego County 5-year average deaths to annual deaths
          -- Population for 2022+ county level is suppressed and will be replaced
          -- with yearly CCM population estimates which require annual death counts to
          -- calculate rates
          ,CASE 
            WHEN [year] >= 2022 and [location] = 'San Diego County' THEN [deaths] / 5
            ELSE [deaths] / 1
          END AS [deaths]
          ,[pop]
      FROM [socioec_data].[vital_statistics].[cdc_wonder_mortality]
-- Create Not Stated deaths
), [not_stated] AS (
    SELECT 
        [location]
        ,[sex]
        ,SUM([deaths]) AS [deaths] 
    FROM [base]
    WHERE [hispanic_origin] = 'Not Stated' OR [age] = 'Not Stated'
    GROUP BY [location], [sex]
-- Create Stated deaths
), [stated] AS (
    SELECT 
        [location]
        ,[sex]
        ,SUM([deaths]) AS [deaths] 
    FROM [base]
    WHERE [age] = 'All Stated Ages'
    GROUP BY [location], [sex]
-- Create inflation factor
) SELECT 
    [not_stated].[location]
    ,[not_stated].[sex]
    ,1 + ([not_stated].[deaths] / [stated].[deaths]) AS inflation_factor
FROM 
(SELECT * FROM [not_stated]) AS [not_stated]
LEFT JOIN (SELECT * FROM [stated]) AS [stated] ON [stated].[location] = [not_stated].[location] AND [stated].[sex] = [not_stated].[sex]
