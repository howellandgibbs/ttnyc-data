# Methodology

Author: Felix Suwarno
Last updated: 2026-10-28

This file currently explains only one table: the Housing Court cases by ZIP code table. The building-level data has no section here yet.

## Housing Court cases by ZIP code

### What this figure is, and what it is not

The table counts New York City Housing Court cases for each ZIP code (Zone Improvement Plan code), each year from 2016 to 2025, and each of two property groups.

It is a neighborhood signal. It is not a building signal. The source data has only the city, state, and ZIP code of the property for each case. It has no street address. So a count in this table says how many cases were filed for properties in that ZIP code. It does not say that any case was filed against one particular building, and it must never be shown as if it did.

If Tenant Triage NYC shows a ZIP code count on a building's page, the count must be labeled as a ZIP code count for the neighborhood. How the site shows it has not been decided.

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

- The ZIP code type rule is not enforced. The rule is to exclude ZIP codes used only for Post Office boxes and ZIP codes that belong to a single company or organization, and to include ZIP codes for buildings. No source of ZIP code types has been chosen, so the build script uses only the PLUTO list. The run record `ziptable_run.json` has the field `zip_type_rule_enforced`, and it is `false`. Some ZIP codes in the table may therefore be Post Office box ZIP codes or company ZIP codes. That has not been checked.
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