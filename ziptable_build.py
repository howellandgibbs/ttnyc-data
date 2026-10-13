# ABOUT THIS FILE
#
# This file is called ziptable_build.py. It builds the ZIP table of Housing
# Court cases for Tenant Triage NYC. It reads two tables from the Housing
# Data Coalition, called HDC. The Housing Court data is also called the OCA
# data, because the Office of Court Administration collects it.
#
# The two tables are oca_index and oca_addresses. The oca_index table has
# one row for each court case, with the court, the filing date, the case
# type, and the property type. The oca_addresses table has the ZIP code of
# the property. Both tables carry the same case code, called indexnumberid.
# We use that code to attach a ZIP code to each case.
#
# These are the rules that Felix decided. Each rule is also a setting in
# step 2.
# - Only the five New York City borough civil courts and the two community
#   justice centers count.
# - Only cases filed from 2016 to 2025 count.
# - Only cases whose ZIP code is in the list of 217 New York City ZIP codes
#   count. The list comes from PLUTO, the New York City tax-lot file.
#   Cases with another ZIP code are left out, and the file counts them.
# - A case with more than one address uses its first address row.
# - The file counts only. It does not calculate rates.
# - Felix also decided that ZIP codes for P.O. boxes and for companies are
#   excluded, and ZIP codes for buildings are included. This rule is not
#   enforced yet, because no source of ZIP code types has been chosen. Step 2
#   has an empty list where the excluded ZIP codes will go.
#
# The result is a CSV table. A CSV file is a plain text file that holds a
# table, with one row on each line and commas between the values. The table
# has one row for each ZIP code, each year, and each property group. There
# are two property groups:
# - "residential" counts the cases with the property type Residential.
# - "plus commercial" counts the cases with the property type Residential
#   plus the cases with the property type Commercial.
# So a "plus commercial" row is always at least as big as the "residential"
# row for the same ZIP code and year. Do not add the two rows together,
# because the residential cases are already inside the "plus commercial" row.
#
# Every ZIP code in the table gets a row for every year, also when it had no
# cases. In that case every count is 0.
#
# Each row has these counts:
# - total_cases is the number of cases. It is counted on its own, without
#   looking at the case type.
# - Nine columns count the nine case types that we know.
# - The column unclassified counts the cases with any other case type, or
#   with no case type. The Master Plan asks for this column.
# The nine columns and the unclassified column must add up to total_cases.
# The file checks this for every row, and stops if one row does not add up.
#
# The file also checks that every case is accounted for. Each case from the
# New York City courts, filed inside the years, must end in exactly one of
# four places: counted in the table, no address row, ZIP code outside the
# list, or ZIP code excluded by the ZIP type rule. The file checks this for
# every year, property type, and case type.
#
# Before the table gets its real name, the file reads the saved file back
# and compares it with what it meant to write. A failed run never replaces a
# good file.
#
# Next to the table, the file writes a small run record. It holds the date
# of the source files, the number of cases that were left out and why, and
# any case types that were not on the list of nine.
#
# These checks show that the file is consistent with itself. They do not
# prove that the data from HDC is right, or that the nine case types are the
# only ones that exist. We have no outside number to compare with.
#
# The file does not save the Housing Court tables. It reads each table as it
# arrives and keeps only short numbers made from the case codes, and small
# counts. It never writes a case code.
#
# This file is a stand-alone helper for now. Keep it next to inspect_oca.py,
# outside the ttnyc-data folder. Later, its steps will move into the
# ttnyc-data pipeline.
#
# Python reads this file from top to bottom. The numbered steps below are
# in that same order. Steps 1 and 2 prepare the settings. Steps 3 to 11 each
# prepare one small piece of work. Step 12 puts the pieces together. Step 13
# starts step 12 when you run this file.
#
# This file only uses tools that come with Python. You do not need to
# install anything.
#
# How to run it on your computer:
#     python ziptable_build.py
#         This reads both tables completely and needs about 400 MB of
#         memory. It can take several minutes.



# 1. BRING IN THE TOOLS THIS FILE NEEDS
#
# Python comes with many ready-made tools. A file has to ask for each tool
# before it can use it. These lines ask for eleven tools.
#
# "sys" lets the file stop with a failure code.
#
# "csv" lets the file read and write a CSV file correctly. Some values
# contain commas inside quotation marks, and the csv tool understands that.
#
# "io" lets the file read the arriving bytes as text.
#
# "re" lets the file check the shape of a piece of text, such as "five
# digits".
#
# "json" lets the file read the answer of the New York City Open Data
# website, which comes in a format called JSON, and write the run record in
# the same format.
#
# "datetime" lets the file write down the date and time of the run.
#
# "Counter" is a tool that counts how often each value appears.
#
# "Path" lets the file work with the locations of files on the computer.
#
# "urllib.request" lets the file talk to a web address and read from it.
# "urllib.error" and "http.client" let the file understand what went wrong
# when a web address does not answer well.
import sys
import csv
import io
import re
import json
import datetime
import http.client
import urllib.request
import urllib.error
from collections import Counter
from pathlib import Path



# 2. THE SETTINGS
#
# BASE_URL is the web address of the folder where HDC keeps its public
# files. LAST_UPDATED_URL is a tiny text file in that folder. It holds the
# date when HDC last updated its files.
#
# ZIP_LIST_URL is the web address that gives the list of ZIP codes in PLUTO.
# It asks for each ZIP code once, and leaves out lots with no ZIP code.
#
# EXPECTED_ZIP_COUNT is the number of ZIP codes we found when we counted
# them by hand. If the list now has a different number, the file stops,
# because the table size would change without anyone deciding it.
#
# EXCLUDED_ZIP_CODES are the ZIP codes that the ZIP type rule removes. The
# rule says to exclude ZIP codes for P.O. boxes and for companies. The list
# is empty because no source of ZIP code types has been chosen yet. When it
# is filled in, those ZIP codes get no rows, and their cases are counted as
# left out for this reason. Every ZIP code in this list must also be in the
# list from PLUTO, or the file stops. This catches typing mistakes.
#
# NYC_COURTS are the court names that count as New York City. The five
# borough civil courts are certain. The two community justice centers,
# Harlem and Red Hook, are in the list because of their names. This is an
# assumption that we have not confirmed.
#
# FIRST_YEAR and LAST_YEAR are the years that the table holds.
#
# CASE_TYPE_COLUMNS connects each known case type, written as in the HDC
# file, to the name of its column in the table. The order here is the order
# of the columns. UNCLASSIFIED is the name of the extra column for every
# other case type.
#
# PROPERTY_TYPES are the two property types that we know. A case with any
# other property type stops the file, because it would change what the two
# property groups mean. GROUP_RESIDENTIAL and GROUP_PLUS_COMMERCIAL are the
# two values of the property group column.
#
# TABLE_PATH is where the table is saved. RUN_RECORD_PATH is where the run
# record is saved. Both are saved in the same folder as this file, so the
# file works on any computer. Do not keep this folder inside OneDrive.
#
# PROGRESS_EVERY is how many rows to read before printing a progress line.
#
# LEFT_OUT_ZIPS_SHOWN is how many left-out ZIP codes to list in the run
# record.
BASE_URL = "https://oca-2-dev.s3.amazonaws.com/public/"
LAST_UPDATED_URL = BASE_URL + "last-updated-date.txt"
ZIP_LIST_URL = (
    "https://data.cityofnewyork.us/resource/64uk-42ks.json"
    "?$select=zipcode&$group=zipcode&$where=zipcode%20IS%20NOT%20NULL&$limit=1000"
)
EXPECTED_ZIP_COUNT = 217
EXCLUDED_ZIP_CODES = set()
NYC_COURTS = {
    "Bronx County Civil Court",
    "Kings County Civil Court",
    "New York County Civil Court",
    "Queens County Civil Court",
    "Richmond County Civil Court",
    "Harlem Community Justice Center",
    "Redhook Community Justice Center",
}
FIRST_YEAR = 2016
LAST_YEAR = 2025
CASE_TYPE_COLUMNS = {
    "Non-Payment": "non_payment",
    "Holdover": "holdover",
    "HP": "hp",
    "Illegal Lockout": "illegal_lockout",
    "HP with Harassment": "hp_with_harassment",
    "Harassment": "harassment",
    "Illegal Activity": "illegal_activity",
    "Article 7A": "article_7a",
    "Breach of Warrant of Habitability": "breach_of_warrant_of_habitability",
}
UNCLASSIFIED = "unclassified"
PROPERTY_TYPES = {"Residential", "Commercial"}
GROUP_RESIDENTIAL = "residential"
GROUP_PLUS_COMMERCIAL = "plus commercial"
TABLE_PATH = Path(__file__).resolve().parent / "zip_housing_court.csv"
RUN_RECORD_PATH = Path(__file__).resolve().parent / "zip_housing_court_run.json"
PROGRESS_EVERY = 500_000
LEFT_OUT_ZIPS_SHOWN = 20



# 3. GET THE LIST OF NEW YORK CITY ZIP CODES
#
# This function asks the New York City Open Data website for every ZIP code
# that appears in PLUTO. It gives back a set of ZIP codes. A set remembers
# each value once.
#
# Each ZIP code is made into text with exactly five digits. A number such
# as 10451.0 becomes "10451". A ZIP code that does not have five digits
# after this is a problem, so the function stops with a clear message. The
# function also stops if the list does not have the expected number of ZIP
# codes.
def get_nyc_zip_codes():
    # 3.1 Ask for the list and read the answer as JSON.
    with urllib.request.urlopen(ZIP_LIST_URL, timeout=120) as answer:
        records = json.loads(answer.read().decode("utf-8"))



    # 3.2 Clean each ZIP code and check its shape.
    zip_codes = set()
    for record in records:
        zip_code = str(record.get("zipcode", "")).strip()
        if zip_code.endswith(".0"):
            zip_code = zip_code[:-2]
        if not re.fullmatch(r"\d{5}", zip_code):
            raise ValueError(f"PLUTO gave a ZIP code that is not five digits: {zip_code!r}")
        zip_codes.add(zip_code)



    # 3.3 Check the number of ZIP codes, then give back the set.
    if len(zip_codes) != EXPECTED_ZIP_COUNT:
        raise ValueError(
            f"PLUTO gave {len(zip_codes)} ZIP codes, but {EXPECTED_ZIP_COUNT} were expected. "
            "Check the list, then change EXPECTED_ZIP_COUNT in step 2 if the change is right."
        )
    return zip_codes



# 4. READ THE DATE OF THE SOURCE FILES
#
# This function reads the tiny text file in which HDC writes the date of its
# last update. It gives back that text. If the file cannot be read, it gives
# back "could not be read", and the run goes on, because this date is only
# information for the run record.
def get_source_last_updated():
    # 4.1 Read the text file.
    try:
        with urllib.request.urlopen(LAST_UPDATED_URL, timeout=30) as answer:
            return answer.read().decode("utf-8").strip()



    # 4.2 If the text file cannot be read, say so.
    except (urllib.error.URLError, OSError, UnicodeDecodeError):
        return "could not be read"



# 5. READ A TABLE ONE ROW AT A TIME
#
# This function opens one table on the internet and hands over its rows one
# at a time. It never keeps the whole table. For each row it hands over only
# the columns that we asked for, in the order that we asked for them.
#
# The function stops with a clear message if a column that we need is
# missing from the file. A row that is too short gets blank values for the
# missing columns.
def read_columns(name, needed_columns):
    # 5.1 Open the web address. The "with" block closes the connection when
    # we are done.
    url = BASE_URL + name + ".csv"
    with urllib.request.urlopen(url, timeout=120) as answer:
        # 5.2 Turn the arriving bytes into text. The name "utf-8-sig" also
        # removes an invisible mark that some programs put at the start of a
        # file. A byte that cannot be understood is replaced by a question
        # mark symbol, so the program does not stop.
        text = io.TextIOWrapper(answer, encoding="utf-8-sig", errors="replace", newline="")
        reader = csv.reader(text)



        # 5.3 The first row holds the column names. Find the position of
        # each column that we need. If one is missing, stop.
        header = next(reader, None)
        if not header:
            raise ValueError(f"{name} is empty")
        missing = [column for column in needed_columns if column not in header]
        if missing:
            raise ValueError(f"{name} has no column named: {', '.join(missing)}")
        positions = [header.index(column) for column in needed_columns]



        # 5.4 Hand over the wanted values of each row.
        for row in reader:
            yield tuple(row[position].strip() if position < len(row) else "" for position in positions)



# 6. FIRST PASS: READ oca_index
#
# This function reads oca_index and looks only at the cases from the New
# York City courts. It counts how many of them there are, and how many were
# filed outside the years of the table.
#
# For each New York City case filed inside the years, it remembers a short
# number made from the case code, together with the year, the case type, and
# the property type. To save memory, each different combination of these
# three values gets a number, and the case remembers only that number.
#
# The short number is made by Python from the case code. Two different codes
# could in theory give the same short number. That is extremely unlikely.
# If it ever happened, the check in step 8 would notice and stop the run.
#
# A case type that is not one of the nine known types is stored as
# "unclassified". The function also counts each such case type by its real
# name, so that the run record can list them. A blank case type is counted
# under the name "(blank)".
#
# The function also counts the cases for every combination. This count is
# made here, before the address table is read. Step 8 compares it with what
# happens to the cases later.
#
# If a case has a property type that we do not know, the function stops with
# a clear message.
def read_index_table():
    # 6.1 Prepare the empty places to remember things.
    nyc_cases = {}
    combination_numbers = {}
    combinations = []
    cases_by_combination = Counter()
    unknown_case_types = Counter()
    rows_read = 0
    nyc_cases_all_years = 0
    cases_outside_years = 0



    # 6.2 Go through the rows. Print a progress line from time to time.
    for case_code, court, filed_date, property_type, case_type in read_columns(
        "oca_index", ["indexnumberid", "court", "fileddate", "propertytype", "classification"]
    ):
        rows_read = rows_read + 1
        if rows_read % PROGRESS_EVERY == 0:
            print(f"  oca_index: {rows_read:,} rows read ...")



        # 6.3 Keep going only for the New York City courts.
        if court not in NYC_COURTS:
            continue
        nyc_cases_all_years = nyc_cases_all_years + 1



        # 6.4 The year is the first four characters of the filing date. A
        # case with another year, or with no usable year, is counted as
        # outside the years and not kept.
        year_text = filed_date[:4]
        if not (re.fullmatch(r"\d{4}", year_text) and FIRST_YEAR <= int(year_text) <= LAST_YEAR):
            cases_outside_years = cases_outside_years + 1
            continue



        # 6.5 Stop if the property type is not one that we know. If the
        # case type is not one that we know, store it as unclassified, and
        # count its real name.
        if property_type not in PROPERTY_TYPES:
            raise ValueError(f"oca_index has a property type that is not in step 2: {property_type!r}")
        if case_type in CASE_TYPE_COLUMNS:
            case_type_label = case_type
        else:
            case_type_label = UNCLASSIFIED
            unknown_case_types[case_type or "(blank)"] += 1



        # 6.6 Give this combination a number, if it has none yet, and
        # remember the number for this case. Count the case under its
        # combination.
        combination = (int(year_text), case_type_label, property_type)
        if combination not in combination_numbers:
            combination_numbers[combination] = len(combinations)
            combinations.append(combination)
        combination_number = combination_numbers[combination]
        nyc_cases[hash(case_code)] = combination_number
        cases_by_combination[combination_number] += 1



    # 6.7 Give back what we remembered and counted.
    return {
        "rows_read": rows_read,
        "nyc_cases": nyc_cases,
        "combinations": combinations,
        "cases_by_combination": cases_by_combination,
        "unknown_case_types": unknown_case_types,
        "nyc_cases_all_years": nyc_cases_all_years,
        "cases_outside_years": cases_outside_years,
    }



# 7. SECOND PASS: READ oca_addresses
#
# This function reads oca_addresses and looks only at the cases that step 6
# kept. The first address row of a case decides its ZIP code. A later
# address row of the same case is counted as an extra row and then ignored.
#
# Only the first five characters of the postal code are used as the ZIP
# code, because some values have four more numbers after a dash.
#
# It gives back the ZIP code of every case that has an address, and, for
# every pair of a ZIP code and a combination from step 6, how many cases
# there are.
def read_address_table(index_result):
    # 7.1 Prepare the empty places to remember things.
    nyc_cases = index_result["nyc_cases"]
    first_zip_of_case = {}
    zip_and_combination_counts = Counter()
    extra_rows = 0
    rows_read = 0



    # 7.2 Go through the rows. Print a progress line from time to time.
    for case_code, postal_code in read_columns("oca_addresses", ["indexnumberid", "postalcode"]):
        rows_read = rows_read + 1
        if rows_read % PROGRESS_EVERY == 0:
            print(f"  oca_addresses: {rows_read:,} rows read ...")



        # 7.3 Ignore the cases that step 6 did not keep.
        case_number = hash(case_code)
        combination_number = nyc_cases.get(case_number)
        if combination_number is None:
            continue



        # 7.4 If the case already has an address, this row is an extra row.
        if case_number in first_zip_of_case:
            extra_rows = extra_rows + 1
            continue



        # 7.5 This is the first address of the case. Remember its ZIP code
        # and count it together with the combination of the case.
        zip_code = postal_code[:5]
        first_zip_of_case[case_number] = zip_code
        zip_and_combination_counts[(zip_code, combination_number)] += 1



    # 7.6 Give back what we counted.
    return {
        "rows_read": rows_read,
        "first_zip_of_case": first_zip_of_case,
        "zip_and_combination_counts": zip_and_combination_counts,
        "extra_rows": extra_rows,
    }



# 8. FOLLOW EVERY CASE TO ITS END
#
# This function decides what happens to every New York City case that was
# filed inside the years. Each case ends in exactly one of four places:
# - counted in the table,
# - no address row,
# - ZIP code excluded by the ZIP type rule,
# - ZIP code not in the list of PLUTO.
#
# Then it checks that no case was lost or counted twice. For every
# combination of year, case type, and property type, the number of cases
# counted in step 6 must be the same as the number of cases that ended in one
# of the four places. If one combination does not match, the function stops
# with a clear message.
#
# It gives back the pairs of ZIP code and combination that are counted in
# the table, and the numbers for the run record.
def follow_cases(nyc_zip_codes, index_result, address_result):
    # 8.1 Sort every pair of a ZIP code and a combination into one of three
    # places. The fourth place, no address row, is found in step 8.2.
    combinations = index_result["combinations"]
    counted_pairs = Counter()
    counted_by_combination = Counter()
    excluded_by_combination = Counter()
    outside_list_by_combination = Counter()
    excluded_zip_counts = Counter()
    outside_list_zip_counts = Counter()
    for (zip_code, combination_number), count in address_result["zip_and_combination_counts"].items():
        if zip_code in EXCLUDED_ZIP_CODES:
            excluded_by_combination[combination_number] += count
            excluded_zip_counts[zip_code] += count
        elif zip_code in nyc_zip_codes:
            counted_pairs[(zip_code, combination_number)] += count
            counted_by_combination[combination_number] += count
        else:
            outside_list_by_combination[combination_number] += count
            outside_list_zip_counts[zip_code if re.fullmatch(r"\d{5}", zip_code) else "(not five digits)"] += count



    # 8.2 Find the cases with no address row. A case has an address row if
    # its short number is in the list of first ZIP codes.
    no_address_by_combination = Counter()
    first_zip_of_case = address_result["first_zip_of_case"]
    for case_number, combination_number in index_result["nyc_cases"].items():
        if case_number not in first_zip_of_case:
            no_address_by_combination[combination_number] += 1



    # 8.3 Check every combination. The cases counted in step 6 must be the
    # same as the cases in the four places.
    for combination_number, combination in enumerate(combinations):
        found = (
            counted_by_combination[combination_number]
            + excluded_by_combination[combination_number]
            + outside_list_by_combination[combination_number]
            + no_address_by_combination[combination_number]
        )
        expected = index_result["cases_by_combination"][combination_number]
        if found != expected:
            raise ValueError(
                f"Cases were lost or counted twice for year {combination[0]}, case type "
                f"{combination[1]}, property type {combination[2]}: {expected:,} cases were "
                f"read from oca_index, but {found:,} were followed to the end."
            )



    # 8.4 Put together the numbers for the run record.
    numbers = {
        "new_york_city_cases_all_years": index_result["nyc_cases_all_years"],
        "left_out_filed_outside_the_years": index_result["cases_outside_years"],
        "new_york_city_cases_inside_the_years": sum(index_result["cases_by_combination"].values()),
        "left_out_no_address_row": sum(no_address_by_combination.values()),
        "left_out_zip_excluded_by_type_rule": sum(excluded_by_combination.values()),
        "left_out_zip_not_in_list": sum(outside_list_by_combination.values()),
        "counted_in_the_table": sum(counted_by_combination.values()),
        "extra_address_rows_ignored": address_result["extra_rows"],
        "left_out_zip_not_in_list_biggest": dict(outside_list_zip_counts.most_common(LEFT_OUT_ZIPS_SHOWN)),
        "left_out_zip_excluded_by_type_rule_by_zip": dict(excluded_zip_counts),
        "case_types_not_on_the_list_of_nine": dict(index_result["unknown_case_types"]),
    }
    return counted_pairs, numbers



# 9. BUILD THE ROWS OF THE TABLE
#
# This function turns the counted pairs into the rows of the table. It gives
# back the list of rows.
#
# The total of each row is counted on its own. The function makes two
# separate counts from the same pairs:
# - The first count only looks at the ZIP code, the year, and the property
#   type. It does not look at the case type. This is the total.
# - The second count also looks at the case type. This gives the nine
#   known case types and the unclassified column.
# Step 10 then checks that the second count adds up to the first.
#
# Every ZIP code in the table gets a row for every year and for both
# property groups, also when it has no cases.
def build_table_rows(table_zip_codes, index_result, counted_pairs):
    # 9.1 Make the two counts.
    combinations = index_result["combinations"]
    total_counts = Counter()
    type_counts = Counter()
    for (zip_code, combination_number), count in counted_pairs.items():
        year, case_type_label, property_type = combinations[combination_number]
        total_counts[(zip_code, year, property_type)] += count
        type_counts[(zip_code, year, property_type, case_type_label)] += count



    # 9.2 Build the rows. The residential group counts the cases with the
    # property type Residential. The plus commercial group adds the cases
    # with the property type Commercial.
    rows = []
    for zip_code in sorted(table_zip_codes):
        for year in range(FIRST_YEAR, LAST_YEAR + 1):
            for group, property_types in (
                (GROUP_RESIDENTIAL, ("Residential",)),
                (GROUP_PLUS_COMMERCIAL, ("Residential", "Commercial")),
            ):
                row = {"zip": zip_code, "year": year, "property_group": group}
                row["total_cases"] = sum(total_counts[(zip_code, year, property_type)] for property_type in property_types)
                for case_type, column in CASE_TYPE_COLUMNS.items():
                    row[column] = sum(type_counts[(zip_code, year, property_type, case_type)] for property_type in property_types)
                row[UNCLASSIFIED] = sum(type_counts[(zip_code, year, property_type, UNCLASSIFIED)] for property_type in property_types)
                rows.append(row)



    # 9.3 Give back the rows.
    return rows



# 10. CHECK THE ROWS BEFORE ANYTHING IS SAVED
#
# This function checks the rows and the numbers from step 8. If any check
# fails, it stops with a clear message, and nothing is saved.
#
# The checks are:
# - The number of rows is the number of ZIP codes times the number of years
#   times two groups.
# - No ZIP code, year, and group appears twice.
# - In every row, the nine case types and the unclassified column add up to
#   the total, which was counted on its own.
# - No count is negative.
# - In every ZIP code and year, the plus commercial row is at least as big
#   as the residential row, for the total and for each column.
# - The total of all plus commercial rows is the number of counted cases.
def check_rows(rows, numbers, table_zip_codes):
    # 10.1 Check the number of rows and look for duplicates.
    years = LAST_YEAR - FIRST_YEAR + 1
    expected_rows = len(table_zip_codes) * years * 2
    if len(rows) != expected_rows:
        raise ValueError(f"The table has {len(rows)} rows, but {expected_rows} were expected.")
    keys = {(row["zip"], row["year"], row["property_group"]) for row in rows}
    if len(keys) != len(rows):
        raise ValueError("The table has the same ZIP code, year, and group twice.")



    # 10.2 Check each row. The columns must add up to the total, and no
    # count may be negative.
    columns = list(CASE_TYPE_COLUMNS.values()) + [UNCLASSIFIED]
    for row in rows:
        if any(row[column] < 0 for column in columns + ["total_cases"]):
            raise ValueError(f"A count is negative in {row['zip']} {row['year']}.")
        if row["total_cases"] != sum(row[column] for column in columns):
            raise ValueError(
                f"The case types do not add up to the total in {row['zip']} {row['year']} "
                f"{row['property_group']}: total {row['total_cases']}, case types {sum(row[column] for column in columns)}."
            )



    # 10.3 Check that the plus commercial row is at least as big as the
    # residential row. The rows come in pairs: residential first, plus
    # commercial second.
    for position in range(0, len(rows), 2):
        residential = rows[position]
        plus_commercial = rows[position + 1]
        if residential["property_group"] != GROUP_RESIDENTIAL or plus_commercial["property_group"] != GROUP_PLUS_COMMERCIAL:
            raise ValueError("The rows are not in pairs of residential and plus commercial.")
        for column in columns + ["total_cases"]:
            if plus_commercial[column] < residential[column]:
                raise ValueError(f"Plus commercial is smaller than residential in {residential['zip']} {residential['year']}.")



    # 10.4 Check that the totals add up to the number of counted cases.
    plus_commercial_total = sum(row["total_cases"] for row in rows if row["property_group"] == GROUP_PLUS_COMMERCIAL)
    if plus_commercial_total != numbers["counted_in_the_table"]:
        raise ValueError(
            f"The plus commercial rows add up to {plus_commercial_total:,}, "
            f"but {numbers['counted_in_the_table']:,} cases were counted."
        )



# 11. SAVE THE FILES, AND READ THE TABLE BACK
#
# This function saves the table and the run record. It writes each file
# under a temporary name that ends in ".part". Then it reads the table back
# from the disk and compares it with the rows in memory. Only when that
# check passes does it rename the files to their real names. If anything
# goes wrong, it deletes the temporary files and stops, and the old files
# stay as they were.
#
# The check of the saved table has these parts:
# - The column names are exactly the expected ones, in the expected order.
# - The number of rows is the same, and no row has extra values.
# - Every value is the same as in memory.
# - Every ZIP code has exactly five digits.
# - Every value, except the property group, is a whole number made of digits
#   only. So the file cannot hold text such as names or case codes.
#
# The run record holds only counts, settings, and dates. It holds no case
# code.
def save_outputs(rows, numbers, source_last_updated, source_row_counts, table_zip_codes):
    # 11.1 Work out the temporary names and make the folders.
    table_part = TABLE_PATH.with_name(TABLE_PATH.name + ".part")
    record_part = RUN_RECORD_PATH.with_name(RUN_RECORD_PATH.name + ".part")
    TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUN_RECORD_PATH.parent.mkdir(parents=True, exist_ok=True)
    column_names = ["zip", "year", "property_group", "total_cases"] + list(CASE_TYPE_COLUMNS.values()) + [UNCLASSIFIED]



    # 11.2 Write the table and the run record under the temporary names,
    # then read the table back and check it. If a check fails, or a file
    # cannot be written, delete the temporary files and pass the problem on.
    try:
        with open(table_part, "w", encoding="utf-8", newline="") as table_file:
            writer = csv.DictWriter(table_file, fieldnames=column_names)
            writer.writeheader()
            writer.writerows(rows)
        check_saved_table(table_part, rows, column_names)
        record = {
            "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "source_files_last_updated": source_last_updated,
            "source_rows_read": source_row_counts,
            "courts_used": sorted(NYC_COURTS),
            "first_year": FIRST_YEAR,
            "last_year": LAST_YEAR,
            "zip_codes_in_table": len(table_zip_codes),
            "zip_type_rule_enforced": bool(EXCLUDED_ZIP_CODES),
            "table_rows": len(rows),
            "table_columns": column_names,
            "cases": numbers,
            "checks_passed": [
                "every case followed to its end, for every year, case type, and property type",
                "case types and unclassified add up to the total counted on its own, in every row",
                "plus commercial is at least residential, in every ZIP code and year",
                "saved file read back and equal to the rows in memory",
            ],
        }
        with open(record_part, "w", encoding="utf-8") as record_file:
            json.dump(record, record_file, indent=2)
            record_file.write("\n")
    except (ValueError, OSError):
        for part in (table_part, record_part):
            if part.exists():
                part.unlink()
        raise



    # 11.3 Both files are complete and checked. Give them their real names.
    table_part.replace(TABLE_PATH)
    record_part.replace(RUN_RECORD_PATH)



def check_saved_table(part_path, rows, column_names):
    # 11.4 Read the saved table back.
    with open(part_path, "r", encoding="utf-8", newline="") as saved_file:
        reader = csv.DictReader(saved_file)
        if reader.fieldnames != column_names:
            raise ValueError("The saved table has different column names than expected.")
        saved_rows = list(reader)



    # 11.5 Compare the number of rows, then every row and every value.
    if len(saved_rows) != len(rows):
        raise ValueError(f"The saved table has {len(saved_rows)} rows, but {len(rows)} were expected.")
    for saved_row, row in zip(saved_rows, rows):
        if None in saved_row or any(value is None for value in saved_row.values()):
            raise ValueError("A row of the saved table has too many or too few values.")
        if not re.fullmatch(r"\d{5}", saved_row["zip"]):
            raise ValueError(f"The saved table has a ZIP code that is not five digits: {saved_row['zip']!r}")
        for column in column_names:
            if saved_row[column] != str(row[column]):
                raise ValueError(f"The saved table differs from memory in {row['zip']} {row['year']}, column {column}.")
            if column != "property_group" and not re.fullmatch(r"\d+", saved_row[column]):
                raise ValueError(f"The saved table has a value that is not a whole number in column {column}.")



# 12. BUILD THE TABLE
#
# This function runs the steps in order: get the ZIP list, read the source
# date, read oca_index, read oca_addresses, follow every case, build the
# rows, check them, save them, read the table back, and print a short
# summary. If something cannot be read, or a check fails, it prints what went
# wrong and ends with a failure code. In that case, the old files stay as
# they were.
def main():
    # 12.1 Run the steps that read from the internet and check the result.
    # The ZIP codes of the table are the PLUTO ZIP codes, minus the ones
    # excluded by the ZIP type rule. Every excluded ZIP code must be in the
    # PLUTO list.
    try:
        print("Getting the ZIP code list from PLUTO ...")
        nyc_zip_codes = get_nyc_zip_codes()
        unknown_excluded = EXCLUDED_ZIP_CODES - nyc_zip_codes
        if unknown_excluded:
            raise ValueError(f"EXCLUDED_ZIP_CODES has ZIP codes that are not in the PLUTO list: {sorted(unknown_excluded)}")
        table_zip_codes = nyc_zip_codes - EXCLUDED_ZIP_CODES
        source_last_updated = get_source_last_updated()
        print("Reading oca_index ...")
        index_result = read_index_table()
        print("Reading oca_addresses ...")
        address_result = read_address_table(index_result)
        counted_pairs, numbers = follow_cases(nyc_zip_codes, index_result, address_result)
        rows = build_table_rows(table_zip_codes, index_result, counted_pairs)
        check_rows(rows, numbers, table_zip_codes)
    except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError, csv.Error) as error:
        print(f"FAILED. Nothing was saved. {error}")
        sys.exit(1)



    # 12.2 Save the files and check the saved table. If this fails, say so
    # and stop. The old files stay as they were.
    try:
        save_outputs(
            rows,
            numbers,
            source_last_updated,
            {"oca_index": index_result["rows_read"], "oca_addresses": address_result["rows_read"]},
            table_zip_codes,
        )
    except (ValueError, OSError) as error:
        print(f"FAILED. The files were not saved. {error}")
        sys.exit(1)



    # 12.3 Print a short summary. Warn loudly if some cases have a case type
    # that is not on the list of nine, or if the ZIP type rule is not
    # enforced.
    print()
    print(f"Source files last updated: {source_last_updated}")
    print(f"Table saved to: {TABLE_PATH} ({len(rows):,} rows)")
    print(f"Run record saved to: {RUN_RECORD_PATH}")
    for name, value in numbers.items():
        if not isinstance(value, dict):
            print(f"  {name}: {value:,}")
    if numbers["case_types_not_on_the_list_of_nine"]:
        print("WARNING: some cases have a case type that is not on the list of nine. They are in the unclassified column:")
        for case_type, count in numbers["case_types_not_on_the_list_of_nine"].items():
            print(f"    {count:,}  {case_type}")
    if not EXCLUDED_ZIP_CODES:
        print("NOTE: the ZIP type rule (exclude P.O. box and company ZIP codes) is not enforced. EXCLUDED_ZIP_CODES is empty.")
    print("All checks passed. The saved table was read back and matches.")



# 13. START THE FILE
#
# The line "if __name__ == '__main__'" is true only when you start this
# file directly, by typing "python ziptable_build.py". It is not true when
# another file imports this file. That way, importing this file never
# starts a request by accident.
if __name__ == "__main__":
    main()