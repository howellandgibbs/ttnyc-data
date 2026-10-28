# Data dictionary

Author: Felix Suwarno
Last updated: 2026-10-28

This file currently covers the Housing Court ZIP table, its run record, and one note about Environmental Control Board severity labels. The building-level fields have no section here yet.

## Housing Court cases by ZIP code: `ziptable.csv`

- What it describes: a neighborhood (ZIP code, meaning Zone Improvement Plan code). It never describes one building. A count in this table must never be called a building-level fact.
- Built by: `ziptable_build.py`.
- Source: the Housing Data Coalition extract of Office of Court Administration Housing Court records, tables `oca_index` and `oca_addresses`, at https://oca-2-dev.s3.amazonaws.com/public/.
- Rows: 4,340, which is 217 ZIP codes times 10 years (2016 to 2025) times 2 property groups. Rows are sorted by ZIP code, then year, then property group, with `residential` first.
- File format: CSV (comma-separated values). It stores only text, so read `zip` as text. If a tool reads it as a number, it can drop the leading zero of a ZIP code.
- Refresh: the table is rebuilt by running the build script. Where and how often it runs is not decided. The source extract is updated weekly according to one document and monthly according to another. This is not resolved.
- Known gaps: see the methodology file. The most important are that the ZIP code type rule is not enforced and that the source column descriptions have not been compared with the official Housing Data Coalition dictionary.

In the field entries below, "source" names the Housing Data Coalition column the value comes from. "script" means `ziptable_build.py` decides the value.

### `zip`
- Type: text. Always 5 digits.
- Meaning: the ZIP code of the property. It is the first 5 characters of `postalcode` from the first address row of the case. Only the 217 ZIP codes that appear on at least one New York City tax lot in PLUTO (Primary Land Use Tax Lot Output) are in the table.
- Source: `postalcode` in `oca_addresses`, and the script.

### `year`
- Type: number.
- Meaning: the year the case was filed. It is the first 4 characters of `fileddate`. Values are 2016 to 2025.
- Source: `fileddate` in `oca_index`, and the script.

### `property_group`
- Type: text. Either `residential` or `plus commercial`.
- Meaning: `residential` counts cases with property type Residential. `plus commercial` counts cases with property type Residential plus cases with property type Commercial. The `plus commercial` row already contains the `residential` cases, so never add the two rows together. For residential only, remove the `plus commercial` rows.
- Source: `propertytype` in `oca_index`, and the script.

### `total_cases`
- Type: number.
- Meaning: the number of cases for the ZIP code, year, and property group. It is counted on its own, without looking at the case type. It is not the sum of the case type columns. The case type columns plus `unclassified` must add up to it, and the build script checks that in every row.
- Source: the script.

### `non_payment`
- Type: number.
- Meaning: cases with case type Non-Payment. The landlord sues for unpaid rent.
- Source: `classification` in `oca_index`.

### `holdover`
- Type: number.
- Meaning: cases with case type Holdover. The landlord wants the apartment back for a reason other than unpaid rent, for example the lease ended.
- Source: `classification` in `oca_index`.

### `hp`
- Type: number.
- Meaning: cases with case type HP. HP is the source's own label. The tenant sues to force the landlord to make repairs.
- Source: `classification` in `oca_index`.

### `illegal_lockout`
- Type: number.
- Meaning: cases with case type Illegal Lockout. The tenant was locked out without a court order.
- Source: `classification` in `oca_index`.

### `hp_with_harassment`
- Type: number.
- Meaning: cases with case type HP with Harassment.
- Source: `classification` in `oca_index`.

### `harassment`
- Type: number.
- Meaning: cases with case type Harassment.
- Source: `classification` in `oca_index`.

### `illegal_activity`
- Type: number.
- Meaning: cases with case type Illegal Activity.
- Source: `classification` in `oca_index`.

### `article_7a`
- Type: number.
- Meaning: cases with case type Article 7A.
- Source: `classification` in `oca_index`.

### `breach_of_warrant_of_habitability`
- Type: number.
- Meaning: cases with case type Breach of Warrant of Habitability.
- Source: `classification` in `oca_index`.

### `unclassified`
- Type: number.
- Meaning: cases with any other case type, or with a blank case type. On the full build of 2026-10-12 it was expected to be 0 in every row. A value above 0 means the source has a case type that is not one of the nine.
- Source: the script.

### Rules that hold for every value in the table

- Every value is a count of cases. The table has no rates.
- Every value except `zip` and `property_group` is a whole number made of digits only.
- Only cases from the Bronx, Kings, New York, Queens, and Richmond County Civil Courts, the Harlem Community Justice Center, and the Red Hook Community Justice Center are counted. The Harlem Community Justice Center and the Red Hook Community Justice Center are community courts listed on the New York City Civil Court pages of the New York State courts website (https://nycourts.gov/courts/nyc/civil/communitycourts.shtml). The source data spells the second one "Redhook Community Justice Center." As of October 28, 2026, the courts website says the Harlem Community Justice Center is temporarily closed and sends cases to the New York County Civil Court at 111 Centre Street (https://www.nycourts.gov/node/160101). Both courts are counted in the table, so the ZIP code counts are not affected.
- Cases filed in 2026 or later are not in the table.
- Cases with a ZIP code that is not on the list of 217 are not in the table.
- The table holds no case code, no party name, no tenant name, and no address.

## Run record: `ziptable_run.json`

The build script writes this file next to `ziptable.csv`. It holds no case code. It holds:

- the build time
- the source update date
- the number of rows read
- the courts used
- the years used
- the number of ZIP codes
- the column list
- `zip_type_rule_enforced`, which is `true` or `false`. It is `false` today, because no source of ZIP code types has been chosen.
- the case counts: all New York City cases, cases left out because they were filed outside the years, cases left out for no address row, cases left out by the ZIP code type rule, cases left out because the ZIP code is not on the list (with the 20 largest left-out ZIP codes), cases counted, and extra address rows ignored
- the case types that were not one of the nine
- the list of checks that passed

## Environmental Control Board severity labels

This note describes the source. It changes no code.

The Environmental Control Board violations dataset (identifier `6bgk-3dad`) labels severity in two ways:

- Newer summonses say CLASS - 1, CLASS - 2, and CLASS - 3.
- Older summonses say Hazardous or Non-Hazardous.

Both sets of labels are kept as they are in the source. They are not merged or converted. How the site shows them has not been decided.

The source column that holds the severity label is `severity` in dataset `6bgk-3dad`. `building-profile.js` returns it as `activeBySeverity`.