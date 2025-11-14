## 1 Overview
The Cohort Component model outputs three core datasets; the Population/Households/Group Quarters information, the Rates used to increment the Population and create Households/Group Quarters information, and the Components of Change. These individual datasets are described below.

## 2 Output Datasets

#### Table 1: Population/Households/Group Quarters information
| Field | Type | Description | 
| :---: | :--: | ----------- |
| **year**          | integer | *The increment year; includes the base up to horizon year.* |
| **race**          | string  | *Race/ethnicity category.* |
| **sex**           | string  | *Sex category.* |
| **age**           | integer | *Single year of age.* |
| **pop**           | integer | *Total population.* |
| **pop_mil**       | integer | *Active-duty military population.* |
| **gq**            | integer | *Group Quarters population*. |
| **hh**            | integer | *Total households.* |
| **hh_head_lf**    | integer | *Heads of households in the labor force.* |
| **child1**        | integer | *Households with children (<18) present.* |
| **senior1**       | integer | *Households with senior (>=65) present.* |
| **size1**         | integer | *Households with 1 person.* |
| **size2**         | integer | *Households with 2 persons.* |
| **size3**         | integer | *Households with 3 or more persons.* |
| **workers0**      | integer | *Households with no workers.* |
| **workers1**      | integer | *Households with 1 worker.* |
| **workers2**      | integer | *Households with 2 workers.* |
| **workers3**      | integer | *Households with 3 or more workers.* |

#### Table 2: Rates
| Field | Type | Description | 
| :---: | :--: | ----------- |
| **year**            | integer | *The increment year; includes the base up to horizon year.* |
| **race**            | string  | *Race/ethnicity category.* |
| **sex**             | string  | *Sex category.* |
| **age**             | integer | *Single year of age.* |
| **rate_birth**      | float   | *Birth rate.* |
| **rate_death**      | float   | *Death rate.* |
| **rate_in**         | float   | *In migration rate. Includes both foreign and domestic.* |
| **rate_out**        | float   | *Out migration rate.* |
| **rate_gq**         | float   | *Group Quarters formation rate.* |
| **rate_hh**         | float   | *Household formation rate.* |
| **rate_hh_head_lf** | float   | *Labor force participation rate for heads of households.* |
| **rate_size1**      | float   | *Household characteristic rate; households with 1 person.* |
| **rate_size2**      | float   | *Household characteristic rate; households with 2 persons.* |
| **rate_size3**      | float   | *Household characteristic rate; households with 3 or more persons.* |
| **rate_child1**     | float   | *Household characteristic rate; households with 1 or more children (<18).* |
| **rate_senior1**    | float   | *Household characteristic rate; households with 1 or more seniors (>=65).* |
| **workers0**        | float   | *Household characteristic rate; households with no workers.* |
| **workers1**        | float   | *Household characteristic rate; households with 1 worker.* |
| **workers2**        | float   | *Household characteristic rate; households with 2 workers.* |
| **workers3**        | float   | *Household characteristic rate; households with 3 or more workers.* |

#### Table 3: Components of Change
| Field | Type | Description | 
| :---: | :--: | ----------- |
| **year**   | integer | *The increment year; includes the base up to horizon year.* |
| **race**   | string  | *Race/ethnicity category.* |
| **sex**    | string  | *Sex category.* |
| **age**    | integer | *Single year of age.* |
| **deaths** | integer | *Deaths.* |
| **births** | integer | *Births.* |
| **ins**    | integer | *In migrants. Includes both foreign and domestic.* |
| **outs**   | integer | *Out migrants.* |

## 3 Storage Location
Output files for each increment year from base to horizon are written to the **output** folder as csv files; **population.csv**, **rates.csv**, and **components.csv**.