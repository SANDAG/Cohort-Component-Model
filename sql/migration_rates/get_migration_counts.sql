/* 
Calculate in/out migration counts by age group, sex, and race/ethnicity for San Diego County.

Using the ACS 5-year PUMS, in/out migration counts are calculated within SANDAG
Estimates Program age groups, sex, and race/ethnicity categories. The "Group
Quarters - Military" and "Group Quarters - Institutional Correctional
Facilities" populations are excluded as these populations are held constant
for the duration of the forecast.

The ACS 5-year PUMS changes both field names and definitions through the years
that impact the calculations of in/out migration counts. These field name and
definition changes are listed below for ACS 5-year PUMS from 2006-2010 to
2020-2024.

2006-2010 and 2007-2011
  - Pre-2012 PUMS files do not contain the [DIS] field used to identify "Group
  Quarters - Institutional Correctional Facilities" requiring the use of the
  2008-2012 PUMS. See https://github.com/SANDAG/Estimates-Program/issues/203.
  - All other differences not tracked due to use of 2008-2012 PUMS.

2008-2012 to 2011-2015
  - Uses [RELP] = 16 to identify the "Institutionalized group quarters population"
  - Uses [RELP] = 17 to identify the "Noninstitutionalized group quarters population"
  - Has both [PUMA00] and [PUMA10] fields to denote PUMA of residence depending on survey year
  - Has both [MIGPUMA00] and [MIGPUMA10] fields to denote migration PUMA depending on survey year
  - Has both [MIGSP05] and [MIGSP12] field to denote State or foreign country code depending on survey year

2012-2016 to 2014-2018
  - Uses [RELP] = 16 to identify the "Institutionalized group quarters population"
  - Uses [RELP] = 17 to identify the "Noninstitutionalized group quarters population"
  - Uses just [PUMA] (2010 geography) to denote PUMA of residence
  - Uses just [MIGPUMA] (2010 geography) to denote migration PUMA
  - Uses [MIGSP] to denote State or foreign country code

2015-2019 to 2017-2021
  - Uses [RELSHIPP] = 37 to identify the "Institutionalized group quarters population"
  - Uses [RELSHIPP] = 38 to identify the "Noninstitutionalized group quarters population"
  - Uses just [PUMA] (2010 geography) to denote PUMA of residence
  - Uses just [MIGPUMA] (2010 geography) to denote migration PUMA
  - Uses [MIGSP] to denote State or foreign country code

2018-2022
  - Uses [RELSHIPP] = 37 to identify the "Institutionalized group quarters population"
  - Uses [RELSHIPP] = 38 to identify the "Noninstitutionalized group quarters population"
  - Has both [PUMA10] and [PUMA20] fields to denote PUMA of residence depending on survey year
  - Has both [MIGPUMA10] and [MIGPUMA20] fields to denote migration PUMA depending on survey year
  - Uses [MIGSP] to denote State or foreign country code

2019-2023 to 2020-2024
  - Uses [RELSHIPP] = 37 to identify the "Institutionalized group quarters population"
  - Uses [RELSHIPP] = 38 to identify the "Noninstitutionalized group quarters population"
  - Uses just [PUMA] (2020 geography) to denote PUMA of residence
  - Uses just [MIGPUMA] (2020 geography) to denote migration PUMA
  - Uses [MIGSP] to denote State or foreign country code
  - Renamed the [ST] field to [STATE]
*/
SET NOCOUNT ON;
-- Initialize parameters -----------------------------------------------------
DECLARE @year INTEGER = :year;
IF @year IN (2010, 2011) SET @year = 2012;  -- Pre-2012 PUMS files cannot be used (see header)
DECLARE @pums_5yr NVARCHAR(9) = CONCAT(CONVERT(NVARCHAR, @year-4), '_', CONVERT(NVARCHAR, @year))
DECLARE @msg nvarchar(45) = 'ACS 5-Year PUMS does not exist';
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
    -- Create tables storing San Diego County PUMA geographies -------------------
    DROP TABLE IF EXISTS [#PUMA00];
    SELECT [PUMA00]
    INTO [#PUMA00]
    FROM ( 
	    VALUES
		    ('08101'),('08102'),('08103'),('08104'),('08105'),('08106'),
		    ('08107'),('08108'),('08109'),('08110'),('08111'),('08112'),
		    ('08113'),('08114'),('08115'),('08116')
    ) AS [tt] ([PUMA00])

    DROP TABLE IF EXISTS [#PUMA10];
    SELECT [PUMA10]
    INTO [#PUMA10]
    FROM ( 
	    VALUES
		    ('07301'),('07302'),('07303'),('07304'),('07305'),('07306'),
		    ('07307'),('07308'),('07309'),('07310'),('07311'),('07312'),
		    ('07313'),('07314'),('07315'),('07316'),('07317'),('07318'),
		    ('07319'),('07320'),('07321'),('07322')
    ) AS [tt] ([PUMA10])

    DROP TABLE IF EXISTS [#PUMA20];
    SELECT [PUMA20]
    INTO [#PUMA20]
    FROM ( 
	    VALUES
		    ('07301'),('07302'),('07306'),('07307'),('07308'),('07310'),
		    ('07311'),('07312'),('07313'),('07314'),('07315'),('07316'),
		    ('07317'),('07322'),('07323'),('07324'),('07325'),('07326'),
		    ('07327'),('07328'),('07329'),('07330')
    ) AS [tt] ([PUMA20])


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


    -- Select desired 5-year ACS PUMS ----------------------------------------
    -- Create temporary table storing ACS PUMS persons fields for migrants
    DROP TABLE IF EXISTS [#pums_migrants_tbl];
    CREATE TABLE [#pums_migrants_tbl] (
        [SERIALNO] varchar(13) NOT NULL,
        [SPORDER] float NOT NULL,
        [STATE] varchar(2) NOT NULL,
        [PUMA00] varchar(5) NULL,
        [PUMA10] varchar(5) NULL,
        [PUMA20] varchar(5) NULL,
        [AGEP] int NOT NULL,
        [SEX] varchar(1) NOT NULL,
        [HISP] varchar(2) NOT NULL,
        [RAC1P] varchar(1) NOT NULL,
        [DIS] varchar(1) NOT NULL,
        [MIL] varchar(1) NULL,
        [MIGSP05] varchar(3) NULL,
        [MIGSP12] varchar(3) NULL,
        [MIGSP] varchar(3) NULL,
        [MIGPUMA00] varchar(5) NULL,
        [MIGPUMA10] varchar(5) NULL,
        [MIGPUMA20] varchar(5) NULL,
        [RELP] varchar(2) NULL,
        [RELSHIPP] varchar(2) NULL,
        [PWGTP] float NOT NULL,
        PRIMARY KEY ([SERIALNO], [SPORDER])
    );

    -- Build ACS PUMS query based on year and filter to migrants using [MIG] field
    DECLARE @pums_qry nvarchar(max) =
        CASE 
            WHEN @year BETWEEN 2012 AND 2015 THEN 'SELECT [SERIALNO], [SPORDER], [ST] AS [STATE], [PUMA00], [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [DIS], [MIL], [MIGSP05], [MIGSP12], NULL AS [MIGSP], [MIGPUMA00], [MIGPUMA10], NULL AS [MIGPUMA20], [RELP], NULL AS [RELSHIPP], [PWGTP] FROM [acs].[pums].[5y_' + @pums_5yr + '_persons] WHERE [MIG] IN (''2'', ''3'')'
            WHEN @year BETWEEN 2016 AND 2018 THEN 'SELECT [SERIALNO], [SPORDER], [ST] AS [STATE], NULL AS [PUMA00], [PUMA] AS [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [DIS], [MIL], NULL AS [MIGSP05], NULL AS [MIGSP12], [MIGSP], NULL AS [MIGPUMA00], [MIGPUMA] AS [MIGPUMA10], NULL AS [MIGPUMA20], [RELP], NULL AS [RELSHIPP], [PWGTP] FROM [acs].[pums].[5y_' + @pums_5yr + '_persons] WHERE [MIG] IN (''2'', ''3'')'
            WHEN @year BETWEEN 2019 AND 2021 THEN 'SELECT [SERIALNO], [SPORDER], [ST] AS [STATE], NULL AS [PUMA00], [PUMA] AS [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [DIS], [MIL], NULL AS [MIGSP05], NULL AS [MIGSP12], [MIGSP], NULL AS [MIGPUMA00], [MIGPUMA] AS [MIGPUMA10], NULL AS [MIGPUMA20], NULL AS [RELP], [RELSHIPP], [PWGTP] FROM [acs].[pums].[5y_' + @pums_5yr + '_persons] WHERE [MIG] IN (''2'', ''3'')'
            WHEN @year = 2022 THEN 'SELECT [SERIALNO], [SPORDER], [ST] AS [STATE], NULL AS [PUMA00], [PUMA10], [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [DIS], [MIL], NULL AS [MIGSP05], NULL AS [MIGSP12], [MIGSP], NULL AS [MIGPUMA00], [MIGPUMA10], [MIGPUMA20], NULL AS [RELP], [RELSHIPP], [PWGTP] FROM [acs].[pums].[5y_' + @pums_5yr + '_persons] WHERE [MIG] IN (''2'', ''3'')'
            WHEN @year BETWEEN 2023 AND @max_year THEN 'SELECT [SERIALNO], [SPORDER], [STATE], NULL AS [PUMA00], NULL AS [PUMA10], [PUMA] AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [DIS], [MIL], NULL AS [MIGSP05], NULL AS [MIGSP12], [MIGSP], NULL AS [MIGPUMA00], NULL AS [MIGPUMA10], [MIGPUMA] AS [MIGPUMA20], NULL AS [RELP], [RELSHIPP], [PWGTP] FROM [acs].[pums].[5y_' + @pums_5yr + '_persons] WHERE [MIG] IN (''2'', ''3'')'
            ELSE NULL
        END

    -- Insert ACS PUMS query results for migrants into table
    INSERT INTO [#pums_migrants_tbl]
    EXECUTE sp_executesql @pums_qry;


    -- Calculate Ins/Outs by age group, sex, and race/ethnicity --------------
    WITH [migrants] AS (
        SELECT
            [age_group].[name] AS [age_group],
            CASE
                WHEN [SEX] = '1' THEN 'Male'
                WHEN [SEX] = '2' THEN 'Female'
                ELSE NULL
            END AS [sex],  -- Change numeric codes into standard text codes.
            CASE
                WHEN [HISP] NOT IN ('01', '1') THEN 'Hispanic' -- Exclude non-Hispanic which is 01 or 1.  Hispanic takes precedence over race
                WHEN [RAC1P] IN ('1', '8') THEN 'Non-Hispanic, White' -- Combine Some other race with White
                WHEN [RAC1P] = '2' THEN 'Non-Hispanic, Black'
                WHEN [RAC1P] IN ('3', '4', '5') THEN 'Non-Hispanic, American Indian or Alaska Native'  -- Group various codes for AI and AN together
                WHEN [RAC1P] = '6' THEN 'Non-Hispanic, Asian'
                WHEN [RAC1P] = '7' THEN 'Non-Hispanic, Hawaiian or Pacific Islander'
                WHEN [RAC1P] = '9' THEN 'Non-Hispanic, Two or More Races'
                ELSE NULL
            END AS [ethnicity],
            -- Identify in-migrants into San Diego County
            CASE
                -- Census 2020 geographies using [MIGSP] applies to ACS PUMS 5-years from 2018-2022 (partially) and onwards (fully)
                WHEN ([MIGSP] NOT IN ('006', '6') OR ([MIGSP] IN ('006', '6') AND [MIGPUMA20] != '07300'))  -- Migrated from outside California, or from within California but from outside San Diego County
                    AND [STATE] = '06' AND [PUMA20] IN (SELECT [PUMA20] FROM [#PUMA20])  -- Currently reside in San Diego County, defined by state being California and PUMA of residence being in a list of San Diego County PUMAs
                THEN [PWGTP]

                -- Census 2010 geographies using [MIGSP] applies to ACS PUMS 5-years from 2012-2016 to 2017-2021 (fully) as well as 2018-2022 (partially)
                WHEN ([MIGSP] NOT IN ('006', '6') OR ([MIGSP] IN ('006', '6') AND [MIGPUMA10] != '07300'))  -- Migrated from outside California, or from within California but from outside San Diego County
                    AND [STATE] = '06' AND [PUMA10] IN (SELECT [PUMA10] FROM [#PUMA10])  -- Currently reside in San Diego County, defined by state being California and PUMA of residence being in a list of San Diego County PUMAs
                THEN [PWGTP]

                -- Census 2010 geographies using [MIGSP12] applies to ACS PUMS 5-years 2008-2012 to 2011-2015 (partially)
                WHEN ([MIGSP12] NOT IN ('006', '6') OR ([MIGSP12] IN ('006', '6') AND [MIGPUMA10] != '07300'))  -- Migrated from outside California, or from within California but from outside San Diego County
                    AND [STATE] = '06' AND [PUMA10] IN (SELECT [PUMA10] FROM [#PUMA10])  -- Currently reside in San Diego County, defined by state being California and PUMA of residence being in a list of San Diego County PUMAs
                 THEN [PWGTP]

                -- Census 2000 geographies using [MIGSP05] applies to ACS PUMS 5-years 2008-2012 to 2011-2015 (partially)
                WHEN ([MIGSP05] NOT IN ('006', '6') OR ([MIGSP05] IN ('006', '6') AND [MIGPUMA00] != '081'))  -- Migrated from outside California, or from within California but from outside San Diego County
                    AND [STATE] = '06' AND [PUMA00] IN (SELECT [PUMA00] FROM [#PUMA00])  -- Currently reside in San Diego County, defined by state being California and PUMA of residence being in a list of San Diego County PUMAs
                THEN [PWGTP]

                ELSE 0
            END AS [in],

            -- Identify out-migrants from San Diego County
            CASE
                -- Census 2020 geographies using [MIGSP] applies to ACS PUMS 5-years from 2018-2022 (partially) and onwards (fully)
                WHEN [MIGSP] IN ('006', '6') AND [MIGPUMA20] = '07300'  -- Migrated from San Diego County, defined by migration state being California and migration PUMA being the code for San Diego County
                    AND ([STATE] != '06' OR ([STATE] = '06' AND [PUMA20] NOT IN (SELECT [PUMA20] FROM [#PUMA20])))  -- Currently reside not in San Diego County, defined by state being not California and PUMA of residence being not in a list of San Diego County PUMAs
                THEN [PWGTP]

                -- Census 2010 geographies using [MIGSP] applies to ACS PUMS 5-years from 2012-2016 to 2017-2021 (fully) as well as 2018-2022 (partially)
                WHEN [MIGSP] IN ('006', '6') AND [MIGPUMA10] = '07300'  -- Migrated from San Diego County, defined by migration state being California and migration PUMA being the code for San Diego County
                    AND ([STATE] != '06' OR ([STATE] = '06' AND [PUMA10] NOT IN (SELECT [PUMA10] FROM [#PUMA10])))  -- Currently reside not in San Diego County, defined by state being not California and PUMA of residence being not in a list of San Diego County PUMAs
                THEN [PWGTP]

                -- Census 2010 geographies using [MIGSP12] applies to ACS PUMS 5-years 2008-2012 to 2011-2015 (partially)
                WHEN [MIGSP12] IN ('006', '6') AND [MIGPUMA10] = '07300'  -- Migrated from San Diego County, defined by migration state being California and migration PUMA being the code for San Diego County
                    AND ([STATE] != '06' OR ([STATE] = '06' AND [PUMA10] NOT IN (SELECT [PUMA10] FROM [#PUMA10])))  -- Currently reside not in San Diego County, defined by state being not California and PUMA of residence being not in a list of San Diego County PUMAs
                THEN [PWGTP]

                -- Census 2000 geographies using [MIGSP05] applies to ACS PUMS 5-years 2008-2012 to 2011-2015 (partially)
                WHEN [MIGSP05] IN ('006', '6') AND [MIGPUMA00] = '081'  -- Migrated from San Diego County, defined by migration state being California and migration PUMA being the code for San Diego County
                    AND ([STATE] != '06' OR ([STATE] = '06' AND [PUMA00] NOT IN (SELECT [PUMA00] FROM [#PUMA00])))  -- Currently reside not in San Diego County, defined by state being not California and PUMA of residence being not in a list of San Diego County PUMAs
                THEN [PWGTP]

                ELSE 0
            END AS [out]
        FROM [#pums_migrants_tbl]
        INNER JOIN [demographic_warehouse].[dim].[age_group]
            ON [#pums_migrants_tbl].[AGEP] BETWEEN [age_group].[lower_bound] AND [age_group].[upper_bound]
            OR ([#pums_migrants_tbl].[AGEP] > 99 AND [age_group].[name] = '85 and Older')
        WHERE 
            -- Remove "Group Quarters - Military"
            NOT ([MIL] = 1 AND ((@year BETWEEN 2012 AND 2018 AND [RELP] = '17') OR (@year > 2018 AND [RELSHIPP] = '38')))
            -- Remove "Group Quarters - Institutional Correctional Facilities
            AND NOT ([DIS] = '2' AND [AGEP] >= 10 AND ((@year BETWEEN 2012 AND 2018 AND [RELP] = '16') OR (@year > 2018 AND [RELSHIPP] = '37')))
    )
    SELECT
        [age_group],
        [sex],
        [ethnicity],
        SUM([in]) AS [in],
        SUM([out]) AS [out]
    FROM [migrants]
    GROUP BY [age_group], [sex], [ethnicity]
    ORDER BY [age_group], [sex], [ethnicity]

END