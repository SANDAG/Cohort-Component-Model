/*
Get household characteristics for San Diego County by age group, sex, and ethnicity.

Rates are calculated directly from the 5-year ACS PUMS mapping single of year
of age to SANDAG age groups used in SANDAG's Estimates Program. The rates are
assigned to age group, sex, and ethnicity categories using the head of
household's demographic characteristics.

This data is used as initial values that are controlled such that, when applied
to launch year households, the totals match totals from SANDAG's Estimates
Program.

Note this script must be run in the production Estimates Program database.
*/

SET NOCOUNT ON;
-- Initialize parameters -----------------------------------------------------
DECLARE @run_id INTEGER = :run_id;
DECLARE @year integer = :year;
DECLARE @msg nvarchar(45) = 'ACS 5-Year PUMS does not exist';
DECLARE @pums nvarchar(10) = CONCAT(
	CONVERT(NVARCHAR(4), @year-4), '_', CONVERT(NVARCHAR(4), @year)
)

-- Send error message if no data exists --------------------------------------
IF OBJECT_ID('acs.pums.vi_5y_' + @pums + '_households_sd', 'V') IS NULL
    OR OBJECT_ID('acs.pums.vi_5y_' + @pums + '_persons_sd', 'V') IS NULL
SELECT @msg AS [msg]
ELSE
BEGIN
    -- Calculate household characteristics rates from ACS PUMS ---------------
    DECLARE @query NVARCHAR(max) = '
        SELECT
            [estimates_groups].[age_group],
            [estimates_groups].[sex],
            [estimates_groups].[ethnicity],
            ISNULL(SUM([hh_size1]) / NULLIF(SUM([PWGTP]), 0), 0) AS [rate_hh_size1],
            ISNULL(SUM([hh_size2]) / NULLIF(SUM([PWGTP]), 0), 0) AS [rate_hh_size2],
            ISNULL(SUM([hh_size3]) / NULLIF(SUM([PWGTP]), 0), 0) AS [rate_hh_size3],
            ISNULL(SUM([hh_workers0]) / NULLIF(SUM([PWGTP]), 0), 0) AS [rate_hh_workers0],
            ISNULL(SUM([hh_workers1]) / NULLIF(SUM([PWGTP]), 0), 0) AS [rate_hh_workers1],
            ISNULL(SUM([hh_workers2]) / NULLIF(SUM([PWGTP]), 0), 0) AS [rate_hh_workers2],
            ISNULL(SUM([hh_workers3]) / NULLIF(SUM([PWGTP]), 0), 0) AS [rate_hh_workers3],
            ISNULL(SUM([hh_head_lf]) / NULLIF(SUM([PWGTP]), 0), 0) AS [rate_hh_head_lf],
            ISNULL(SUM([hh_children]) / NULLIF(SUM([PWGTP]), 0), 0) AS [rate_hh_children],
            ISNULL(SUM([hh_seniors]) / NULLIF(SUM([PWGTP]), 0), 0) AS [rate_hh_seniors]
        FROM (
            SELECT DISTINCT
                [age_group],
                [sex],
                [ethnicity]
            FROM [inputs].[controls_ase]
            WHERE [run_id] = ' + CONVERT(NVARCHAR(max), @run_id) + '
                AND [year] = ' + CONVERT(NVARCHAR(max), @year) + '
        ) AS [estimates_groups]
        LEFT OUTER JOIN (
            SELECT
                [age_group].[name] AS [age_group],  -- Group oldest ages into one category, if over 99 as 99, otherwise keep single year of age
                CASE WHEN [SEX] = ''1'' THEN ''Male'' WHEN [SEX] = ''2'' THEN ''Female'' ELSE NULL END AS [sex],  -- Change numeric codes into standard text codes.
                CASE WHEN [HISP] NOT IN (''01'', ''1'') THEN ''Hispanic'' -- Exclude non-Hispanic which is 01 or 1.  Hispanic takes precendence over Race
                        WHEN [RAC1P] IN (''1'', ''8'') THEN ''Non-Hispanic, White'' -- Combine Some other race with White
                        WHEN [RAC1P] = ''2'' THEN ''Non-Hispanic, Black''
                        WHEN [RAC1P] IN (''3'', ''4'', ''5'') THEN ''Non-Hispanic, American Indian or Alaska Native''  -- Group various codes for AI and AN together
                        WHEN [RAC1P] = ''6'' THEN ''Non-Hispanic, Asian''
                        WHEN [RAC1P] = ''7'' THEN ''Non-Hispanic, Hawaiian or Pacific Islander''
                        WHEN [RAC1P] = ''9'' THEN ''Non-Hispanic, Two or More Races''
                        ELSE NULL END AS [ethnicity],
                [PWGTP],  -- [SPORDER]=1 filter makes this equivalent to household weight
                CASE WHEN [NP] = 1 THEN [PWGTP] ELSE 0 END AS [hh_size1],
                CASE WHEN [NP] = 2 THEN [PWGTP] ELSE 0 END AS [hh_size2],
                CASE WHEN [NP] >= 3 THEN [PWGTP] ELSE 0 END AS [hh_size3],
                CASE WHEN [hh_workers] = 0 THEN [PWGTP] ELSE 0 END AS [hh_workers0],
                CASE WHEN [hh_workers] = 1 THEN [PWGTP] ELSE 0 END AS [hh_workers1],
                CASE WHEN [hh_workers] = 2 THEN [PWGTP] ELSE 0 END AS [hh_workers2],
                CASE WHEN [hh_workers] >= 3 THEN [PWGTP] ELSE 0 END AS [hh_workers3],
                CASE WHEN [ESR] IN (1,2,3,4,5) THEN [PWGTP] ELSE 0 END AS [hh_head_lf],
                CASE WHEN [hh_children] = 1 THEN [PWGTP] ELSE 0 END AS [hh_children],
                CASE WHEN [hh_seniors] = 1 THEN [PWGTP] ELSE 0 END AS [hh_seniors]
            FROM [acs].[pums].[vi_5y_' + @pums + '_households_sd] AS [households]
            INNER JOIN [acs].[pums].[vi_5y_' + @pums + '_persons_sd] AS [persons]
                ON [households].[SERIALNO] = [persons].[SERIALNO]
            INNER JOIN (
                SELECT
                    [SERIALNO],
                    SUM(CASE WHEN [ESR] IN (1,2,4,5) THEN 1 ELSE 0 END) AS [hh_workers],  -- Exclude unemployed (3) or not in labor force (6)
                    MAX(CASE WHEN [AGEP] < 18 THEN 1 ELSE 0 END) AS [hh_children],
                    MAX(CASE WHEN [AGEP] >= 65 THEN 1 ELSE 0 END) AS [hh_seniors]
                FROM [acs].[pums].[vi_5y_' + @pums + '_persons_sd]
                GROUP BY [SERIALNO]
            ) AS [hh_info]
                ON [households].[SERIALNO] = [hh_info].[SERIALNO]
            INNER JOIN [demographic_warehouse].[dim].[age_group]
                ON [persons].[AGEP] BETWEEN [age_group].[lower_bound] AND [age_group].[upper_bound]
                OR ([persons].[AGEP] > 99 AND [age_group].[name] = ''85 and Older'')
            WHERE [WGTP] > 0  -- Remove Group Quarters records
                AND [SPORDER] = 1  -- Household heads only
        ) AS [acs_persons]
            ON [estimates_groups].[age_group] = [acs_persons].[age_group]
            AND [estimates_groups].[sex] = [acs_persons].[sex]
            AND [estimates_groups].[ethnicity] = [acs_persons].[ethnicity]
        GROUP BY
            [estimates_groups].[age_group],
            [estimates_groups].[sex],
            [estimates_groups].[ethnicity]
        ORDER BY
            [estimates_groups].[age_group],
            [estimates_groups].[sex],
            [estimates_groups].[ethnicity]
    '

    EXECUTE sp_executesql @query
END