The Cohort Component model outputs three core datasets; the Population/Households/Group Quarters information, the Rates used to increment the Population and create Households/Group Quarters information, and the Components of Change.

The individual datasets are described below.

# Output Datasets

## Table 1: Population/Households/Group Quarters information
| Field | Type | Description | 
| :---: | :--: | ----------- |
| **year**          | integer | *The increment year; includes the launch up to horizon year* |
| **age**           | integer | *Single year of age* |
| **sex**           | string  | *Sex category* |
| **ethnicity**     | string  | *Race/ethnicity category* |
| **pop**           | integer | *Total population* |
| **gq_mil**        | integer | *Military group quarters population* |
| **gq_prison**     | integer | *Institutional Correctional Facilities group quarters population* |
| **gq_college**    | integer | *College group quarters population* |
| **gq_other**      | integer | *Other group quarters population* |
| **hh**            | integer | *Total households* |
| **hh_size1**      | integer | *Households with 1 person* |
| **hh_size2**      | integer | *Households with 2 persons* |
| **hh_size3**      | integer | *Households with 3 or more persons* |
| **hh_workers0**   | integer | *Households with no workers* |
| **hh_workers1**   | integer | *Households with 1 worker* |
| **hh_workers2**   | integer | *Households with 2 workers* |
| **hh_workers3**   | integer | *Households with 3 or more workers* |
| **hh_head_lf**    | integer | *Households with head of household in the labor force* |
| **hh_children**   | integer | *Households with children (<18) present* |
| **hh_seniors**    | integer | *Households with senior (>=65) present* |


## Table 2: Rates
| Field | Type | Description | 
| :---: | :--: | ----------- |
| **year**             | integer | *The increment year; includes the launch up to horizon year* |
| **age**              | integer | *Single year of age* |
| **sex**              | string  | *Sex category* |
| **ethnicity**        | string  | *Race/ethnicity category* |
| **rate_birth**       | float   | *Birth rate* |
| **rate_death**       | float   | *Death rate* |
| **rate_in**          | float   | *In migration rate; includes both foreign and domestic* |
| **rate_out**         | float   | *Out migration rate* |
| **rate_gq_college**  | float   | *College group quarters formation rate* |
| **rate_gq_other**    | float   | *Other group quarters formation rate* |
| **rate_hh**          | float   | *Household formation rate* |
| **rate_hh_size1**    | float   | *Household characteristic rate; households with 1 person* |
| **rate_hh_size2**    | float   | *Household characteristic rate; households with 2 persons* |
| **rate_hh_size3**    | float   | *Household characteristic rate; households with 3 or more persons* |
| **rate_hh_workers0** | float   | *Household characteristic rate; households with no workers* |
| **rate_hh_workers1** | float   | *Household characteristic rate; households with 1 worker* |
| **rate_hh_workers2** | float   | *Household characteristic rate; households with 2 workers* |
| **rate_hh_workers3** | float   | *Household characteristic rate; households with 3 or more workers* |
| **rate_hh_head_lf**  | float   | *Household characteristic rate; labor force participation rate for heads of households* |
| **rate_hh_children** | float   | *Household characteristic rate; households with 1 or more children (<18)* |
| **rate_hh_seniors**  | float   | *Household characteristic rate; households with 1 or more seniors (>=65)* |


## Table 3: Components of Change
| Field | Type | Description | 
| :---: | :--: | ----------- |
| **year**      | integer | *The increment year; includes the launch up to horizon year* |
| **age**       | integer | *Single year of age* |
| **sex**       | string  | *Sex category* |
| **ethnicity** | string  | *Race/ethnicity category* |
| **births**    | integer | *Births* |
| **deaths**    | integer | *Deaths* |
| **ins**       | integer | *In migrants; includes both foreign and domestic* |
| **outs**      | integer | *Out migrants* |

# Storage Location
Output files for each increment year from launch to horizon are written to the **output** folder as csv files; **population.csv**, **rates.csv**, and **components.csv**.

Optionally, these outputs are assigned a run identifier and loaded to the production SQL database.