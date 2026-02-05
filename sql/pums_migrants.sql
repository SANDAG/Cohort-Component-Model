/* 
The purpose of this script is to count migration in and out of San Diego County by age, sex, and race/ethnicity from 5-year ACS PUMS 2006-2010 to 2018-2022.
 
-- Compile in and out migration by single year of age, sex, and race/ethnicity for San Diego County from 5-year ACS PUMS for all the years into one CTE.
-- Ensure fields exist in pums_persons for each variation of a variable, such as PUMA/PUMA00/PUMA10/PUMA20 and MIGPUMA/MIGPUMA00/MIGPUMA10/MIGPUMA20, by setting the fields to NULL when there is no data for that year.
-- Combine MIGSP05 and MIGSP12 variables, which are present 2008-2012 to 2011-2015, into MIGSP, which is present 2006-2010 to 2007-2011 and 2012-2016 to 2018-2022, because the code for CA (006/6) is the same throughout.
-- Remove active-duty military and persons who did not migrate.
*/

-- Select ACS PUMS data based on input survey year this is done to lower original runtime of approximately 20 minutes to 1-4 minutes
DECLARE @year integer = {yr};
DECLARE @pums_qry nvarchar(max) =
    CASE WHEN @year = 2010 THEN 'SELECT [ST], [PUMA] AS [PUMA00], NULL AS [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [MIG], [MIGSP], [MIGPUMA] AS [MIGPUMA00], NULL AS [MIGPUMA10], NULL AS [MIGPUMA20], [PWGTP] FROM [acs].[pums].[5y_2006_2010_persons] WHERE [MIL] != ''1'' AND [MIG] IN (''2'', ''3'')'
         WHEN @year = 2011 THEN 'SELECT [ST], [PUMA] AS [PUMA00], NULL AS [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [MIG], [MIGSP], [MIGPUMA] AS [MIGPUMA00], NULL AS [MIGPUMA10], NULL AS [MIGPUMA20], [PWGTP] FROM [acs].[pums].[5y_2007_2011_persons] WHERE [MIL] != ''1'' AND [MIG] IN (''2'', ''3'')'
         WHEN @year = 2012 THEN 'SELECT [ST], [PUMA00], [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [MIG], CASE WHEN [MIGSP05] IS NULL THEN [MIGSP12] ELSE [MIGSP05] END AS [MIGSP], [MIGPUMA00], [MIGPUMA10], NULL AS [MIGPUMA20], [PWGTP] FROM [acs].[pums].[5y_2008_2012_persons] WHERE [MIL] != ''1'' AND [MIG] IN (''2'', ''3'')'
         WHEN @year = 2013 THEN 'SELECT [ST], [PUMA00], [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [MIG], CASE WHEN [MIGSP05] IS NULL THEN [MIGSP12] ELSE [MIGSP05] END AS [MIGSP], [MIGPUMA00], [MIGPUMA10], NULL AS [MIGPUMA20], [PWGTP] FROM [acs].[pums].[5y_2009_2013_persons] WHERE [MIL] != ''1'' AND [MIG] IN (''2'', ''3'')'
         WHEN @year = 2014 THEN 'SELECT [ST], [PUMA00], [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [MIG], CASE WHEN [MIGSP05] IS NULL THEN [MIGSP12] ELSE [MIGSP05] END AS [MIGSP], [MIGPUMA00], [MIGPUMA10], NULL AS [MIGPUMA20], [PWGTP] FROM [acs].[pums].[5y_2010_2014_persons] WHERE [MIL] != ''1'' AND [MIG] IN (''2'', ''3'')'
         WHEN @year = 2015 THEN 'SELECT [ST], [PUMA00], [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [MIG], CASE WHEN [MIGSP05] IS NULL THEN [MIGSP12] ELSE [MIGSP05] END AS [MIGSP], [MIGPUMA00], [MIGPUMA10], NULL AS [MIGPUMA20], [PWGTP] FROM [acs].[pums].[5y_2011_2015_persons] WHERE [MIL] != ''1'' AND [MIG] IN (''2'', ''3'')'
         WHEN @year = 2016 THEN 'SELECT [ST], NULL AS [PUMA00], [PUMA] AS [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [MIG], [MIGSP], NULL AS [MIGPUMA00], [MIGPUMA] AS [MIGPUMA10], NULL AS [MIGPUMA20], [PWGTP] FROM [acs].[pums].[5y_2012_2016_persons] WHERE [MIL] != ''1'' AND [MIG] IN (''2'', ''3'')'
         WHEN @year = 2017 THEN 'SELECT [ST], NULL AS [PUMA00], [PUMA] AS [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [MIG], [MIGSP], NULL AS [MIGPUMA00], [MIGPUMA] AS [MIGPUMA10], NULL AS [MIGPUMA20], [PWGTP] FROM [acs].[pums].[5y_2013_2017_persons] WHERE [MIL] != ''1'' AND [MIG] IN (''2'', ''3'')'
         WHEN @year = 2018 THEN 'SELECT [ST], NULL AS [PUMA00], [PUMA] AS [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [MIG], [MIGSP], NULL AS [MIGPUMA00], [MIGPUMA] AS [MIGPUMA10], NULL AS [MIGPUMA20], [PWGTP] FROM [acs].[pums].[5y_2014_2018_persons]  WHERE [MIL] != ''1'' AND [MIG] IN (''2'', ''3'')'
         WHEN @year = 2019 THEN 'SELECT [ST], NULL AS [PUMA00], [PUMA] AS [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [MIG], [MIGSP], NULL AS [MIGPUMA00], [MIGPUMA] AS [MIGPUMA10], NULL AS [MIGPUMA20], [PWGTP] FROM [acs].[pums].[5y_2015_2019_persons] WHERE [MIL] != ''1'' AND [MIG] IN (''2'', ''3'')'
         WHEN @year = 2020 THEN 'SELECT [ST], NULL AS [PUMA00], [PUMA] AS [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [MIG], [MIGSP], NULL AS [MIGPUMA00], [MIGPUMA] AS [MIGPUMA10], NULL AS [MIGPUMA20], [PWGTP] FROM [acs].[pums].[5y_2016_2020_persons] WHERE [MIL] != ''1'' AND [MIG] IN (''2'', ''3'')'
         WHEN @year = 2021 THEN 'SELECT [ST], NULL AS [PUMA00], [PUMA] AS [PUMA10], NULL AS [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [MIG], [MIGSP], NULL AS [MIGPUMA00], [MIGPUMA] AS [MIGPUMA10], NULL AS [MIGPUMA20], [PWGTP] FROM [acs].[pums].[5y_2017_2021_persons] WHERE [MIL] != ''1'' AND [MIG] IN (''2'', ''3'')'
         WHEN @year = 2022 THEN 'SELECT [ST], NULL AS [PUMA00], [PUMA10], [PUMA20], [AGEP], [SEX], [HISP], [RAC1P], [MIL], [MIG], [MIGSP], NULL AS [MIGPUMA00], [MIGPUMA10], [MIGPUMA20], [PWGTP] FROM [acs].[pums].[5y_2018_2022_persons] WHERE [MIL] != ''1'' AND [MIG] IN (''2'', ''3'')'
    ELSE NULL END;

-- Declare temporary table to insert results of ACS PUMS query
DROP TABLE IF EXISTS [#pums_tbl]
CREATE TABLE [#pums_tbl] (
    [ST] varchar(2) NOT NULL,
    [PUMA00] varchar(5) NULL,
    [PUMA10] varchar(5) NULL,
    [PUMA20] varchar(5) NULL,
    [AGEP] int NOT NULL,
    [SEX] varchar(1) NOT NULL,
    [HISP] varchar(2) NOT NULL,
    [RAC1P] varchar(1) NOT NULL,
    [MIL] varchar(1) NOT NULL,
    [MIG] varchar(1) NOT NULL,
    [MIGSP] varchar(3) NOT NULL,
    [MIGPUMA00] varchar(5) NULL,
    [MIGPUMA10] varchar(5) NULL,
    [MIGPUMA20] varchar(5) NULL,
    [PWGTP] float NOT NULL
);

-- Insert ACS PUMS query results into temporary table
INSERT INTO [#pums_tbl]
EXECUTE sp_executesql @pums_qry;


-- Create a new table which transforms the raw data in the PUMS table into useful summaries.
with [transformed_tbl] AS (
    SELECT
        CASE WHEN [AGEP] > 110 THEN 110 ELSE [AGEP] END AS [age],  -- Group oldest ages into one category, if over 110 as 110, otherwise keep single year of age
        CASE WHEN [SEX] = '1' THEN 'M' WHEN [SEX] = '2' THEN 'F' ELSE NULL END AS [sex],  -- Change numeric codes into standard M and F text codes.
        CASE WHEN [HISP] NOT IN ('01', '1') THEN 'Hispanic' -- Exclude non-Hispanic which is 01 or 1.  Hispanic takes precendence over Race
             WHEN [RAC1P] IN ('1', '8') THEN 'White alone' -- Combine Some other race with White
             WHEN [RAC1P] = '2' THEN 'Black or African American alone'
             WHEN [RAC1P] IN ('3', '4', '5') THEN 'American Indian or Alaska Native alone'  -- Group various codes for AI and AN together
             WHEN [RAC1P] = '6' THEN 'Asian alone'
             WHEN [RAC1P] = '7' THEN 'Native Hawaiian or Other Pacific Islander alone'
             WHEN [RAC1P] = '9' THEN 'Two or More Races'
             ELSE NULL END AS [race],

        -- Identify in-migrants into San Diego County       
        CASE  
            -- The ACS 5-year from 2018-2022 to 2021-2025 mix both Census 2010 and 2020 geographies (only 2018-2022 currently available, but setting up script correctly for future years)
             WHEN @year BETWEEN 2022 AND 2025
                AND (
                        -- Census 2020 geographies
                        (
                            ([MIGSP] NOT IN ('006', '6') OR ([MIGSP] IN ('006', '6') AND [MIGPUMA20] != '07300')) -- Migrated from outside California, or from within California but from outside San Diego County
                            AND [ST] = '06' AND [PUMA20] IN (SELECT DISTINCT PUMA FROM [acs].[pums].[vi_1y_2022_households_sd]) -- Currently reside in San Diego County, defined by state being California and PUMA of residence being in a list of San Diego County PUMAs
                        ) OR
                        -- Census 2010 geographies
                        (
                            ([MIGSP] NOT IN ('006', '6') OR ([MIGSP] IN ('006', '6') AND [MIGPUMA10] != '07300')) -- Migrated from outside California, or from within California but from outside San Diego County (note the code for SD County changed to 07300 in Census 2010)
                            AND [ST] = '06' AND [PUMA10] IN (SELECT DISTINCT PUMA FROM [acs].[pums].[vi_1y_2012_households_sd]) -- Currently reside in San Diego County, defined by state being California and PUMA of residence being in a list of San Diego County PUMAs
                        )
                )
                THEN [PWGTP] -- Count persons using the person weight variable

             -- The ACS 5-years from 2012-2016 to 2017-2021 solely use Census 2010 geographies
             WHEN @year BETWEEN 2016 AND 2021
                AND ([MIGSP] NOT IN ('006', '6') OR ([MIGSP] IN ('006', '6') AND [MIGPUMA10] != '07300')) -- Migrated from outside California, or from within California but from outside San Diego County (note the code for SD County changed to 07300 in Census 2010)
                AND [ST] = '06' AND [PUMA10] IN (SELECT DISTINCT PUMA FROM [acs].[pums].[vi_1y_2012_households_sd]) -- Currently reside in San Diego County, defined by state being California and PUMA of residence being in a list of San Diego County PUMAs
                THEN [PWGTP] -- Count persons using the person weight variable

            -- The ACS 5-years from 2008-2012 to 2011-2015 mix both Census 2000 and 2010 geographies
             WHEN @year BETWEEN 2012 AND 2015
                AND (
                        -- Census 2010 geographies
                        (
                            ([MIGSP] NOT IN ('006', '6') OR ([MIGSP] IN ('006', '6') AND [MIGPUMA10] != '07300')) -- Migrated from outside California, or from within California but from outside San Diego County (note the code for SD County changed to 07300 in Census 2010)
                            AND [ST] = '06' AND [PUMA10] IN (SELECT DISTINCT PUMA FROM [acs].[pums].[vi_1y_2012_households_sd]) -- Currently reside in San Diego County, defined by state being California and PUMA of residence being in a list of San Diego County PUMAs
                        ) OR
                        -- Census 2000 geographies
                        (
                            ([MIGSP] NOT IN ('006', '6') OR ([MIGSP] IN ('006', '6') AND [MIGPUMA00] != '081')) -- Migrated from outside California, or from within California but from outside San Diego County (note the code for SD County was 81 in Census 2000)
                            AND [ST] = '06' AND [PUMA00] IN (SELECT DISTINCT PUMA FROM [acs].[pums].[vi_1y_2010_households_sd]) -- Currently reside in San Diego County, defined by state being California and PUMA of residence being in a list of San Diego County PUMAs
                        )
                )
                THEN [PWGTP] -- Count persons using the person weight variable

            -- The ACS 5-years from 2006-2010 to 2007-2011 solely use Census 2000 geographies
             WHEN @year BETWEEN 2010 AND 2011
                AND ([MIGSP] NOT IN ('006', '6') OR ([MIGSP] IN ('006', '6') AND [MIGPUMA00] != '081')) -- Migrated from outside California, or from within California but from outside San Diego County (note the code for SD County was 81 in Census 2000)
                AND [ST] = '06' AND [PUMA00] IN (SELECT DISTINCT PUMA FROM [acs].[pums].[vi_1y_2010_households_sd]) -- Currently reside in San Diego County, defined by state being California and PUMA of residence being in a list of San Diego County PUMAs
                THEN [PWGTP] -- Count persons using the person weight variable
             ELSE 0 END AS [in],  -- Create table, called in, for count of in-migrants to San Diego County

        -- Identify out-migrants from San Diego County
        CASE 
            -- The ACS 5-year from 2018-2022 to 2021-2025 mix both Census 2010 and 2020 geographies (only 2018-2022 currently available, but setting up script correctly for future years)
             WHEN @year BETWEEN 2022 AND 2025
                AND (
                        -- Census 2020 geographies
                        (
                            [MIGSP] IN ('006', '6') AND [MIGPUMA20] = '07300' -- Migrated from San Diego County, defined by migration state being California and migration PUMA being the code for San Diego County (07300)
                            AND ([ST] != '06' OR ([ST] = '06' AND [PUMA20] NOT IN (SELECT DISTINCT PUMA FROM [acs].[pums].[vi_1y_2022_households_sd]))) -- Currently reside not in San Diego County, defined by state being not California and PUMA of residence being not in a list of San Diego County PUMAs
                        ) OR
                        -- Census 2010 geographies
                        (
                            [MIGSP] IN ('006', '6') AND [MIGPUMA10] = '07300' -- Migrated from San Diego County, defined by migration state being California and migration PUMA being the code for San Diego County (07300)
                            AND ([ST] != '06' OR ([ST] = '06' AND [PUMA10] NOT IN (SELECT DISTINCT PUMA FROM [acs].[pums].[vi_1y_2012_households_sd]))) -- Currently reside not in San Diego County, defined by state being not California and PUMA of residence being not in a list of San Diego County PUMAs
                        )
                )
                THEN [PWGTP] -- Count persons using the person weight variable

             -- The ACS 5-years from 2012-2016 to 2017-2021 solely use Census 2010 geographies
             WHEN @year BETWEEN 2016 AND 2021
                AND [MIGSP] IN ('006', '6') AND [MIGPUMA10] = '07300' -- Migrated from San Diego County, defined by migration state being California and migration PUMA being the code for San Diego County (07300)
                AND ([ST] != '06' OR ([ST] = '06' AND [PUMA10] IN (SELECT DISTINCT PUMA FROM [acs].[pums].[vi_1y_2012_households_sd]))) -- Currently reside not in San Diego County, defined by state being not California and PUMA of residence being not in a list of San Diego County PUMAs
                THEN [PWGTP] -- Count persons using the person weight variable

            -- The ACS 5-years from 2008-2012 to 2011-2015 mix both Census 2000 and 2010 geographies
             WHEN @year BETWEEN 2012 AND 2015
                AND (
                        -- Census 2010 geographies
                        (
                            [MIGSP] IN ('006', '6') AND [MIGPUMA10] = '07300' -- Migrated from San Diego County, defined by migration state being California and migration PUMA being the code for San Diego County (07300)
                            AND ([ST] != '06' OR ([ST] = '06' AND [PUMA10] NOT IN (SELECT DISTINCT PUMA FROM [acs].[pums].[vi_1y_2012_households_sd]))) -- Currently reside not in San Diego County, defined by state being not California and PUMA of residence being not in a list of San Diego County PUMAs
                        ) OR
                        -- Census 2000 geographies
                        (
                            [MIGSP] IN ('006', '6') AND [MIGPUMA00] = '081' -- Migrated from San Diego County, defined by migration state being California and migration PUMA being the code for San Diego County (081)
                            AND ([ST] != '06' OR ([ST] = '06' AND [PUMA00] NOT IN (SELECT DISTINCT PUMA FROM [acs].[pums].[vi_1y_2010_households_sd]))) -- Currently reside not in San Diego County, defined by state being not California and PUMA of residence being not in a list of San Diego County PUMAs
                        )
                )
                THEN [PWGTP] -- Count persons using the person weight variable

            -- The ACS 5-years from 2006-2010 to 2007-2011 solely uses Census 2000 geographies
             WHEN @year BETWEEN 2010 AND 2011
                AND [MIGSP] IN ('006', '6') AND [MIGPUMA00] = '081' -- Migrated from San Diego County,  defined by migration state being California and migration PUMA being the code for San Diego County (081)
                AND ([ST] != '06' OR ([ST] = '06' AND [PUMA00] NOT IN (SELECT DISTINCT PUMA FROM [acs].[pums].[vi_1y_2010_households_sd]))) -- Currently reside not in San Diego County,  defined by state being not California and PUMA of residence being not in a list of San Diego County PUMAs
                THEN [PWGTP] -- Count persons using the person weight variable
             ELSE 0 END AS [out] -- Create table, called out, for count of out-migrants from San Diego County
    FROM [#pums_tbl]
)
-- Output final result set of in/out migrants by age/sex/ethnicity
SELECT
    [age],
    [sex],
    [race],
    SUM([in]) AS [in],
    SUM([out]) AS [out]
FROM [transformed_tbl]  
GROUP BY [age], [sex], [race]
ORDER BY [age], [sex], [race]