## 1 Overview
Integerize the calculated population, group quarters, households, and household characteristics totals for each increment from the base year up to the horizon year.

## 2 Input Datasets
* [Calculated Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Population-Calculator)

## 3 Methods
* Take the Calculated Population and integerize the total population, group quarters, households, and number of households within each characteristic category such that the sum is preserved within each using the **saferound** method from the [third-party iteround library](https://pypi.org/project/iteround/).

* After integerization, for each field, ensure that all constraints (e.g. HH Workers 0 <= HHs) are respected by reallocating integers from records violating constraints to records with non-zero values that do not violate constraints preserving the sum within each field.

## 4 Repository Location
The main classes, methods, and utilities associated with integerization and reallocation are contained in **python/calculate_population.py** and **python/utilities.py**