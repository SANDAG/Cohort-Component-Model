This module generates school enrollment and enrollment rates by single year of age and enrollment category.

# Inputs
| Input | Module Source | Usage |
| ----- | ------------- | ----- |
| School Enrollment Rates | External (ACS) | The ACS 5-year PUMS provides school enrollment rates by single year of age and enrollment category |
| TK Enrollment Counts | External (CDE) | The CDE provides TK and Kindergarten enrollment counts by single year of age for San Diego County |
| Group Quarters - College | [Launch Year Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population) and [Annual Cycle](https://github.com/SANDAG/Cohort-Component-Model/wiki/Annual-Cycle) | The "Group Quarters - College" population is assumed to be fully enrolled in College in each forecast increment |

## School Enrollment Rates
The United States Census Bureau's American Community Survey (ACS) [Public Use Microdata Sample (PUMS)](https://www.census.gov/programs-surveys/acs/microdata.html) files provide school enrollment rates for San Diego County. The rates are calculated using only the household population as the "Group Quarters - College" population is assumed to be fully enrolled in College while all other group quarters populations are excluded from enrollment in any category.

## TK Enrollment Counts
The California Department of Education (CDE) provides [Statewide TK/K-12 Enrollment by Age Group and Grade](https://www.cde.ca.gov/ds/ad/edtop.asp) reports each year showing the total number of persons enrolled in TK and Kindergarten, starting in school year 2023-24. These counts are used to adjust the ACS school enrollment rates as respondents may select "Nursery school/preschool" when enrolled in TK. For the purposes of SANDAG's travel model, we prefer TK to be bundled into Kindergarten as the travel patterns are similar.

## Group Quarters - College
The "Group Quarters - College" population in each increment is assumed to be fully enrolled in College. See [Launch Year Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Launch-Year-Population) and [Annual Cycle](https://github.com/SANDAG/Cohort-Component-Model/wiki/Annual-Cycle).

# Outputs
## School Enrollment Rates
School enrollment rates by single year of age are generated primarly by using ACS PUMS data. Rates are calculated for K-4th, 5th-8th, 9th-12th, and College categories. For years 2023 and beyond, the California Department of Education enrollment data is used to adjust Nursery school/preschool persons into the Kindergarten category to account for universal TK. Rates are calculated using the ACS PUMS household population as it is assumed that all "Group Quarters - College" population is enrolled in the College category while all other group quarters populations are excluded from school enrollment.

## School Enrollment Counts
School enrollment rates are applied to the household population to create regional enrollment by enrollment category, with the "Group Quarters - College" population added to the College enrollment category.

*See the **python/enrollment.py** file and **sql/enrollment** folder for underlying code used by the module.*