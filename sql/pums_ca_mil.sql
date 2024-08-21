-- Get the total State of California active-duty military population
WITH [pums_persons] AS (
-- All 5-year ACS PUMS persons datasets from 2006-2010 to 2018-2022				
    SELECT 2010 AS [year], [ST], [MIL], [PWGTP] FROM [acs].[pums].[5y_2006_2010_persons]
        UNION ALL
    SELECT 2011 AS [year], [ST], [MIL], [PWGTP] FROM [acs].[pums].[5y_2007_2011_persons]
        UNION ALL
    SELECT 2012 AS [year], [ST], [MIL], [PWGTP] FROM [acs].[pums].[5y_2008_2012_persons]
        UNION ALL
    SELECT 2013 AS [year], [ST], [MIL], [PWGTP] FROM [acs].[pums].[5y_2009_2013_persons]
        UNION ALL
    SELECT 2014 AS [year], [ST], [MIL], [PWGTP] FROM [acs].[pums].[5y_2010_2014_persons]
        UNION ALL
    SELECT 2015 AS [year], [ST], [MIL], [PWGTP] FROM [acs].[pums].[5y_2011_2015_persons]
        UNION ALL
    SELECT 2016 AS [year], [ST], [MIL], [PWGTP] FROM [acs].[pums].[5y_2012_2016_persons]
        UNION ALL
    SELECT 2017 AS [year], [ST], [MIL], [PWGTP] FROM [acs].[pums].[5y_2013_2017_persons]
        UNION ALL
    SELECT 2018 AS [year], [ST], [MIL], [PWGTP] FROM [acs].[pums].[5y_2014_2018_persons]
        UNION ALL
    SELECT 2019 AS [year], [ST], [MIL], [PWGTP] FROM [acs].[pums].[5y_2015_2019_persons]
        UNION ALL
    SELECT 2020 AS [year], [ST], [MIL], [PWGTP] FROM [acs].[pums].[5y_2016_2020_persons]
        UNION ALL
    SELECT 2021 AS [year], [ST], [MIL], [PWGTP] FROM [acs].[pums].[5y_2017_2021_persons]
        UNION ALL
    SELECT 2022 AS [year], [ST], [MIL], [PWGTP] FROM [acs].[pums].[5y_2018_2022_persons]
    )
SELECT [year], SUM([PWGTP]) AS [pop_ca_mil]
FROM [pums_persons]
WHERE [ST] = '06' AND MIL = '1'
GROUP BY [year]
ORDER BY [year]