# ABOUT THIS FILE
#
# This file is called ziptable_oca_join_check.py. It checks whether the two Housing
# Court tables from the Housing Data Coalition, called HDC, fit together
# well enough to build the ZIP table. The Housing Court data is also called
# the OCA data, because the Office of Court Administration collects it.
#
# The two tables are oca_index and oca_addresses. The oca_index table has
# one row for each court case, with the court, the filing date, and the case
# type. The oca_addresses table has the ZIP code of the property. Both
# tables carry the same case code, called indexnumberid. We use that code to
# attach a ZIP code to each case.
#
# The file keeps only the cases from the New York City courts. These are
# the five borough civil courts and the two community justice centers. The
# list is in step 2.
#
# The file answers these questions:
# - How many New York City cases have no address row at all?
# - How many have a ZIP code that is not in the list of 217 New York City
#   ZIP codes?
# - How many have a blank property type, and does the blank share change from
#   year to year?
# - Do some cases have more than one address, with different ZIP codes?
# - Are there address rows whose case code is not in oca_index at all?
# - How many cases would the ZIP table hold for 2016 to 2025?
# - Does any of the 217 ZIP codes have no cases at all?
#
# The list of 217 ZIP codes comes from PLUTO, the New York City tax-lot
# file, on the New York City Open Data website. The file asks for it when it
# starts. A ZIP code is in the list if it appears on at least one New York
# City lot.
#
# The file does not save the Housing Court tables. It reads each table as it
# arrives and keeps only short numbers made from the case codes, and small
# counts. It never prints a case code.
#
# The file does not change the Tenant Triage project. It is a separate
# helper.
#
# Python reads this file from top to bottom. The numbered steps below are
# in that same order. Steps 1 and 2 prepare the settings. Steps 3 to 8 each
# prepare one small piece of work. Step 9 puts the pieces together. Step 10
# starts step 9 when you run this file.
#
# This file only uses tools that come with Python. You do not need to
# install anything.
#
# How to run it on your computer:
#     python ziptable_oca_join_check.py
#         This reads both tables completely and needs about 500 MB of
#         memory. It can take several minutes.



# 1. BRING IN THE TOOLS THIS FILE NEEDS
#
# Python comes with many ready-made tools. A file has to ask for each tool
# before it can use it. These lines ask for nine tools.
#
# "sys" lets the file stop with a failure code.
#
# "csv" lets the file read a CSV file correctly. A CSV file is a plain text
# file that holds a table, with one row on each line and commas between the
# values. Some values contain commas inside quotation marks, and the csv
# tool understands that.
#
# "io" lets the file read the arriving bytes as text.
#
# "re" lets the file check the shape of a piece of text, such as "five
# digits".
#
# "json" lets the file read the answer of the New York City Open Data
# website, which comes in a format called JSON.
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
import http.client
import urllib.request
import urllib.error
from collections import Counter
from pathlib import Path



# 2. THE SETTINGS
#
# BASE_URL is the web address of the folder where HDC keeps its public
# files.
#
# ZIP_LIST_URL is the web address that gives the list of ZIP codes in PLUTO.
# It asks for each ZIP code once, and leaves out lots with no ZIP code.
#
# EXPECTED_ZIP_COUNT is the number of ZIP codes we found when we counted
# them by hand. If the list now has a different number, the report says so.
#
# NYC_COURTS are the court names that count as New York City. The five
# borough civil courts are certain. The two community justice centers,
# Harlem and Red Hook, are in the list because of their names. This is an
# assumption that we have not confirmed.
#
# FIRST_YEAR and LAST_YEAR are the years that the ZIP table will hold.
#
# REPORT_PATH is the place on your computer where the report is saved. It is
# saved in the same folder as this file, so the file works on any computer.
# Do not keep this folder inside OneDrive.
#
# PROGRESS_EVERY is how many rows to read before printing a progress line.
#
# TOP_ZIPS_SHOWN is how many ZIP codes to show in the lists of biggest ZIP
# codes and of outside ZIP codes.
BASE_URL = "https://oca-2-dev.s3.amazonaws.com/public/"
ZIP_LIST_URL = (
    "https://data.cityofnewyork.us/resource/64uk-42ks.json"
    "?$select=zipcode&$group=zipcode&$where=zipcode%20IS%20NOT%20NULL&$limit=1000"
)
EXPECTED_ZIP_COUNT = 217
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
REPORT_PATH = Path(__file__).resolve().parent / "ziptable_oca_join_check.txt"
PROGRESS_EVERY = 500_000
TOP_ZIPS_SHOWN = 15



# 3. GET THE LIST OF NEW YORK CITY ZIP CODES
#
# This function asks the New York City Open Data website for every ZIP code
# that appears in PLUTO. It gives back a set of ZIP codes. A set remembers
# each value once.
#
# Each ZIP code is made into text with exactly five digits. A number such
# as 10451.0 becomes "10451". A ZIP code that does not have five digits
# after this is a problem, so the function stops with a clear message.
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



    # 3.3 Give back the set.
    return zip_codes



# 4. READ A TABLE ONE ROW AT A TIME
#
# This function opens one table on the internet and hands over its rows one
# at a time. It never keeps the whole table. For each row it hands over only
# the columns that we asked for, in the order that we asked for them.
#
# The function stops with a clear message if a column that we need is
# missing from the file. A row that is too short gets blank values for the
# missing columns.
def read_columns(name, needed_columns):
    # 4.1 Open the web address. The "with" block closes the connection when
    # we are done.
    url = BASE_URL + name + ".csv"
    with urllib.request.urlopen(url, timeout=120) as answer:
        # 4.2 Turn the arriving bytes into text. The name "utf-8-sig" also
        # removes an invisible mark that some programs put at the start of a
        # file. A byte that cannot be understood is replaced by a question
        # mark symbol, so the program does not stop.
        text = io.TextIOWrapper(answer, encoding="utf-8-sig", errors="replace", newline="")
        reader = csv.reader(text)



        # 4.3 The first row holds the column names. Find the position of
        # each column that we need. If one is missing, stop.
        header = next(reader, None)
        if not header:
            raise ValueError(f"{name} is empty")
        missing = [column for column in needed_columns if column not in header]
        if missing:
            raise ValueError(f"{name} has no column named: {', '.join(missing)}")
        positions = [header.index(column) for column in needed_columns]



        # 4.4 Hand over the wanted values of each row.
        for row in reader:
            yield tuple(row[position].strip() if position < len(row) else "" for position in positions)



# 5. FIRST PASS: READ oca_index
#
# This function reads oca_index and remembers two things.
#
# First, it remembers a short number for every case code in the table. This
# lets step 6 find out if an address belongs to a case that is missing from
# oca_index. The short number is made by Python from the code. Two different
# codes could in theory give the same short number. That is extremely
# unlikely, and it would not change what we learn.
#
# Second, for the cases from the New York City courts only, it remembers the
# court, the filing year, the case type, and the property type. To save
# memory, each different combination of these four values gets a number,
# and the case remembers only that number.
#
# It gives back everything it remembered.
def read_index_table():
    # 5.1 Prepare the empty places to remember things.
    all_case_numbers = set()
    nyc_cases = {}
    combination_numbers = {}
    combinations = []
    rows_read = 0



    # 5.2 Go through the rows. Remember the short number of every case.
    for case_code, court, filed_date, property_type, case_type in read_columns(
        "oca_index", ["indexnumberid", "court", "fileddate", "propertytype", "classification"]
    ):
        rows_read = rows_read + 1
        case_number = hash(case_code)
        all_case_numbers.add(case_number)



        # 5.3 Keep going only for the New York City courts.
        if court in NYC_COURTS:
            # 5.4 The year is the first four characters of the filing date,
            # but only if they are four digits. The property type and the
            # case type get a label when they are blank.
            year = filed_date[:4] if re.fullmatch(r"\d{4}", filed_date[:4]) else "(blank or odd)"
            combination = (court, year, case_type or "(blank)", property_type or "(blank)")



            # 5.5 Give this combination a number, if it has none yet, and
            # remember the number for this case.
            if combination not in combination_numbers:
                combination_numbers[combination] = len(combinations)
                combinations.append(combination)
            nyc_cases[case_number] = combination_numbers[combination]



        # 5.6 Print a progress line from time to time.
        if rows_read % PROGRESS_EVERY == 0:
            print(f"  oca_index: {rows_read:,} rows read ...")



    # 5.7 Give back what we remembered.
    return {
        "rows_read": rows_read,
        "all_case_numbers": all_case_numbers,
        "nyc_cases": nyc_cases,
        "combinations": combinations,
    }



# 6. SECOND PASS: READ oca_addresses
#
# This function reads oca_addresses. For every address row it asks three
# questions in this order.
#
# Is the case code missing from oca_index? Then the row is counted as an
# orphan row and nothing else happens.
#
# Is the case outside the New York City courts? Then the row is ignored.
#
# Otherwise the row belongs to a New York City case. The first address row
# of a case decides its ZIP code. A later address row of the same case is
# counted as an extra row, and the file checks if its ZIP code is different.
#
# Only the first five characters of the postal code are used as the ZIP
# code, because some values have four more numbers after a dash.
#
# It gives back everything it counted.
def read_address_table(index_result):
    # 6.1 Prepare the empty places to remember things.
    all_case_numbers = index_result["all_case_numbers"]
    nyc_cases = index_result["nyc_cases"]
    first_zip_of_case = {}
    zip_and_combination_counts = Counter()
    orphan_rows = 0
    orphan_case_numbers = set()
    extra_rows = 0
    extra_rows_with_other_zip = 0
    first_rows_outside_new_york_state = 0
    rows_read = 0



    # 6.2 Go through the rows. Print a progress line from time to time.
    for case_code, state, postal_code in read_columns("oca_addresses", ["indexnumberid", "state", "postalcode"]):
        rows_read = rows_read + 1
        case_number = hash(case_code)
        if rows_read % PROGRESS_EVERY == 0:
            print(f"  oca_addresses: {rows_read:,} rows read ...")



        # 6.3 Question one: is the case code missing from oca_index?
        if case_number not in all_case_numbers:
            orphan_rows = orphan_rows + 1
            orphan_case_numbers.add(case_number)
            continue



        # 6.4 Question two: is the case outside the New York City courts?
        combination_number = nyc_cases.get(case_number)
        if combination_number is None:
            continue



        # 6.5 This is a New York City case. Cut the postal code to five
        # characters.
        zip_code = postal_code[:5]



        # 6.6 If the case already has an address, this row is an extra row.
        # Count it, and check if its ZIP code differs from the first one.
        if case_number in first_zip_of_case:
            extra_rows = extra_rows + 1
            if first_zip_of_case[case_number] != zip_code:
                extra_rows_with_other_zip = extra_rows_with_other_zip + 1
            continue



        # 6.7 This is the first address of the case. Remember its ZIP code,
        # and count it together with the combination of the case.
        first_zip_of_case[case_number] = zip_code
        zip_and_combination_counts[(zip_code, combination_number)] += 1
        if state != "New York":
            first_rows_outside_new_york_state = first_rows_outside_new_york_state + 1



    # 6.8 Give back what we counted.
    return {
        "rows_read": rows_read,
        "first_zip_of_case": first_zip_of_case,
        "zip_and_combination_counts": zip_and_combination_counts,
        "orphan_rows": orphan_rows,
        "orphan_cases": len(orphan_case_numbers),
        "extra_rows": extra_rows,
        "extra_rows_with_other_zip": extra_rows_with_other_zip,
        "first_rows_outside_new_york_state": first_rows_outside_new_york_state,
    }



# 7. TURN THE COUNTS INTO A REPORT
#
# This function takes everything counted in steps 5 and 6, and the list of
# New York City ZIP codes, and builds the lines of the report. It gives the
# lines back as a list. It does not print them.
#
# A small helper, "share", turns two numbers into a percentage text.
def share(part, whole):
    return f"{100 * part / whole:.1f}%" if whole else "n/a"



def build_report(nyc_zip_codes, index_result, address_result):
    # 7.1 Get the pieces that we need.
    nyc_cases = index_result["nyc_cases"]
    combinations = index_result["combinations"]
    first_zip_of_case = address_result["first_zip_of_case"]
    pair_counts = address_result["zip_and_combination_counts"]
    nyc_total = len(nyc_cases)
    lines = ["JOIN CHECK OF THE HOUSING COURT TABLES", ""]



    # 7.2 Report the sizes of the tables and the ZIP list.
    lines.append(f"oca_index rows read: {index_result['rows_read']:,}")
    lines.append(f"oca_addresses rows read: {address_result['rows_read']:,}")
    lines.append(f"ZIP codes in PLUTO: {len(nyc_zip_codes)} (expected {EXPECTED_ZIP_COUNT})")
    if len(nyc_zip_codes) != EXPECTED_ZIP_COUNT:
        lines.append("WARNING: the number of ZIP codes is different from what we counted by hand.")
    lines.append("")



    # 7.3 Report the New York City cases by court. Also say if one of the
    # court names was never seen, which would mean a spelling mistake.
    cases_by_court = Counter()
    for combination_number in nyc_cases.values():
        cases_by_court[combinations[combination_number][0]] += 1
    lines.append(f"CASES IN THE NEW YORK CITY COURTS: {nyc_total:,}")
    for court in sorted(NYC_COURTS):
        lines.append(f"  {cases_by_court[court]:>10,}  {court}")
    for court in sorted(NYC_COURTS):
        if cases_by_court[court] == 0:
            lines.append(f"WARNING: no case was found for the court name {court!r}.")
    lines.append("")



    # 7.4 Report the cases that have no address row at all, split by court.
    # A case has an address row if its short number is in the list of first
    # ZIP codes.
    no_address_by_court = Counter()
    for case_number, combination_number in nyc_cases.items():
        if case_number not in first_zip_of_case:
            no_address_by_court[combinations[combination_number][0]] += 1
    no_address_total = sum(no_address_by_court.values())
    lines.append(f"CASES WITH NO ADDRESS ROW: {no_address_total:,} ({share(no_address_total, nyc_total)})")
    for court, count in no_address_by_court.most_common():
        lines.append(f"  {count:>10,}  {court}")
    lines.append("")



    # 7.5 Report the extra address rows and the orphan address rows.
    lines.append("MORE THAN ONE ADDRESS, AND ORPHANS")
    lines.append(f"  Extra address rows for New York City cases: {address_result['extra_rows']:,}")
    lines.append(f"  Of those, rows with a different ZIP code: {address_result['extra_rows_with_other_zip']:,}")
    lines.append(f"  Address rows whose case code is not in oca_index: {address_result['orphan_rows']:,}")
    lines.append(f"  Different case codes among those rows: {address_result['orphan_cases']:,}")
    lines.append(f"  New York City cases whose first address is outside New York State: {address_result['first_rows_outside_new_york_state']:,}")
    lines.append("")



    # 7.6 Count the cases by ZIP code. Split them into cases whose ZIP code
    # is in the list, and cases whose ZIP code is not. For the cases not in
    # the list, separate the ZIP codes that do not have five digits.
    cases_with_zip = sum(pair_counts.values())
    cases_in_list = 0
    outside_zip_counts = Counter()
    cases_by_zip = Counter()
    for (zip_code, combination_number), count in pair_counts.items():
        if zip_code in nyc_zip_codes:
            cases_in_list = cases_in_list + count
            cases_by_zip[zip_code] += count
        elif re.fullmatch(r"\d{5}", zip_code):
            outside_zip_counts[zip_code] += count
        else:
            outside_zip_counts["(not five digits)"] += count
    outside_total = sum(outside_zip_counts.values())
    lines.append("ZIP CODES OF THE CASES THAT HAVE AN ADDRESS")
    lines.append(f"  Cases with an address: {cases_with_zip:,}")
    lines.append(f"  ZIP code is in the list of {len(nyc_zip_codes)}: {cases_in_list:,} ({share(cases_in_list, cases_with_zip)})")
    lines.append(f"  ZIP code is not in the list: {outside_total:,} ({share(outside_total, cases_with_zip)})")
    for zip_code, count in outside_zip_counts.most_common(TOP_ZIPS_SHOWN):
        lines.append(f"    {count:>10,}  {zip_code}")
    if len(outside_zip_counts) > TOP_ZIPS_SHOWN:
        lines.append(f"    ... and {len(outside_zip_counts) - TOP_ZIPS_SHOWN:,} more values not shown.")
    lines.append("")



    # 7.7 Report the property type of all New York City cases, then the
    # blank share for each year. The year table shows if blanks come from
    # certain years only.
    property_total = Counter()
    year_total = Counter()
    year_blank = Counter()
    for combination_number in nyc_cases.values():
        _, year, _, property_type = combinations[combination_number]
        property_total[property_type] += 1
        year_total[year] += 1
        if property_type == "(blank)":
            year_blank[year] += 1
    lines.append("PROPERTY TYPE OF ALL NEW YORK CITY CASES")
    for property_type, count in property_total.most_common():
        lines.append(f"  {count:>10,}  {share(count, nyc_total):>6}  {property_type}")
    lines.append("")
    lines.append("BLANK PROPERTY TYPE BY FILING YEAR (New York City cases)")
    for year in sorted(year_total):
        lines.append(f"  {year}: {year_total[year]:>9,} cases, {year_blank[year]:>9,} blank ({share(year_blank[year], year_total[year])})")
    lines.append("")



    # 7.8 Report the case types of all New York City cases.
    case_type_total = Counter()
    for combination_number in nyc_cases.values():
        case_type_total[combinations[combination_number][2]] += 1
    lines.append("CASE TYPES OF ALL NEW YORK CITY CASES")
    for case_type, count in case_type_total.most_common():
        lines.append(f"  {count:>10,}  {share(count, nyc_total):>6}  {case_type}")
    lines.append("")



    # 7.9 Report the cases that the ZIP table would hold: New York City
    # courts, an address ZIP code in the list, and a filing year inside the
    # range. Split them by property type.
    wanted_years = {str(year) for year in range(FIRST_YEAR, LAST_YEAR + 1)}
    scope_total = 0
    scope_by_property = Counter()
    scope_cases_by_zip = Counter()
    for (zip_code, combination_number), count in pair_counts.items():
        _, year, _, property_type = combinations[combination_number]
        if zip_code in nyc_zip_codes and year in wanted_years:
            scope_total = scope_total + count
            scope_by_property[property_type] += count
            scope_cases_by_zip[zip_code] += count
    lines.append(f"CASES THE ZIP TABLE WOULD HOLD ({FIRST_YEAR} to {LAST_YEAR}, list ZIP codes only): {scope_total:,}")
    for property_type, count in scope_by_property.most_common():
        lines.append(f"  {count:>10,}  {share(count, scope_total):>6}  {property_type}")
    lines.append("")



    # 7.10 Report the ZIP codes with the most cases, and the ZIP codes of
    # the list that have no case at all in the range.
    lines.append(f"ZIP CODES WITH THE MOST CASES ({FIRST_YEAR} to {LAST_YEAR})")
    for zip_code, count in scope_cases_by_zip.most_common(TOP_ZIPS_SHOWN):
        lines.append(f"  {count:>10,}  {zip_code}")
    empty_zips = sorted(zip_code for zip_code in nyc_zip_codes if scope_cases_by_zip[zip_code] == 0)
    lines.append("")
    lines.append(f"ZIP CODES OF THE LIST WITH NO CASE IN {FIRST_YEAR} TO {LAST_YEAR}: {len(empty_zips)}")
    if empty_zips:
        lines.append("  " + ", ".join(empty_zips))
    lines.append("")



    # 7.11 Give back the lines.
    return lines



# 8. SAVE THE REPORT
#
# This function writes the report lines into a text file. It makes the
# folder first if it does not exist. The report is already on the screen, so
# a failure here does not lose it.
def save_report(lines):
    # 8.1 Make the folder and write the file.
    try:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as error:
        print(f"The report could not be saved: {error}")
        return False



    # 8.2 Tell the person where the file is.
    print(f"The report was saved to {REPORT_PATH}")
    return True



# 9. RUN THE WHOLE CHECK
#
# This function runs the steps in order: get the ZIP list, read oca_index,
# read oca_addresses, build the report, print it, and save it. If something
# cannot be read, it prints what went wrong and ends with a failure code.
def main():
    # 9.1 Run the steps. If the website cannot be reached, or sends an
    # error, or a column is missing, print the problem and stop.
    try:
        print("Getting the ZIP code list from PLUTO ...")
        nyc_zip_codes = get_nyc_zip_codes()
        print("Reading oca_index ...")
        index_result = read_index_table()
        print("Reading oca_addresses ...")
        address_result = read_address_table(index_result)
    except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError, csv.Error) as error:
        print(f"FAILED. {error}")
        sys.exit(1)



    # 9.2 Build the report, print it, and save it.
    report_lines = build_report(nyc_zip_codes, index_result, address_result)
    print()
    print("\n".join(report_lines))
    save_report(report_lines)



# 10. START THE FILE
#
# The line "if __name__ == '__main__'" is true only when you start this
# file directly, by typing "python ziptable_oca_join_check.py". It is not true when
# another file imports this file. That way, importing this file never
# starts a request by accident.
if __name__ == "__main__":
    main()