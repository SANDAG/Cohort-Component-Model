-- Create shell table of required race, sex, and ages in result table
-- Age: 0-110, Sex: F, M, Race: 7 Options
DROP TABLE IF EXISTS [tt_shell];
WITH [age] AS (
    SELECT 0 AS [age]
        UNION ALL
    SELECT [age] + 1 FROM [age] WHERE [age] < 110
),
[sex] AS (
    SELECT [sex] FROM (VALUES ('F'), ('M')) AS [tt] ([sex])
),
[race] AS (
    SELECT [race] FROM (
        VALUES
          ('Hispanic'),
          ('White alone'),
          ('Black or African American alone'),
          ('American Indian or Alaska Native alone'),
          ('Asian alone'),
          ('Native Hawaiian or Other Pacific Islander alone'),
          ('Two or More Races')
    ) AS [tt] ([race])
)
SELECT [age], [sex], [race]
INTO [tt_shell]
FROM [age]
CROSS JOIN [sex]
CROSS JOIN [race]
OPTION (MAXRECURSION 111);


-- Create temporary table of Census 2010 San Diego County PUMAs
-- 5yr ACS PUMS from 2012-2016 to 2017-2021 use 2010 Census PUMAs
DROP TABLE IF EXISTS [tt_sd_pumas_2010];
DECLARE @tt_sd_pumas_2010 TABLE ([PUMA] varchar(5))
INSERT INTO @tt_sd_pumas_2010
	([puma])
VALUES
	('07301'),
	('07302'),
	('07303'),
	('07304'),
	('07305'),
	('07306'),
	('07307'),
	('07308'),
	('07309'),
	('07310'),
	('07311'),
	('07312'),
	('07313'),
	('07314'),
	('07315'),
	('07316'),
	('07317'),
	('07318'),
	('07319'),
	('07320'),
	('07321'),
	('07322');


-- Select ACS PUMS data based on input survey year this is done to lower runtime
DECLARE @year integer = {yr};
DECLARE @pums_qry nvarchar(max) =
    CASE WHEN @year = 2020 THEN 'SELECT [SERIALNO], [ST], [PUMA], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [RELSHIPP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[5y_2016_2020_persons]'
         WHEN @year = 2021 THEN 'SELECT [SERIALNO], [ST], [PUMA], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [RELSHIPP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[5y_2017_2021_persons]'
    ELSE NULL END;

-- Declare temporary table to insert results of ACS PUMS query
DROP TABLE IF EXISTS #pums_tbl
CREATE TABLE #pums_tbl (
    [SERIALNO] varchar(13) NOT NULL,
    [ST] varchar(2) NOT NULL,
    [PUMA] varchar(5) NULL,
    [AGEP] int NOT NULL,
    [SEX] varchar(1) NOT NULL,
    [HISP] varchar(2) NOT NULL,
    [RAC1P] varchar(1) NOT NULL,
    [MIL] varchar(1) NULL,
    [RELSHIPP] varchar(2) NOT NULL,
    [SPORDER] float NOT NULL,
    [ESR] varchar(1) NULL,
    [PWGTP] float NOT NULL
);

-- Insert ACS PUMS query results into temporary table
INSERT INTO #pums_tbl
EXECUTE sp_executesql @pums_qry;


-- Get San Diego County single year of age, sex, race population from ACS PUMs
WITH [persons] AS (
    SELECT
        [serialno],
        CASE WHEN [agep] > 110 THEN 110 ELSE [agep] END AS [age], -- maximum age is 110
        CASE WHEN [sex] = '1' THEN 'M' WHEN [sex] = '2' THEN 'F' ELSE NULL END AS [sex],
        CASE WHEN [hisp] != '01' THEN 'Hispanic' -- Hispanic takes precendence over Race
             WHEN [rac1p] IN ('1', '8') THEN 'White alone' -- both White and Other
             WHEN [rac1p] = '2' THEN 'Black or African American alone'
             WHEN [rac1p] IN ('3','4','5') THEN 'American Indian or Alaska Native alone'
             WHEN [rac1p] = '6' THEN 'Asian alone'
             WHEN [rac1p] = '7' THEN 'Native Hawaiian or Other Pacific Islander alone'
             WHEN [rac1p] = '9' THEN 'Two or More Races'
             ELSE NULL END AS [race],
        [mil],
        [relshipp],
        [sporder],
        [esr],
        [pwgtp]
    FROM #pums_tbl
    WHERE
        -- Note the [ST] and [PUMA] fields are specific to certain years of ACS
       -- 5yr ACS PUMS from 2012-2016 to 2017-2021 use 2010 Census PUMAS
       (@year BETWEEN 2016 AND 2021 AND [st] = '06' AND [puma] IN (SELECT [puma] FROM @tt_sd_pumas_2010))
),
[hh_info] AS (
    SELECT
        [serialno],
        COUNT([serialno]) AS [size],
        SUM(CASE WHEN [esr] IN (1,2,4,5) THEN 1 ELSE 0 END) AS [workers],
        MAX(CASE WHEN [age] < 18 THEN 1 ELSE 0 END) AS [children],
        MAX(CASE WHEN [age] >= 65 THEN 1 ELSE 0 END) AS [seniors]
    FROM [persons]
    GROUP BY [serialno]
)
SELECT
    [tt_shell].[age],
    [tt_shell].[sex],
    [tt_shell].[race],
    ISNULL(SUM([pwgtp]), 0) AS [pop],
    SUM(CASE WHEN [mil] = '1' THEN [pwgtp] ELSE 0 END) AS [pop_mil],
    SUM(CASE WHEN [relshipp] IN ('37','38') THEN [pwgtp] ELSE 0 END) AS [pop_gq],
    SUM(CASE WHEN [relshipp] NOT IN ('37','38') THEN [pwgtp] ELSE 0 END) AS [pop_hh],
    -- households and household attributes
    SUM(CASE WHEN [relshipp] NOT IN ('37','38') AND [sporder] = 1 THEN [pwgtp] ELSE 0 END) AS [pop_hh_head],
    SUM(CASE WHEN [relshipp] NOT IN ('37','38') AND [sporder] = 1 AND [esr] IN (1,2,3,4,5) THEN [pwgtp] ELSE 0 END) AS [hh_head_lf],
    SUM(CASE WHEN [relshipp] NOT IN ('37','38') AND [sporder] = 1 AND [size] = 1 THEN [pwgtp] ELSE 0 END) AS [size1],
    SUM(CASE WHEN [relshipp] NOT IN ('37','38') AND [sporder] = 1 AND [size] = 2 THEN [pwgtp] ELSE 0 END) AS [size2],
    SUM(CASE WHEN [relshipp] NOT IN ('37','38') AND [sporder] = 1 AND [size] >= 3 THEN [pwgtp] ELSE 0 END ) AS [size3],
    SUM(CASE WHEN [relshipp] NOT IN ('37','38') AND [sporder] = 1 AND [workers] = 0 THEN [pwgtp] ELSE 0 END) AS [workers0],
    SUM(CASE WHEN [relshipp] NOT IN ('37','38') AND [sporder] = 1 AND [workers] = 1 THEN [pwgtp] ELSE 0 END) AS [workers1],
    SUM(CASE WHEN [relshipp] NOT IN ('37','38') AND [sporder] = 1 AND [workers] = 2 THEN [pwgtp] ELSE 0 END) AS [workers2],
    SUM(CASE WHEN [relshipp] NOT IN ('37','38') AND [sporder] = 1 AND [workers] >= 3 THEN [pwgtp] ELSE 0 END) AS [workers3],
    SUM(CASE WHEN [relshipp] NOT IN ('37','38') AND [sporder] = 1 AND [children] = 1 THEN [pwgtp] ELSE 0 END) AS [child1],
    SUM(CASE WHEN [relshipp] NOT IN ('37','38') AND [sporder] = 1 AND [seniors] = 1 THEN [pwgtp] ELSE 0 END) AS [senior1]
FROM [persons]
INNER JOIN [hh_info]
    ON [persons].[serialno] = [hh_info].[serialno]
RIGHT OUTER JOIN [tt_shell]
    ON [persons].[age] = [tt_shell].[age]
    AND [persons].[sex] = [tt_shell].[sex]
    AND [persons].[race] = [tt_shell].[race]
GROUP BY [tt_shell].[age], [tt_shell].[sex], [tt_shell].[race]
ORDER BY [tt_shell].[age], [tt_shell].[sex], [tt_shell].[race]