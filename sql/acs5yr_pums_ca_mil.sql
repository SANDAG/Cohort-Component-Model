-- Get the total State of California active-duty military population
with
    [pums_persons]
    AS
    (
        -- all 5-year ACS PUMS persons datasets from 2006-2010 to 2017-2021
                                    SELECT 2018 AS [year], [ST], [MIL], [PWGTP]
            FROM [acs].[pums].[5y_2014_2018_persons]
        UNION ALL
            SELECT 2019 AS [year], [ST], [MIL], [PWGTP]
            FROM [acs].[pums].[5y_2015_2019_persons]
        UNION ALL
            SELECT 2020 AS [year], [ST], [MIL], [PWGTP]
            FROM [acs].[pums].[5y_2016_2020_persons]
        UNION ALL
            SELECT 2021 AS [year], [ST], [MIL], [PWGTP]
            FROM [acs].[pums].[5y_2017_2021_persons]
    )
SELECT [year], SUM([PWGTP]) AS [pop_ca_mil]
FROM [pums_persons]
WHERE [ST] = '06' AND MIL = '1'
GROUP BY [year]