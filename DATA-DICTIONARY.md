# Data dictionary

Author: Felix Suwarno
Last updated: 2026-11-18

This file describes the fields that the building lookup returns, the Housing Court ZIP table, its run record, and one note about Environmental Control Board severity labels. The building lookup and the ZIP table are separate. A ZIP table count is never a fact about one building.

## Building profile: `getBuildingProfile()` in `building-profile.js`

- What it describes: one tax lot, identified by its Borough, Block, and Lot number (BBL), and every building on that lot. A lot can hold several buildings, and the lookup cannot separate them. It never holds a Housing Court count by ZIP code.
- Built by: the function `getBuildingProfile(building)` in `building-profile.js`. It runs in the browser at each visit. Nothing it returns is stored in this repository.
- Input: the address match from GeoSearch, the address search of the New York City Department of City Planning. The lookup uses its `bbl`, `bin`, and `postalCode` values.
- Output: one object with the fields `bbl`, `bin`, `nycha`, `zip`, `fetchedAt`, and `datasets`.
- Refresh: the numbers are asked for again at every visit, so they change when the source datasets change.
- Known gaps and limits: see the methodology file.

Rules that hold for every field of the profile:

- Every count is a whole number. A count of 0 means the source has no matching record.
- Every date is text written as YYYY-MM-DD, or null when the source has no date.
- Null means that the value is unknown or not available. It never means 0.
- If one dataset does not answer within 20 seconds, or answers with an error, its section is replaced by one field named `error`. The `error` field holds a short text, for example `im9z-53hg answered 503`. The other sections still come back. A section with an `error` field is not a count of 0.
- A class or a severity that has no record is not listed. For example, `openByClass` has no key `I` when the building has no open class I violation.
- Each section has a field `source`. It holds the identifier of the NYC Open Data dataset that the section reads.
- The profile holds no raw row, no apartment number, no court index number, no name of a person, no dollar amount, and no violation description. The owner name from PLUTO is used only to set `nycha.isNycha` and is never returned.

In the field entries below, "source" names the dataset column the value comes from. "code" means `building-profile.js` decides the value.

### `bbl`
- Type: text. Always 10 digits.
- Meaning: the Borough, Block, and Lot number of the building's tax lot. It is 1 digit for the borough, 5 digits for the block, and 4 digits for the lot.
- Source: the address search (`addendum.pad.bbl`).

### `bin`
- Type: text, or null.
- Meaning: the Building Identification Number (BIN) of the building that the address search found. It is returned exactly as the address search gave it. It can be null, or a placeholder that ends in 000000. A missing BIN, a BIN that is not 7 digits, and a placeholder BIN are never used in a query.
- Source: the address search (`addendum.pad.bin`).

### `nycha`
- Type: object with two fields, `isNycha` and `development`. It sits next to `bbl` and `bin`, not inside `datasets`.
- Meaning: whether the building is a New York City Housing Authority (NYCHA) building.
- Source: the NYCHA Residential Addresses list (`3ub5-4ph8`) and PLUTO (`64uk-42ks`), and the code.

### `nycha.isNycha`
- Type: true, false, or null.
- Meaning: true when either source matches the building's BBL. The NYCHA Residential Addresses list matches when column `borough_block_lot` equals the BBL. PLUTO matches when column `ownername` contains "HOUSING AUTH" for the BBL. False when both lookups worked and neither matched. Null when neither source matched and at least one lookup failed, so the site knows that the building could not be checked. When one source matches and the other lookup fails, the value is true.
- Source: `borough_block_lot` in dataset `3ub5-4ph8`, and `ownername` in dataset `64uk-42ks`. Both BBL columns are number columns.

### `nycha.development`
- Type: text, or null.
- Meaning: the name of the NYCHA development, for example BRONX RIVER. It is null when the NYCHA Residential Addresses list has no match, or when that lookup failed. If the rows of one lot name more than one development, the first name in alphabetical order is returned.
- Source: `development` in dataset `3ub5-4ph8`.

### `zip`
- Type: text, or null.
- Meaning: the ZIP code (Zone Improvement Plan code) of the building's address. It is not a Housing Court count and not a neighborhood figure.
- Source: `postalCode` from the address search.

### `fetchedAt`
- Type: text.
- Meaning: the time the lookup finished, in Coordinated Universal Time, for example 2026-11-18T22:51:20.213Z.
- Source: the code.

### `datasets`
- Type: object with eight sections: `evictions`, `hpdViolations`, `hpdComplaints`, `hpdLitigation`, `dobViolations`, `ecbViolations`, `nychaViolations`, and `pluto`.
- Meaning: one section for each source dataset. The fields of each section follow.

### `datasets.evictions`: Department of Investigation marshal evictions

Source: dataset `6z8x-wfk4`. A row is matched when its `bbl` equals the building's BBL (text) and `residential_commercial_ind` is Residential. Evictions with no BBL are not counted. As of October 20, 2026, 8,401 of 123,897 residential evictions (6.8 percent) had no BBL.

- `source`: text. `6z8x-wfk4`.
- `residentialTotal`: number. The number of residential evictions at the lot. It is the sum of `residentialByYear`.
- `residentialByYear`: object. Each key is a year, and each value is the number of residential evictions with an execution date (`executed_date`) in that year. A year with no evictions is not listed.

### `datasets.hpdViolations`: Housing Preservation and Development (HPD) violations

Source: dataset `wvxf-dwi5`. A row is matched when its `bbl` column equals the building's BBL (text). About 10,600 rows in the whole dataset have no `bbl` value and are not counted.

- `source`: text. `wvxf-dwi5`.
- `total`: number. All violations at the lot.
- `open`: number. Violations with `violationstatus` equal to Open. It includes class I as well as classes A, B, and C.
- `closed`: number. `total` minus `open`. It counts every violation whose status is not Open.
- `openByClass`: object. Each key is a violation class from the column `class`, and each value is the number of open violations of that class. Class A is the least serious, B is serious, C is the most serious, and I is an informational order. Class I is counted here separately, and it is part of `open`.
- `openRentImpairing`: number. Open violations with `rentimpairing` equal to Y. The source's own definition of that flag has not been compared with this use.
- `latestInspectionDate`: date, or null. The latest `inspectiondate` of all violations, open or closed.

### `datasets.hpdComplaints`: HPD complaints

Source: dataset `ygpa-z7cr`. A row is matched when its `bbl` equals the building's BBL (number column). Each row is one problem inside a complaint, so the lookup counts distinct `complaint_id` values and not rows. About 37,400 of the 16.4 million rows in the whole dataset have no `bbl` value and are not counted. The apartment number and the anonymous-complaint flag are never returned. There is no count of all complaints, because that count took 17 to 38 seconds on the largest buildings.

- `source`: text. `ygpa-z7cr`.
- `openComplaints`: number. Distinct complaints with `complaint_status` equal to OPEN.
- `complaintsLast12Months`: number. Distinct complaints with `received_date` on or after the day 365 days before the lookup.
- `latestComplaintDate`: date, or null. The latest `received_date` of all complaints at the lot.

### `datasets.hpdLitigation`: HPD housing litigation

Source: dataset `59kj-x8nc`. A row is matched when its `bbl` column equals the building's BBL (text). 318 rows in the whole dataset have no `bbl` value and are not counted. The respondent name, the penalty, and the case identifiers are never returned.

- `source`: text. `59kj-x8nc`.
- `totalCases`: number. All cases at the lot.
- `pendingCases`: number. Cases with `casestatus` equal to PENDING or APPLICATION PENDING. A few old cases (2006 and earlier) have other status text, and they count as not pending.
- `casesByType`: object. Each key is a case type label from `casetype`, written as the source writes it, including its spelling "Harrassment". Each value is the number of cases of that type.
- `harassmentFindings`: number. Cases with `findingofharassment` equal to After Inquest or After Trial. The value No Harassment does not count.
- `latestCaseOpenDate`: date, or null. The latest `caseopendate`.

### `datasets.dobViolations`: Department of Buildings (DOB) violations

Source: dataset `3h2n-5cm9`. It holds the older civil penalties that the Department of Buildings recorded. The newer civil penalties are in a different dataset, DOB Safety Violations, which the lookup does not read. A row is matched when its `bin` is in the list of BINs on the lot, or when its `boro`, `block`, and `lot` are the lot of the building. This dataset writes the borough as 1 digit, the block as 5 digits, and the lot as 5 digits, so the lot gets a leading 0. If the list of BINs is empty, only the lot is used.

- `source`: text. `3h2n-5cm9`.
- `buildingsOnLot`: number. The number of usable BINs in the list of BINs on the lot. The list holds the BIN from the address search and the BIN of every building on the lot in NYC Building Footprints (dataset `5zhs-2jue`). It can be 0.
- `totalViolations`: number. All violations matched.
- `activeViolations`: number. Violations whose `violation_category` ends with the word ACTIVE. One category with the text "V%-DOB VIOLATION" (about 1,000 rows in the whole dataset) does not say whether it is active or dismissed and is not counted as active.
- `activeHazardousViolations`: number. Active violations whose category starts with VH or VWH. This rule comes from the category text. The source's own definition of these codes has not been compared with it.
- `latestIssueDate`: date, or null. The latest `issue_date`. The source writes it as YYYYMMDD, and the code writes it as YYYY-MM-DD.

### `datasets.ecbViolations`: Environmental Control Board (ECB) summonses

Source: dataset `6bgk-3dad`. A row is matched when its `bin` is in the list of BINs on the lot, or when its `boro`, `block`, and `lot` are the lot of the building. This dataset writes the borough as 1 digit, the block as 5 digits, and the lot as 4 digits. If the list of BINs is empty, only the lot is used. The respondent name, the penalty, and the dollar amounts are never returned, because the source does not define its money columns.

- `source`: text. `6bgk-3dad`.
- `buildingsOnLot`: number. The number of usable BINs in the list of BINs on the lot, as in `datasets.dobViolations.buildingsOnLot`.
- `totalSummonses`: number. All summonses matched.
- `activeSummonses`: number. Summonses with `ecb_violation_status` equal to ACTIVE. The source also uses RESOLVE and, for 3 rows in the whole dataset, Unknown.
- `activeBySeverity`: object. Each key is a severity label from the column `severity`, written as the source writes it. A summons with no severity is counted under the key Not stated. Each value is the number of active summonses with that label. The source uses two labelling schemes, CLASS - 1, CLASS - 2, and CLASS - 3, and Hazardous and Non-Hazardous. Both are kept as they are.
- `latestIssueDate`: date, or null. The latest `issue_date`. The source writes it as YYYYMMDD, and the code writes it as YYYY-MM-DD.

### `datasets.nychaViolations`: HPD violations at NYCHA properties

Source: dataset `im9z-53hg`. HPD publishes these violations in a separate dataset from `wvxf-dwi5`. A row is matched when its `bbl` equals the building's BBL (number column). Rows with `issued_in_err` equal to Y (issued in error) are left out, and rows where it is empty are kept. The dataset has no open or closed status, so the section has no open count. The dataset starts in September 2025. The violation description, the apartment, and the stairhall are never returned.

- `source`: text. `im9z-53hg`.
- `total`: number. All violations matched.
- `byClass`: object. Each key is a hazard class from the column `hzrd_clas` (A, B, or C). A violation with no class is counted under the key Not stated. Each value is the number of violations of that class.
- `latestInspectionDate`: date, or null. The latest `insp_dt`.

### `datasets.pluto`: PLUTO values

Source: dataset `64uk-42ks`, the Primary Land Use Tax Lot Output of the New York City Department of City Planning. A row is matched when its `bbl` equals the building's BBL (number column). Both values describe the whole tax lot, which can hold several buildings.

- `source`: text. `64uk-42ks`.
- `unitsRes`: number, or null. The number of residential units, from `unitsres`. PLUTO writes 0 when the value is unknown, and the code returns null for 0. It is also null when PLUTO has no row for the lot.
- `yearBuilt`: number, or null. The year built, from `yearbuilt`. PLUTO writes 0 when the value is unknown, and the code returns null for 0. It is also null when PLUTO has no row for the lot.

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