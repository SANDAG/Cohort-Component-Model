/*
Get ACS population eligible for school enrollment.

This query identifies the population from the ACS PUMS dataset that is eligible
for school enrollment by single year of age. The group quarters population is
excluded as we assume all "Group Quarters - College" population is enrolled in
the College+ category while all other group quarters populations are excluded
from school enrollment.
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
    -- Calculate eligible population from ACS PUMS ---------------------------
    -- Filter to remove group quarters is ACS PUMS specific
    DECLARE @no_gq_filter NVARCHAR(MAX) = 
        CASE
            WHEN @year BETWEEN 2010 AND 2011 THEN '[RELP] NOT IN (''13'',''14'')'
            WHEN @year BETWEEN 2012 AND 2018 THEN '[RELP] NOT IN (''16'',''17'')'
            WHEN @year > 2018 THEN '[RELSHIPP] NOT IN (''37'',''38'')'
            ELSE NULL
        END;

    -- Query built using ACS PUMS specific filters
    DECLARE @query NVARCHAR(max) = '
        WITH [ages] AS (
            SELECT 0 AS [AGEP]
            UNION ALL
            SELECT [AGEP] + 1
            FROM [ages]
            WHERE [AGEP] < 99
        )
        SELECT
            [ages].[AGEP] AS [age],
            ISNULL(SUM([PWGTP]), 0) AS [pop]
        FROM [ages]
        LEFT OUTER JOIN [acs].[pums].[vi_5y_' + @pums + '_persons_sd] AS [acs]
            ON [ages].[AGEP] = CASE WHEN [acs].[AGEP] >= 99 THEN 99 ELSE [acs].[AGEP] END
            AND ' + @no_gq_filter + '  -- Exclude group quarters population
        GROUP BY [ages].[AGEP]
        ORDER BY [ages].[AGEP]
    '

    EXECUTE sp_executesql @query
END