# ttnyc-data

This repository holds the data work for Tenant Triage NYC. It uses public New York City data about housing, evictions, and Housing Court.

## What the project produces

- **ZIP code table.** For each ZIP code and each year from 2016 to 2025, the number of Housing Court cases. The counts are split by case type and by property group (residential only, and residential plus commercial).
- **Building information.** This is not built in this repository. The website looks up each building when a visitor searches an address.
- Housing Court counts describe a neighborhood. They are never facts about one building.

## Files in this repository

### ZIP code table

- `ziptable_build.py` builds the ZIP code table. It reads the Housing Court files shared by the Housing Data Coalition and the list of ZIP codes from the New York City Department of City Planning.
- `zip_housing_court.csv` is the ZIP code table. It has 4,340 rows: 217 ZIP codes, 10 years, and 2 property groups.
- `zip_housing_court_run.json` records the counts from the build, including how many cases were left out and why.
- `ziptable_column_profile.py` reads the table and writes a plain-text description of every column.

### Housing Court exploration scripts

- `ziptable_oca_column_profile.py` describes every column of two Housing Court tables from the Office of Court Administration.
- `ziptable_oca_join_check.py` checks that the two Housing Court tables match each other, and reports any gaps.

### Housing Preservation and Development buildings scripts

- `HPD_buildings_column_profile.py` downloads the whole Buildings Subject to Housing Preservation and Development Jurisdiction table and describes every column.
- `HPD_buildings_download_zip_10456.py` downloads the rows of that table for ZIP code 10456, as a sample to check.

### Documents

- `docs/` holds the plain-text column descriptions that the scripts write.

## How to run a script

- Install Python 3. The scripts use only tools that come with Python, so nothing else needs to be installed.
- Open a terminal in the folder that holds the script.
- Type `python` followed by the script name. For example: `python ziptable_build.py`
- Each script saves its output files in the same folder as the script.
- `ziptable_build.py` needs about 400 megabytes of free memory and several minutes.
- Each script's first lines explain what it does and what it does not do.

## The Socrata app token

- The two Housing Preservation and Development scripts can use a free Socrata app token. The token lets New York City Open Data send data faster.
- The token is optional. Without it, the scripts still run, but more slowly.
- To use a token, store it in a computer setting named `SOCRATA_APP_TOKEN`. Never write the token inside a script or upload it to this repository.

## What must never be uploaded

This repository is public. Never upload:

- downloaded data files that hold rows of cases, apartments, or addresses (for example, the sample files the download scripts save)
- Socrata app tokens or any other password
- any file that names a person
