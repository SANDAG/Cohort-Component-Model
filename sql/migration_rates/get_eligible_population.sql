/*
Calculate San Diego migration-eligible resident population by age group, sex, and race/ethnicity for San Diego County.

Using the ACS 5-year PUMS, migration eligible residents are calculated within
SANDAG Estimates Program age groups, sex, and race/ethnicity categories. The
"Group Quarters - Military" and "Group Quarters - Institutional Correctional
Facilities" populations are excluded as these populations are held constant
for the duration of the forecast.
*/

SET NOCOUNT ON;
-- Initialize parameters -----------------------------------------------------
DECLARE @year INTEGER = :year;
IF @year IN (2010, 2011) SET @year = 2012;  -- Pre-2012 PUMS files cannot be used (see migration in/out counts SQL)
DECLARE @pums_5yr NVARCHAR(9) = CONCAT(CONVERT(NVARCHAR, @year-4), '_', CONVERT(NVARCHAR, @year))
DECLARE @msg nvarchar(45) = 'PUMS 5-Year does not exist';
-- Maximum 5-Year PUMS data that has been reviewed and incorporated
-- Field definitions may change so new releases must be reviewed
DECLARE @max_year integer = 2024


-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [acs].[INFORMATION_SCHEMA].[TABLES] 
    WHERE
        [TABLE_SCHEMA] = 'pums' 
        AND [TABLE_NAME] = '5y_' + @pums_5yr + '_persons'
)
SELECT @msg AS [msg]
ELSE IF @year > @max_year
BEGIN
    THROW 50000, 'PUMS data exists but has not been reviewed', 1;
END
ELSE
BEGIN

    -- Create shell table of required categories -----------------------------
    DROP TABLE IF EXISTS [#tt_shell];
    WITH [age_group] AS (
        SELECT [age_group] FROM (
            VALUES
                ('Under 5'),
                ('5 to 9'),
                ('10 to 14'),
                ('15 to 17'),
                ('18 and 19'),
                ('20 to 24'),
                ('25 to 29'),
                ('30 to 34'),
                ('35 to 39'),
                ('40 to 44'),
                ('45 to 49'),
                ('50 to 54'),
                ('55 to 59'),
                ('60 and 61'),
                ('62 to 64'),
                ('65 to 69'),
                ('70 to 74'),
                ('75 to 79'),
                ('80 to 84'),
                ('85 and Older')
        ) AS [tt] ([age_group])
    ),
    [sex] AS (
        SELECT [sex] FROM (VALUES ('Female'), ('Male')) AS [tt] ([sex])
    ),
    [ethnicity] AS (
        SELECT [ethnicity] FROM (
            VALUES
                ('Hispanic'),
                ('Non-Hispanic, White'),
                ('Non-Hispanic, Black'),
                ('Non-Hispanic, American Indian or Alaska Native'),
                ('Non-Hispanic, Asian'),
                ('Non-Hispanic, Hawaiian or Pacific Islander'),
                ('Non-Hispanic, Two or More Races')
        ) AS [tt] ([ethnicity])
    )
    SELECT [age_group], [sex], [ethnicity]
    INTO [#tt_shell]
    FROM [age_group]
    CROSS JOIN [sex]
    CROSS JOIN [ethnicity];

    -- Calculate the migration-eligible resident population ------------------
    -- The 2008-2012 to 2014-2018 ACS 5-year PUMS use [RELP] to identify Group Quarters
    -- The 2015-2019 ACS 5-year PUMS and moving forward use [RELSHIPP] to identify Group Quarters
    DECLARE @gq_noninst NVARCHAR(MAX) = 
        CASE
            WHEN @year BETWEEN 2012 AND 2018 THEN '[RELP] = ''17'''
            WHEN @year > 2018 THEN '[RELSHIPP] = ''38'''
            ELSE NULL
        END

    DECLARE @gq_inst NVARCHAR(MAX) = 
        CASE
            WHEN @year BETWEEN 2012 AND 2018 THEN '[RELP] = ''16'''
            WHEN @year > 2018 THEN '[RELSHIPP] = ''37'''
            ELSE NULL
        END

    DECLARE @qry nvarchar(max) = '
        WITH [population] AS (
            SELECT
                [age_group],
                [sex],
                [ethnicity],
                SUM([PWGTP]) AS [pop]
            FROM (
                SELECT
                    [age_group].[name] AS [age_group],
                    CASE
                        WHEN [SEX] = ''1'' THEN ''Male''
                        WHEN [SEX] = ''2'' THEN ''Female''
                        ELSE NULL
                    END AS [sex],  -- Change numeric codes into standard text codes.
                    CASE
                        WHEN [HISP] NOT IN (''01'', ''1'') THEN ''Hispanic'' -- Exclude non-Hispanic which is 01 or 1.  Hispanic takes precedence over race
                        WHEN [RAC1P] IN (''1'', ''8'') THEN ''Non-Hispanic, White'' -- Combine Some other race with White
                        WHEN [RAC1P] = ''2'' THEN ''Non-Hispanic, Black''
                        WHEN [RAC1P] IN (''3'', ''4'', ''5'') THEN ''Non-Hispanic, American Indian or Alaska Native''  -- Group various codes for AI and AN together
                        WHEN [RAC1P] = ''6'' THEN ''Non-Hispanic, Asian''
                        WHEN [RAC1P] = ''7'' THEN ''Non-Hispanic, Hawaiian or Pacific Islander''
                        WHEN [RAC1P] = ''9'' THEN ''Non-Hispanic, Two or More Races''
                        ELSE NULL
                    END AS [ethnicity],
                    [PWGTP]
                FROM [acs].[pums].[vi_5y_' + @pums_5yr + '_persons_sd] AS [persons]
                INNER JOIN [demographic_warehouse].[dim].[age_group]
                    ON [persons].[AGEP] BETWEEN [age_group].[lower_bound] AND [age_group].[upper_bound]
                    OR ([persons].[AGEP] > 99 AND [age_group].[name] = ''85 and Older'')
                WHERE 
                    -- Remove "Group Quarters - Military"
                    NOT ([MIL] = 1 AND ' + @gq_noninst + ')
                    -- Remove "Group Quarters - Institutional Correctional Facilities"
                    AND NOT ([DIS] = ''2'' AND [AGEP] >= 10 AND ' + @gq_inst + ')
            ) AS [migration_eligble]
            GROUP BY [age_group], [sex], [ethnicity]
        )
        SELECT
            [#tt_shell].[age_group],
            [#tt_shell].[sex],
            [#tt_shell].[ethnicity],
            ISNULL([pop], 0) AS [pop]
        FROM [#tt_shell]
        LEFT OUTER JOIN [population]
            ON [#tt_shell].[age_group] = [population].[age_group]
            AND [#tt_shell].[sex] = [population].[sex]
            AND [#tt_shell].[ethnicity] = [population].[ethnicity]
        ORDER BY [#tt_shell].[age_group], [#tt_shell].[sex], [#tt_shell].[ethnicity]
    '

    EXECUTE sp_executesql @qry

END