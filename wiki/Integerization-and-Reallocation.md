## 1 Overview
Integerize the calculated population, group quarters, households, and household characteristics totals for each increment from the base year up to the horizon year.

## 2 Input Datasets
* [Calculated Population](https://github.com/SANDAG/Cohort-Component-Model/wiki/Population-Calculator)

## 3 Methods
* Take the Calculated Population and integerize the total population, group quarters, households, and number of households within each characteristic category such that the sum is preserved within each using the **integerize_1d** method described below.

* After integerization, for each field, ensure that all constraints (e.g. HH Workers 0 <= HHs) are respected by reallocating integers from records violating constraints to records with non-zero values that do not violate constraints preserving the sum within each field.

## 4 Repository Location
The main classes, methods, and utilities associated with integerization and reallocation are contained in **python/calculate_population.py** and **python/utilities.py**

## One-dimensional rounding/integerization (`integerize_1d()`)

### Input data

The input to this function is any one-dimensional list of data, an optional integer control value, an optional methodology (default value `weighted_random`), and an optional random number generator (type: `numpy.random.Generator`, typically created by calling `numpy.random.default_rng(seed=42)`. Additionally, the following conditions must hold:

*   All numeric input data must be non-negative
*   If no optional integer control value is provided, then the one-dimensional list of data must exactly sum to a non-negative integer value
*   The optional methodology must be one of `largest`, `smallest`, `largest_difference`, or `weighted_random`
*   The optional random number generator is used if and only if the chosen methodology is `weighted_random`

### Output data

The output of this function is one-dimensional data of the same shape as the input list of data, such that the following conditions all hold:

*   The sum of the output data exactly matches either (1) the optional control value or (2) the sum of the input data assuming it was a non-negative integer value
*   All output data consists of only non-negative integer values
*   The output is deterministic with respect to the input data. In other words, assuming input data is not changed, the output data will always be exactly the same

### Algorithm

There are four different methodologies, used in `integerize_1d()`. Each methodology uses the exact same workflow, but differ in the metric used to resolve rounding error:

1.  Validate input data. In other words, ensure that (1) valid rounding error methodology was chosen, (2) a seeded random generator was input, if necessary for the chosen rounding error methodology, and (3) all input data is of the correct type and contains no negative values
2.  Get the control value. If not input, then the control value is the sum of the original input data
3.  Control input data to the control value. The input data is simply scaled by a percent change in order to exactly equal the control. Note that data at this point is still decimal
4.  Round data upwards. In theory, rounding up helps to preserve the diversity of data by allowing tiny values to still remain present, as opposed to being rounded down to nothingness.
5.  Resolve rounding error using one of the four methodologies (`largest`, `smallest`, `largest_difference`, or `weighted_random`)

For each methodology, start by computing the amount of rounding error (aka `e`) by subtracting the sum of the post-rounding values and the control value. The following facts always hold true for `e`:

*   `e` is a non-negative integer. Since we always round up, each data point can result in deviations in the range of `[0, 1)`. The sum of non-negative values is also non-negative. Additionally, since the pre/post-rounding data both sum to a non-negative integer, the sum of the difference must also be a non-negative integer
*   `e` is less than or equal to the number of non-zero data points in the post-rounding data. If a data point is zero, rounding up does nothing. Thus, if we consider the number of non-zero data points (`n`), each each non-zero data point can result in deviations in the range of `[0, 1)`, then the maximum deviation is in the range of `[0*n, 1*n)`. In other words, the maximum possible deviation of `n` is guaranteed to be less than `e`

Now with `e` in hand, we choose a set of data points to decrease by one in order to resolve rounding error. This is where the differing methodologies comes into play:

1.  'largest': Choose the `e` largest data points and decrease them by one
2.  'smallest': Choose the `e` smallest non-zero data points and decrease them by one
3.  'largest\_difference': Compute the difference between pre/post-rounding values. Choose the `e` data points which had the largest difference between pre and post-rounding values
4.  'weighted\_random': The default methodology. Compute the difference between pre/post-rounding values. Using a seeded random generator, choose `e` data points without replacement while using the difference as weights. Or in other words, the larger the difference between pre and post-rounding values, the more likely the data point is to be chosen

In case of ties, all methodologies break ties by taking either the first occurrence (`smallest`) or the last occurrence (`largest` and `largest_difference`) . The `weighted_random` methodology will never have ties as it uses random sampling

### Why is `weighted_random` the default methodology?

`weighted_random` is the default methodology simply because all other methodologies, i.e. `largest`, `smallest`, and `largest_difference` all suffer from the same ailment that causes widespread data shifts. Specifically, these methodologies consistently choose the exact same categories to adjust, which causes extremely visible shifts once data has been aggregated. Since these data shifts are easiest to discuss with respect to population by age/sex/ethnicity (ASE), I'll be using ASE language here. Just keep in mind that this effect happens with all variables, not just with ASE.

ASE data is created by applying Census Tract level ASE distributions to MGRA population counts, after which the data is passed into the 1D integerizer. In ASE data, there are (`20` age groups x `2` sexes x `7` race/ethnicity categories =) `280` total categories, which further implies that each category has on average (`1` / `280` =) `.36%` of the population. When you consider further that the race/ethnicity category is highly skewed towards Hispanic and NH-White, the other race/ethnicity categories are even smaller. For example, for [Census Tract `169.02` in 2020](https://data.census.gov/table/ACSDT5Y2020.B03002?q=B03002\&g=1400000US06073016902), which roughly corresponds to Barona, an area with higher than average NH-AIAN (American Indian and Alaska Native) population, the NH-AIAN race/ethnicity category has around `14%` of the population, which means each of the `80` age/sex categories have on average `.17%` of the population.

Let's hypothetically use the `smallest` methodology. Let's assume an MGRA in Census Tract `169.02` has a population of `100` people. When the Census Tract rate is applied to the MGRA, naturally, the NH-AIAN always be among the smallest ASE categories. Thus, when the 1D integerizer chooses the smallest categories to adjust for rounding error, the NH-AIAN category will consistently be chosen. For this MGRA, it doesn't really matter since a `-1` is well within rounding error. But if Census Tract `169.02` has 50 MGRAs that all decide independently to decrease NH-AIAN, now this Census Tract has a `-50` change in NH-AIAN, which is a change that obviously shows up.

If instead, we used the `largest_difference` methodology, a similar issue would occur. Because NH-AIAN is consistently the smallest ASE category across all Census Tracts, they will also consistently need to be rounded up the most, which means that they will consistently be decreased. If instead, we used the `largest` methodology, similar but opposite problem would occur. Now, instead of consistently choosing NH-AIAN categories, the 1D integerizer would now consistently choose Hispanic or NH-White, which means we would size large unexpected shifts in those categories instead of in NH-AIAN.

Additionally, keep in mind that this ASE balancing is all a zero-sum game, that a negative change in NH-AIAN in some MGRAs must be reflected by the opposite change in other MGRAs. Then, the following table shows these changes:
| Methodology | Primary Change | Secondary Change |
| --- | --- | --- |
| `smallest` | The smallest categories (typically NH-AIAN) will consistently be decreased across all MGRAs in the county | A decrease in NH-AIAN across all MGRAs in the county forces a significant amount of NH-AIAN into MGRAs where NH-AIAN is not the smallest category |
| `largest_difference` | The categories that were rounded up the most (typically NH-AIAN) will consistently be decreased across all MGRAs in the county | A decrease in NH-AIAN across all MGRAs in the county heavily concentrates NH-AIAN into MGRAs where NH-AIAN is not the category with the most rounding up |
| `largest` | The largest categories (typically Hispanic or NH-White) will consistently be decrease across all MGRAs in the county | A decrease in Hispanic/NH-White across all MGRAs in the county forces a significant amount of Hispanic/NH-White into MGRAs where Hispanic/NH-White is not the largest category |

None of the above changes are acceptable, as they result in ASE data can deviate from the ACS beyond the listed margins of errors. Therefore, the `weighted_random` methodology is used instead. The main difference of course being that the `weighted_random` methodology does not consistently choose the exact same ASE categories, only that it mostly does so.

In other words, in some Census Tracts, `smallest` and `largest_difference` will always choose NH-AIAN as the smallest category. This means that in Census Tracts which should have a tiny but non-zero amount of NH-AIAN, they are instead set to zero when adjusting for rounding error. `weighted_random` on the other hand, as it is a probabilistic method, will usually but not always choose NH-AIAN as the category, which means that some MGRAs keep their NH-AIAN and the Census Tract ends up with a tiny but non-zero amount of NH-AIAN, as it should be. So, when using `weighted_random`, every Census Tract should have a distribution which better matches the ACS, and therefore when aggregated should better match the regional controls, which means less re-distribution needs to be done.