## 1 Overview
Control the calculated population, group quarters, households, and household characteristics totals for each increment from the base year up to the launch year.

## 2 Input Datasets
* [SANDAG's Estimates Program](https://opendata.sandag.org/stories/s/SANDAG-Estimates-PDF-Reports/mire-zdsi/)
* [Calculated Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Population-Calculator)

## 3 Methods
* Take the Calculated Population and scale the total population, group quarters, households, and number of households within each characteristic category, if there exists a SANDAG Estimate, to match the total for the increment year from SANDAG's Estimates program using the version from the chosen launch year.

* Note that all population-related fields (e.g. total group quarters but not the military population as it is held constant) are scaled along with the total population even if no SANDAG Estimate exists for them. This is also true for all household-related fields (e.g. characteristic categories). Thus, even if no controls are supplied excepting for total population and households, all related fields will scale with them.

## 4 Repository Location
The main classes, methods, and utilities associated with controlling the calculated population totals are contained in **python/calculate_population.py**