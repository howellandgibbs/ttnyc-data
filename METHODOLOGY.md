# Methodology

Author: Felix Suwarno
Last updated: 2026-11-18

This file explains two things: the building information that the website looks up for each building, and the Housing Court cases by ZIP code table. The two are separate. A ZIP code count is never a fact about one building.

## Building information

### What this is, and what it is not

When a visitor searches an address, the website looks up that building in several public New York City datasets. The lookup code is `building-profile.js`. It runs in the browser, because the site has no server. Nothing from the lookup is stored in this repository. The numbers are asked for again at every visit, so they change when the source datasets change.

Each number is a count of records in a public dataset. It is not a rating of the building. A record exists only if someone filed a complaint, an inspector wrote a violation, or an agency or court took an action. A building with few records is not necessarily in good condition.

Every section is matched on the tax lot, which is identified by its Borough, Block, and Lot number (BBL). A lot can hold more than one building, and the counts cover all of them. The lookup cannot separate the buildings on one lot, except where a section says otherwise.

The lookup returns counts and other values worked out from the data. It never returns a raw row, an apartment number, a court index number, or the name of a person.

### Plain-English terms

- A violation is a written finding by a city inspector that a building breaks a rule.
- Housing Preservation and Development (HPD) violations have a class. Class A is the least serious, class B is serious, and class C is the most serious. Class I is an informational order. These meanings come from the notes in `building-profile.js`.
- A complaint is a report made to HPD about a problem in a building. One complaint can hold several problems, so the lookup counts complaints, not problems.
- A litigation case is a Housing Court case listed in the HPD housing litigation dataset.
- A summons is a notice of violation that the Department of Buildings (DOB) issued and that the Environmental Control Board (ECB) judges.
- The New York City Housing Authority (NYCHA) owns public housing buildings. NYCHA buildings are looked up in a separate violations dataset, described below.
- PLUTO (Primary Land Use Tax Lot Output) is a New York City Department of City Planning dataset with one row for each tax lot.

### How a building is found

The website finds the address with GeoSearch, the address search of the New York City Department of City Planning (https://geosearch.planninglabs.nyc/). The search gives the BBL, the Building Identification Number (BIN), the ZIP code, and the address text.

- The BBL is always 10 digits: 1 digit for the borough, 5 digits for the block, and 4 digits for the lot. Each dataset writes it in its own way, and the code converts it. The HPD violations, HPD litigation, and evictions datasets hold the BBL as text. The HPD complaints, NYCHA address list, NYCHA violations, and PLUTO datasets hold it as a number. The Department of Buildings dataset splits it into borough, block, and a 5-digit lot. The Environmental Control Board dataset splits it into borough, block, and a 4-digit lot.
- The BIN is 7 digits. The address search can return no BIN or a placeholder BIN that ends in 000000. A missing BIN, a BIN that is not 7 digits, and a placeholder BIN are never used in a query, because they would return the records of other buildings.
- The DOB and ECB sections use a list of BINs. The list holds the BIN from the address search and the BIN of every building on the lot in NYC Building Footprints (dataset `5zhs-2jue`). Each BIN is listed once. The list can be empty, and then only the lot is used.

### What each section counts

Every dataset is asked for its answer at the same time. If one dataset does not answer within 20 seconds, or answers with an error, its section holds an error message and the other sections still come back.

**Evictions** (dataset `6z8x-wfk4`, the Department of Investigation marshal evictions)
- Counts residential evictions at the lot, in total and for each year of the execution date.
- A year with no evictions is not listed.
- Left out: evictions with no BBL. As of October 20, 2026, 8,401 of 123,897 residential evictions (6.8 percent) had no BBL. Finding them by address would be a separate project.

**HPD violations** (dataset `wvxf-dwi5`)
- Counts all violations, the open violations, and the closed ones. Closed means every violation whose status is not Open.
- The open total includes class I as well as classes A, B, and C. The open counts by class show class I separately.
- Counts the open violations that the source flags as rent impairing. The source's own definition of that flag has not been compared with this project's use of it.
- Gives the latest inspection date of all violations, open or closed.
- Matched on the dataset's own `bbl` column. Matching on the separate borough, block, and lot columns does not work: for 765 Lincoln Avenue it returned no rows, while the `bbl` column showed 5,082 open violations.
- Left out: about 10,600 violation rows in the whole dataset have no `bbl` value.
- At a NYCHA building, this dataset does not show the full picture. See "New York City Housing Authority buildings" below.

**HPD complaints** (dataset `ygpa-z7cr`)
- Counts the complaints that are still open, the complaints received in the last 365 days, and gives the date of the latest complaint.
- Counts distinct complaint identifiers, not rows.
- There is no count of all complaints since 2003. That count took 17 to 38 seconds on the largest buildings, which is longer than the 20-second limit, so the whole section would have failed where it matters most.
- Left out: about 37,400 of the 16.4 million rows in the whole dataset have no `bbl` value. The apartment number and the anonymous-complaint flag are never returned.

**HPD litigation** (dataset `59kj-x8nc`)
- Counts the cases, the cases that are pending, the cases by case type, and the cases with a finding of harassment, and gives the date the latest case was opened.
- A case is pending when its status is PENDING or APPLICATION PENDING. A few old cases (2006 and earlier) have other status text, and they count as not pending.
- A finding of harassment is counted when the finding column says After Inquest or After Trial. The value No Harassment does not count.
- Case type labels are the source's own, including its spelling "Harrassment".
- Left out: 318 rows in the whole dataset have no `bbl` value. The respondent name, the penalty, and the case identifiers are never returned.

**DOB violations** (dataset `3h2n-5cm9`)
- Counts the older civil penalties that the Department of Buildings recorded: all violations, the active violations, the active violations that are hazardous, and the latest issue date. The newer civil penalties are in a different dataset, DOB Safety Violations, which the lookup does not read.
- A violation is counted when its BIN is in the list of BINs on the lot, or when the row itself is on the lot.
- A violation is active when its category ends with the word ACTIVE. One category with the text "V%-DOB VIOLATION" (about 1,000 rows in the whole dataset) does not say whether it is active or dismissed, and it is not counted as active.
- A violation is hazardous when its category starts with VH or VWH. This rule comes from the category text. The source's own definition of these codes has not been compared with it.

**ECB violations** (dataset `6bgk-3dad`)
- Counts the summonses that the Environmental Control Board judges: all summonses, the active summonses, the active summonses by severity, and the latest issue date.
- A summons is counted when its BIN is in the list of BINs on the lot, or when the row itself is on the lot.
- A summons is active when its status is ACTIVE. The source also uses RESOLVE and, for 3 rows in the whole dataset, Unknown.
- Severity has two labelling schemes in the source: CLASS - 1, CLASS - 2, and CLASS - 3 on newer summonses, and Hazardous or Non-Hazardous on older ones. Both are kept as they are. They are not merged.
- No dollar amount is returned, because the source does not define its money columns. The respondent name and the penalty are never returned.

**New York City Housing Authority (NYCHA) violations** (dataset `im9z-53hg`)
- Counts the violations that HPD publishes for NYCHA properties in a dataset separate from the HPD violations dataset above. It gives the total, the count by hazard class (A, B, or C), and the latest inspection date.
- Matched on the dataset's `bbl` column. Rows where the column `issued_in_err` is Y (issued in error) are left out.
- The dataset has no open or closed status, so the lookup returns no open count. The dataset starts in September 2025, so it holds no earlier violations.
- The violation description, the apartment, and the stairhall are never returned.

**NYCHA flag** (field `nycha`, from the NYCHA Residential Addresses list `3ub5-4ph8` and from PLUTO `64uk-42ks`)
- Tells the site whether the building is a NYCHA building, so that the site can treat these buildings differently. The flag sits next to the BBL and the BIN in the result and not inside a section.
- `isNycha` is true when either source matches the building's BBL: the NYCHA Residential Addresses list has a row for the BBL, or the PLUTO owner name contains "HOUSING AUTH". Each source alone misses a few NYCHA lots. Together they cover all 226 lots that have violations in the NYCHA violations dataset.
- `isNycha` is false when both lookups worked and neither matched.
- `isNycha` is null when neither source matched and at least one lookup failed, so the site knows that the building could not be checked. When one source matches and the other lookup fails, `isNycha` is true.
- `development` is the development name from the NYCHA Residential Addresses list. It is null when that list has no match.
- The PLUTO owner name can be the name of a person. The lookup uses it only to set the flag and never returns it.

**PLUTO values** (dataset `64uk-42ks`)
- Gives the number of residential units (`unitsRes`) and the year built (`yearBuilt`) of the tax lot. PLUTO writes 0 when a value is unknown, and the lookup returns null for 0.
- Both values describe the whole lot, which can hold several buildings.

### New York City Housing Authority buildings

Housing Preservation and Development (HPD) inspects NYCHA buildings only when the Housing Court asks it to, so violation counts at NYCHA buildings don't show a building's full condition. HPD publishes these violations in a separate dataset, which starts in September 2025 and has no open or closed status.

The wording of this limitation is still being checked against the sources of Housing Preservation and Development.

An example shows the effect. On November 18, 2026, the lookup for 1609 East 174 Street (BBL 2038860002) returned 10 violations from the HPD violations dataset, all open, with the latest inspection date 2006-11-08. In the same lookup, the NYCHA violations dataset returned 25 violations: 12 in class A, 11 in class B, and 2 in class C, with the latest inspection date 2026-08-05. A low violation count at a NYCHA building is therefore not a sign of good condition.

How the site shows NYCHA buildings has not been decided.

### Known gaps in the building information

- Rows with no BBL are not counted in any section. The sizes are given above for evictions, HPD violations, HPD complaints, and HPD litigation. The sizes for the other sections have not been measured.
- Every section describes the tax lot, not one building.
- The numbers are live. Two visits on different days can give different numbers for the same building.
- A section can fail on its own, for example when NYC Open Data is slow. A failed section holds an error message, and it is not a count of 0.
- The NYCHA violations dataset is short: it starts in September 2025, and it has no open or closed status.
- The meaning of the rent impairing flag and of the hazardous category codes has not been compared with the source's own definitions.

### Left out on purpose, and future work

- Housing Court counts by ZIP code are not read by the building lookup. The site loads the ZIP code table separately and must label it as a neighborhood figure.
- HPD registration contacts are not used. They would need extra privacy work to separate company names from the names of individual people.
- Hearings of the Office of Administrative Trials and Hearings (OATH) are not used.
- The newer civil penalties in DOB Safety Violations are not read.
- Evictions with no BBL are not found by address. That would be a separate project.

### How the building lookup is checked

The folder `validation` holds a check of `building-profile.js` against 23 validation buildings.

- `validation/pull-baseline.mjs` asks NYC Open Data directly for the expected counts of the 23 buildings. It does not use `building-profile.js`, so the two can check each other. The expected counts are saved in `validation/validation-buildings.json`. They were last pulled on 2026-11-12. The plan is to pull them again about once a month.
- `validation/validate.mjs` finds each building the way the site does, runs `getBuildingProfile()`, and compares the result with the expected counts.
- A count passes if it is within 10 percent or 5 of the expected count, whichever is larger. An expected count of 0 must match exactly. The BBL and the BIN from the address search must match exactly.
- The check compares eight numbers for each building: the open HPD violations of class A, B, and C, the complaints in the last 12 months, the litigation cases, the harassment findings, the residential evictions, and the active ECB summonses.
- The check does not compare the NYCHA flag, the NYCHA violations, or the PLUTO values. Those were tested by hand on November 18, 2026, with two buildings: 1609 East 174 Street, which is a NYCHA building, and 530 East 169 Street, which is not. The results were as expected for both.
- A failure can mean that the data moved since the expected counts were pulled, and not that the code is wrong.

## Housing Court cases by ZIP code

### What this figure is, and what it is not

The table counts New York City Housing Court cases for each ZIP code (Zone Improvement Plan code), each year from 2016 to 2025, and each of two property groups.

It is a neighborhood signal. It is not a building signal. The source data has only the city, state, and ZIP code of the property for each case. It has no street address. So a count in this table says how many cases were filed for properties in that ZIP code. It does not say that any case was filed against one particular building, and it must never be shown as if it did.

The building lookup does not read this table. If Tenant Triage NYC shows a ZIP code count on a building's page, the site loads the table separately, and the count must be labeled as a ZIP code count for the neighborhood. How the site shows it has not been decided.

### Where the numbers come from

The source is a public extract that the Housing Data Coalition publishes from Office of Court Administration Housing Court records. The files are at https://oca-2-dev.s3.amazonaws.com/public/. The extract is de-identified. It holds no party names, no tenant names, and no addresses. Each case has a 64-character code, which this project never prints or publishes.

Two tables of the extract are used:

- `oca_index` has one row for each case. It gives the court, the filing date, the property type, and the case type.
- `oca_addresses` has the city, state, and ZIP code of the property. It is joined to `oca_index` on the case code.

The files cover all of New York State. This project reads them in full and keeps only the cases described below. The extract cannot be filtered by ZIP code on the server.

### What is counted

- Cases from these seven courts: the Bronx, Kings, New York, Queens, and Richmond County Civil Courts, the Harlem Community Justice Center, and the Red Hook Community Justice Center.
- Cases filed from 2016 to 2025.
- Cases with property type Residential, and cases with property type Commercial. They are shown as two property groups. The group `residential` counts Residential cases only. The group `plus commercial` counts Residential and Commercial cases together, so it already contains the residential cases. The two groups must never be added together.
- Nine case types, each in its own column: Non-Payment, Holdover, HP, Illegal Lockout, HP with Harassment, Harassment, Illegal Activity, Article 7A, and Breach of Warrant of Habitability. HP is the source's own label. A case with any other case type, or a blank one, is counted in a tenth column named `unclassified`.
- The ZIP code of a case is the first five characters of the ZIP code in the first address row of that case. About 4.5 percent of ZIP codes in the source have a dash and four more digits, and those extra digits are dropped. If a case has more than one address row, only the first is used.
- The 217 ZIP codes that appear on at least one New York City tax lot in PLUTO (Primary Land Use Tax Lot Output). Every one of them is in the table, including ZIP codes with no cases. Six of them have no case from 2016 to 2025: 10105, 10121, 10271, 10278, 10803, and 11695. They have a row for every year and group, with counts of 0.

The Harlem Community Justice Center and the Red Hook Community Justice Center are community courts listed on the New York City Civil Court pages of the New York State courts website (https://nycourts.gov/courts/nyc/civil/communitycourts.shtml). The source data spells the second one "Redhook Community Justice Center." The Harlem Community Justice Center handles landlord and tenant cases for ZIP codes 10035 and 10037. As of October 28, 2026, the courts website says it is temporarily closed and sends cases to the New York County Civil Court at 111 Centre Street (https://www.nycourts.gov/node/160101). Both courts are counted in the table, so the ZIP code counts are not affected. The Red Hook Community Justice Center handles housing cases from the Red Hook East and Red Hook West developments of the New York City Housing Authority.

The table has 4,340 rows: 217 ZIP codes times 10 years times 2 property groups. All values are counts of cases. The table has no rates.

### What is left out, and why

- Cases from courts outside New York City. The table is for New York City neighborhoods.
- Cases filed in 2026. The year was not finished when the table was built, so a 2026 count would not be comparable to a full year.
- Cases whose ZIP code is not one of the 217 ZIP codes. The first full build left out 1,612 cases for this reason in 2016 to 2025. Many of them have ZIP codes that look like placeholders: 00000, 11111, 99999, and 19999. That reading is an inference. It was not checked against the court.
- The first full build, on 2026-10-12, found 1,749,362 New York City cases in all years. It left out 106,132 filed in 2026 and 1,612 with a ZIP code not on the list. No case lacked an address row. It counted 1,641,618 cases. The rebuild on 2026-10-17 counted 1,641,618 cases again, in 4,340 rows. The numbers change when the source extract is updated.

### Known gaps in this table

- The ZIP code type rule is not enforced. The rule is to exclude ZIP codes used only for Post Office boxes and ZIP codes that belong to a single company or organization, and to include ZIP codes for buildings. No source of ZIP code types is used, so the build script uses only the PLUTO list of 217 ZIP codes that have at least one tax lot. The run record `ziptable_run.json` has the field `zip_type_rule_enforced`, and it is `false`. Some ZIP codes in the table may therefore be Post Office box ZIP codes or company ZIP codes. That has not been checked. The free ZIP code type list at zip-codes.com is not used, because its terms limit it to personal use. This project has not read those terms itself.
- The column descriptions of the source were inferred from the column names. The official Housing Data Coalition data dictionary could not be opened, so the descriptions have not been compared with it.
- No outside total exists to compare the counts with. The checks in the build script compare the table with other numbers produced by the same project. They show that the table agrees with itself. They do not show that the source data is correct, and they do not show that nine is the complete list of case types.
- Filings fell sharply in 2020 and 2021. The cause is probably the eviction moratorium. That is an inference and was not checked.
- The source files say they are updated weekly in one document and monthly in another. This is not resolved.
- A case counted here is a Housing Court case filed in a ZIP code. This table does not show how any case ended.

### How the table is checked

The build script (`ziptable_build.py`) saves nothing if any of these checks fails:

1. Every case is followed to one of four ends: counted, no address row, ZIP code excluded by the ZIP code type rule, or ZIP code not on the list. The counts at each end must add up to the cases read.
2. In every row, the nine case type columns plus `unclassified` add up to `total_cases`. The total is counted separately from the case types.
3. The `plus commercial` totals equal the number of counted cases.
4. The `plus commercial` count is at least the `residential` count in every ZIP code and year.
5. The table has exactly 217 times 10 times 2 rows, with no repeated ZIP code, year, and group.
6. No count is negative.
7. The saved file is read back and compared with the rows in memory. Every ZIP code has five digits. Every value except `zip` and `property_group` is made of digits only, so no name, address, or case code can reach those columns.
8. A property type other than Residential or Commercial stops the build.
9. A case type that is not one of the nine goes to `unclassified`, and the build prints a warning with the name.

### When the table was last built

The last full build recorded here ran on 2026-10-17 and wrote `ziptable.csv` and `ziptable_run.json`. The run record has the source update date. Where and how often the build runs is not decided.