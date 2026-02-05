-- Get persons and household characteristics for San Diego County by age, sex, ethnicity.
-- Household characteristics assigned to head of household record


-- Create shell table of required race, sex, and age variables with necessary categories: Age: 0-110; Sex: F, M; Race: 7 Options
DROP TABLE IF EXISTS [#tt_shell];
WITH [age] AS (
    SELECT 0 AS [age]  -- Begin with zero
        UNION ALL
    SELECT [age] + 1 FROM [age] WHERE [age] < 110  -- Add each age category up to 110
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
INTO [#tt_shell]
FROM [age]
CROSS JOIN [sex]
CROSS JOIN [race]
OPTION (MAXRECURSION 111);  -- Stop at 110


-- Select ACS PUMS data based on input survey year (this is done to lower runtime)
DECLARE @year integer = {yr};
DECLARE @pums_qry nvarchar(max) =
	CASE WHEN @year = 2010 THEN 'SELECT [SERIALNO], [ST], [AGEP], [SEX], [HISP], [RAC1P], [MIL], NULL AS [RELSHIPP], [RELP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[vi_5y_2006_2010_persons_sd]'
		 WHEN @year = 2011 THEN 'SELECT [SERIALNO], [ST], [AGEP], [SEX], [HISP], [RAC1P], [MIL], NULL AS [RELSHIPP], [RELP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[vi_5y_2007_2011_persons_sd]'
		 WHEN @year = 2012 THEN 'SELECT [SERIALNO], [ST], [AGEP], [SEX], [HISP], [RAC1P], [MIL], NULL AS [RELSHIPP], [RELP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[vi_5y_2008_2012_persons_sd]'
		 WHEN @year = 2013 THEN 'SELECT [SERIALNO], [ST], [AGEP], [SEX], [HISP], [RAC1P], [MIL], NULL AS [RELSHIPP], [RELP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[vi_5y_2009_2013_persons_sd]'
		 WHEN @year = 2014 THEN 'SELECT [SERIALNO], [ST], [AGEP], [SEX], [HISP], [RAC1P], [MIL], NULL AS [RELSHIPP], [RELP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[vi_5y_2010_2014_persons_sd]'		
		 WHEN @year = 2015 THEN 'SELECT [SERIALNO], [ST], [AGEP], [SEX], [HISP], [RAC1P], [MIL], NULL AS [RELSHIPP], [RELP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[vi_5y_2011_2015_persons_sd]'
		 WHEN @year = 2016 THEN 'SELECT [SERIALNO], [ST], [AGEP], [SEX], [HISP], [RAC1P], [MIL], NULL AS [RELSHIPP], [RELP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[vi_5y_2012_2016_persons_sd]'
		 WHEN @year = 2017 THEN 'SELECT [SERIALNO], [ST], [AGEP], [SEX], [HISP], [RAC1P], [MIL], NULL AS [RELSHIPP], [RELP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[vi_5y_2013_2017_persons_sd]'
		 WHEN @year = 2018 THEN 'SELECT [SERIALNO], [ST], [AGEP], [SEX], [HISP], [RAC1P], [MIL], NULL AS [RELSHIPP], [RELP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[vi_5y_2014_2018_persons_sd]'
		 WHEN @year = 2019 THEN 'SELECT [SERIALNO], [ST], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [RELSHIPP], NULL AS [RELP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[vi_5y_2015_2019_persons_sd]'
		 WHEN @year = 2020 THEN 'SELECT [SERIALNO], [ST], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [RELSHIPP], NULL AS [RELP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[vi_5y_2016_2020_persons_sd]'
         WHEN @year = 2021 THEN 'SELECT [SERIALNO], [ST], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [RELSHIPP], NULL AS [RELP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[vi_5y_2017_2021_persons_sd]'
		 WHEN @year = 2022 THEN 'SELECT [SERIALNO], [ST], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [RELSHIPP], NULL AS [RELP], [SPORDER], [ESR], [PWGTP] FROM [acs].[pums].[vi_5y_2018_2022_persons_sd]'
	ELSE NULL END;

-- Declare temporary table to receive results of ACS PUMS query (@pums_qry)
DROP TABLE IF EXISTS #pums_tbl
CREATE TABLE #pums_tbl (
    [SERIALNO] varchar(13) NOT NULL,
    [ST] varchar(2) NOT NULL,
    [AGEP] int NOT NULL,
    [SEX] varchar(1) NOT NULL,
    [HISP] varchar(2) NOT NULL,
    [RAC1P] varchar(1) NOT NULL,
    [MIL] varchar(1) NULL,
	[RELSHIPP] varchar(2) NULL, 
    [RELP] varchar(2) NULL,  
    [SPORDER] float NOT NULL,
    [ESR] varchar(1) NULL,
    [PWGTP] float NOT NULL
);

-- Insert ACS PUMS query results into table
INSERT INTO #pums_tbl
EXECUTE sp_executesql @pums_qry;

-- Get San Diego County single year of age, sex, race population
WITH [persons] AS (
    SELECT
        [SERIALNO], -- Count persons by their serial number
        CASE WHEN [AGEP] > 110 THEN 110 ELSE [agep] END AS [age], -- Group oldest ages into one category: if over 110, as 110; otherwise keep single year of age
        CASE WHEN [SEX] = '1' THEN 'M' WHEN [sex] = '2' THEN 'F' ELSE NULL END AS [sex], -- Change numeric codes into standard M and F text codes
		CASE WHEN [HISP] NOT IN ('01', '1') THEN 'Hispanic' -- Exclude non-Hispanic which is 01 or 1.  Hispanic takes precendence over Race
             WHEN [RAC1P] IN ('1', '8') THEN 'White alone' -- Combine Some other race with White
             WHEN [RAC1P] = '2' THEN 'Black or African American alone'
             WHEN [RAC1P] IN ('3', '4', '5') THEN 'American Indian or Alaska Native alone'  -- Group various codes for AI and AN together
             WHEN [RAC1P] = '6' THEN 'Asian alone'
             WHEN [RAC1P] = '7' THEN 'Native Hawaiian or Other Pacific Islander alone'
             WHEN [RAC1P] = '9' THEN 'Two or More Races'
             ELSE NULL END AS [race],
        [MIL],
        -- Survey year dependent indicator if person is in Group Quarters (1/0)
        CASE WHEN @year BETWEEN 2019 AND 2022 AND [RELSHIPP] IN ('37','38') THEN 1
			 WHEN @year BETWEEN 2012 AND 2018 AND [RELP] IN ('16','17') THEN 1
			 WHEN @year = 2011 AND [RELP] IN ('13','14') THEN 1
			 WHEN @year = 2010 AND [RELP] IN ('14','15') THEN 1
             ELSE 0 END AS [gq],
        [SPORDER],
        [ESR],
        [PWGTP]
    FROM #pums_tbl
),
-- Aggregate persons data to household level to get household size, number of workers, presence of children, presence of seniors
[hh_info] AS (
    SELECT
        [SERIALNO],
        COUNT([SERIALNO]) AS [size],
        SUM(CASE WHEN [ESR] IN (1,2,4,5) THEN 1 ELSE 0 END) AS [workers],  -- Exclude unemployed (3) or not in labor force (6)
        MAX(CASE WHEN [AGE] < 18 THEN 1 ELSE 0 END) AS [children],
        MAX(CASE WHEN [AGE] >= 65 THEN 1 ELSE 0 END) AS [seniors]
    FROM [persons]
    GROUP BY [SERIALNO]
)
SELECT
    [#tt_shell].[age],
    [#tt_shell].[sex],
    [#tt_shell].[race],
    ISNULL(SUM([PWGTP]), 0) AS [pop],  -- Total population
    SUM(CASE WHEN [MIL] = '1' THEN [PWGTP] ELSE 0 END) AS [pop_mil],  -- Active-duty military 
    SUM(CASE WHEN [gq] = 1 THEN [PWGTP] ELSE 0 END) AS [pop_gq],  -- Group quarters population 
    SUM(CASE WHEN [gq] = 0 THEN [PWGTP] ELSE 0 END) AS [pop_hh],  -- Household population 
	SUM(CASE WHEN [gq] = 0 AND [SPORDER] = 1 THEN [PWGTP] ELSE 0 END) AS [pop_hh_head],  -- Head of household population
    SUM(CASE WHEN [gq] = 0 AND [SPORDER] = 1 AND [ESR] IN (1,2,3,4,5) THEN [PWGTP] ELSE 0 END) AS [hh_head_lf],  -- Head of household in labor force population
	SUM(CASE WHEN [gq] = 0 AND [SPORDER] = 1 AND [size] = 1 THEN [PWGTP] ELSE 0 END) AS [size1],  -- Household size one
	SUM(CASE WHEN [gq] = 0 AND [SPORDER] = 1 AND [size] = 2 THEN [PWGTP] ELSE 0 END) AS [size2],  -- Household size two
	SUM(CASE WHEN [gq] = 0 AND [SPORDER] = 1 AND [size] >= 3 THEN [PWGTP] ELSE 0 END) AS [size3],  -- Household size three+
	SUM(CASE WHEN [gq] = 0 AND [SPORDER] = 1 AND [workers] = 0 THEN [PWGTP] ELSE 0 END) AS [workers0],  -- Household workers 0
	SUM(CASE WHEN [gq] = 0 AND [SPORDER] = 1 AND [workers] = 1 THEN [PWGTP] ELSE 0 END) AS [workers1],  -- Household workers 1
	SUM(CASE WHEN [gq] = 0 AND [SPORDER] = 1 AND [workers] = 2 THEN [PWGTP] ELSE 0 END) AS [workers2],  -- Household workers 2
    SUM(CASE WHEN [gq] = 0 AND [SPORDER] = 1 AND [workers] >= 3 THEN [PWGTP] ELSE 0 END) AS [workers3],  -- Household workers 3+
    SUM(CASE WHEN [gq] = 0 AND [SPORDER] = 1 AND [children] = 1  THEN [PWGTP] ELSE 0 END) AS [child1],  -- Household children 1+
    SUM(CASE WHEN [gq] = 0 AND [SPORDER] = 1 AND [seniors] = 1  THEN [PWGTP] ELSE 0 END) AS [senior1]  -- Household seniors 1+
FROM [persons]
INNER JOIN [hh_info]
    ON [persons].[serialno] = [hh_info].[serialno]
RIGHT OUTER JOIN [#tt_shell]
    ON [persons].[age] = [#tt_shell].[age]
    AND [persons].[sex] = [#tt_shell].[sex]
    AND [persons].[race] = [#tt_shell].[race]
GROUP BY [#tt_shell].[age], [#tt_shell].[sex], [#tt_shell].[race]
ORDER BY [#tt_shell].[age], [#tt_shell].[sex], [#tt_shell].[race]