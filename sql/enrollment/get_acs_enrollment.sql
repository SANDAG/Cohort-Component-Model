/*
Get school enrollment counts by single year of age for San Diego County.

The 5-year ACS PUMS is used to get school enrollment counts by single year of
age for San Diego County for enrollment categories. Enrollment categories are
age-restricted as the ACS PUMS is a self report survey wherein improbable
grade/age enrollment combinations are present to due to conflation with the
educational attainment question.

The group quarters population is excluded from the enrollment counts as we
assume all "Group Quarters - College" population is enrolled in the College+
category while all other group quarters populations are excluded from school
enrollment.

The age restrictions on enrollment categories are as follows:
    (T)K-4th - restricted to ages 4-11
    5th-8th - restricted to ages 8-15
    9th-12th - restricted to ages 12-19
    College+ - restricted to ages 15-50

Labels for Nursery school/preschool and Kindergarten persons are also returned,
restricted to 4 and 5 year olds, to allow for reallocation of Nursery school/
preschool persons into Kindergarten to account for persons enrolled in TK that
have misspecified themselves as being in Nursery school/preschool.
*/

SET NOCOUNT ON;
-- Initialize parameters -----------------------------------------------------
DECLARE @year integer = :year;
DECLARE @msg nvarchar(45) = 'ACS 5-Year PUMS does not exist';
DECLARE @pums nvarchar(10) = CONCAT(
	CONVERT(NVARCHAR(4), @year-4), '_', CONVERT(NVARCHAR(4), @year)
);
-- Maximum 5-Year PUMS data that has been reviewed and incorporated
-- Field definitions may change so new releases must be reviewed
DECLARE @max_year integer = 2024;

-- Send error message if no data exists --------------------------------------
IF OBJECT_ID('acs.pums.vi_5y_' + @pums + '_persons_sd', 'V') IS NULL
BEGIN
    SELECT @msg AS [msg]
END
ELSE IF @year > @max_year
BEGIN
    THROW 50000, 'PUMS data exists but has not been reviewed', 1;
END
ELSE
BEGIN
    -- Calculate enrollment from ACS PUMS ------------------------------------
    -- Filter to remove group quarters is ACS PUMS specific
    DECLARE @no_gq_filter NVARCHAR(MAX) = 
        CASE
            WHEN @year BETWEEN 2010 AND 2011 THEN '[RELP] NOT IN (''13'',''14'')'
            WHEN @year BETWEEN 2012 AND 2018 THEN '[RELP] NOT IN (''16'',''17'')'
            WHEN @year > 2018 THEN '[RELSHIPP] NOT IN (''37'',''38'')'
            ELSE NULL
        END;

    -- Filter to remove incompatible enrollment/age combinations is ACS PUMS specific
    DECLARE @enrollment_age_filter NVARCHAR(MAX) = 
        CASE
            WHEN @year BETWEEN 2010 AND 2011 THEN '
                -- Look at Nursery School for ages 4-5 as these may be TK (starting in 2023+)
                ([AGEP] BETWEEN 4 AND 5 AND [SCHG] IN (''1'',''2''))
                -- (T)K-4th restricted to ages 4-11
                OR ([AGEP] BETWEEN 4 AND 11 AND [SCHG] IN (''2'',''3''))
                -- 5th-8th restricted to ages 8-15
                OR ([AGEP] BETWEEN 8 AND 15 AND [SCHG] = ''4'')
                -- 9th-12th restricted to ages 12-19
                OR ([AGEP] BETWEEN 12 AND 19 AND [SCHG] = ''5'')
                -- College and Graduate school restricted to ages 15-50
                OR ([AGEP] BETWEEN 15 AND 50 AND [SCHG] IN (''6'',''7''))
            '
            WHEN @year > 2011 THEN '
                -- Look at Nursery School for ages 4-5 as these may be TK (starting in 2023+)
                ([AGEP] BETWEEN 4 AND 5 AND [SCHG] IN (''01'',''02''))
                -- (T)K-4th restricted to ages 4-11
                OR ([AGEP] BETWEEN 4 AND 11 AND [SCHG] IN (''02'',''03'',''04'',''05'',''06''))
                -- 5th-8th restricted to ages 8-15
                OR ([AGEP] BETWEEN 8 AND 15 AND [SCHG] IN (''07'',''08'',''09'',''10''))
                -- 9th-12th restricted to ages 12-19
                OR ([AGEP] BETWEEN 12 AND 19 AND [SCHG] IN (''11'',''12'',''13'',''14''))
                -- College and Graduate school restricted to ages 15-50
                OR ([AGEP] BETWEEN 15 AND 50 AND [SCHG] IN (''15'',''16''))
            '
            ELSE NULL
        END;

    -- Query built using ACS PUMS specific filters
    DECLARE @query NVARCHAR(max) = '
        SELECT
            [AGEP],
            [SCHG],
            CASE
                WHEN [AGEP] BETWEEN 4 AND 5 AND [SCHG] IN (''1'',''01'') THEN ''Nursery school/preschool''
                WHEN [AGEP] BETWEEN 4 AND 5 AND [SCHG] IN (''2'',''02'') THEN ''Kindergarten''
                ELSE NULL
            END AS [tk_reallocation],
            CASE
                WHEN [SCHG] IN (''2'',''3'',''02'',''03'',''04'',''05'',''06'') THEN ''K-4th''
                WHEN [SCHG] IN (''4'',''07'',''08'',''09'',''10'') THEN ''5th-8th''
                WHEN [SCHG] IN (''5'',''11'',''12'',''13'',''14'') THEN ''9th-12th''
                WHEN [SCHG] IN (''6'',''7'',''15'',''16'') THEN ''College''
                ELSE NULL
            END AS [enrollment_category],
            SUM([PWGTP]) AS [PWGTP]
        FROM [acs].[pums].[vi_5y_' + @pums + '_persons_sd]
        WHERE
            [AGEP] >= 3  -- <3 year olds excluded from [SCHG] variable
            AND [SCHG] IS NOT NULL  -- NULL for "N/A (not attending school)" and <3 years old
            AND ' + @no_gq_filter + '  -- Exclude group quarters population
            -- School enrollment grades are restricted by age
            AND (' + @enrollment_age_filter + ')
        GROUP BY
            [AGEP],
            [SCHG]
        ORDER BY
            [AGEP],
            [SCHG]
    '

    EXECUTE sp_executesql @query
END