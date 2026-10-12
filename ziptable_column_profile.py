# ABOUT THIS FILE
#
# This file is called ziptable_column_profile.py. It writes a plain text
# specification of the ZIP table. The ZIP table is the file
# zip_housing_court.csv. It holds Housing Court case counts for each ZIP code
# (ZIP code is short for Zone Improvement Plan code), each year, and each
# property group.
#
# The specification has the same layout as the Housing Preservation and
# Development violation table specification. It starts with a short summary
# of the table. Then it lists every column with its position, its name, its
# data type, and a sentence that says what the column holds.
#
# The sentences about each column are typed into step 3 of this file. They
# come from the project documents and from build_zip_table.py. They were not
# guessed from the values.
#
# Before it writes anything, this file reads the real table and checks it:
# - The column names are exactly the 14 names in step 3, in the same order.
# - Every ZIP code has exactly five digits.
# - Every year is inside the first and last year in step 2.
# - Every property group is residential or plus commercial.
# - Every other value is a whole number made of digits only.
# - The table has one row for every ZIP code, every year, and both property
#   groups, with no row twice.
# - The rows are sorted by ZIP code, then year, then property group.
# - In every row, the case type columns add up to total_cases.
# If one check fails, the file stops with a clear message and writes nothing.
#
# This file does not change the ZIP table. It does not download anything. It
# does not need anything installed, because it only uses tools that come with
# Python.
#
# The result is a text file called ziptable_column_profile.txt. It is saved in
# the same folder as the table. It is a plain text document. Do not run it as
# Python.
#
# How to run it on your computer:
#     python e:/ttnyc-raw/ziptable_column_profile.py
#
# Python reads this file from top to bottom. The numbered steps below are in
# that same order. Steps 1 to 4 prepare the tools and the settings. The pieces
# of work are steps 5 to 8. Step 9 puts the pieces together. Step 10 starts
# step 9 when you run this file.



# 1. BRING IN THE TOOLS THIS FILE NEEDS
#
# Python comes with many ready-made tools. A file has to ask for each tool
# before it can use it. These lines ask for six tools.
#
# "sys" lets the file stop with a failure code.
#
# "csv" lets the file read a CSV file correctly. CSV is short for
# comma-separated values. It is a plain text file that holds a table, with one
# row on each line and commas between the values.
#
# "re" lets the file check the shape of a piece of text, such as "exactly
# five digits".
#
# "datetime" lets the file write down the date and time of the run.
#
# "textwrap" lets the file cut a long sentence into shorter lines.
#
# "Path" lets the file work with the locations of files on the computer.
import sys
import csv
import re
import datetime
import textwrap
from pathlib import Path



# 2. THE SETTINGS
#
# TABLE_PATH is where the ZIP table is saved. SPECIFICATION_PATH is where
# this file saves the specification.
#
# BUILDER_FILE_NAME is the name of the file that builds the ZIP table.
#
# FIRST_YEAR and LAST_YEAR are the years that the table holds.
#
# PROPERTY_GROUP_ORDER lists the two property groups in the order they appear
# in the table. The group residential comes first.
#
# NOT_COUNT_COLUMN_NAMES are the columns that do not hold a number of cases.
# TOTAL_COLUMN_NAME is the column that holds the total number of cases.
#
# The last five settings are widths. They decide how many characters each part
# of a line may use in the specification.
TABLE_PATH = Path(r"E:\ttnyc-raw\ziptable.csv")
SPECIFICATION_PATH = Path(r"E:\ttnyc-raw\ziptable_column_profile.txt")
BUILDER_FILE_NAME = "build_zip_table.py"
FIRST_YEAR = 2016
LAST_YEAR = 2025
PROPERTY_GROUP_ORDER = ["residential", "plus commercial"]
NOT_COUNT_COLUMN_NAMES = ["zip", "year", "property_group"]
TOTAL_COLUMN_NAME = "total_cases"
LABEL_WIDTH = 22
POSITION_WIDTH = 10
NAME_WIDTH = 37
TYPE_WIDTH = 11
DESCRIPTION_WIDTH = 80



# 3. THE FACTS ABOUT EACH COLUMN
#
# This list holds one entry for each column of the ZIP table, in the order of
# the columns in the table. Each entry has three parts: the name of the
# column, its data type, and a sentence that says what the column holds.
#
# The data type text means the following. "text" is a piece of text. "number"
# is a whole number.
#
# The words in brackets at the end of a sentence say where the fact comes
# from. "source" means a Housing Data Coalition column, which is named in the
# brackets. "script" means build_zip_table.py decides it.
COLUMN_FACTS = [
    {
        "name": "zip",
        "data_type": "text",
        "description": (
            "ZIP code of the property. It is the first 5 characters of postalcode from the first "
            "address row of the case. Only the ZIP codes in the PLUTO list are in the table. "
            "Always 5 digits. (source, script)"
        ),
    },
    {
        "name": "year",
        "data_type": "number",
        "description": (
            "Year the case was filed. It is the first 4 characters of fileddate. (source, script)"
        ),
    },
    {
        "name": "property_group",
        "data_type": "text",
        "description": (
            "Either residential or plus commercial. The group residential counts cases with "
            "property type Residential. The group plus commercial counts cases with property type "
            "Residential plus cases with property type Commercial. Never add the two rows "
            "together, because plus commercial already contains the residential cases. "
            "(source: propertytype, script)"
        ),
    },
    {
        "name": "total_cases",
        "data_type": "number",
        "description": (
            "Number of cases for the ZIP code, year, and property group. It is counted on its "
            "own, without looking at the case type. (script)"
        ),
    },
    {
        "name": "non_payment",
        "data_type": "number",
        "description": "Cases with case type Non-Payment. (source: classification)",
    },
    {
        "name": "holdover",
        "data_type": "number",
        "description": "Cases with case type Holdover. (source: classification)",
    },
    {
        "name": "hp",
        "data_type": "number",
        "description": "Cases with case type HP. HP is the source's own label. (source: classification)",
    },
    {
        "name": "illegal_lockout",
        "data_type": "number",
        "description": "Cases with case type Illegal Lockout. (source: classification)",
    },
    {
        "name": "hp_with_harassment",
        "data_type": "number",
        "description": "Cases with case type HP with Harassment. (source: classification)",
    },
    {
        "name": "harassment",
        "data_type": "number",
        "description": "Cases with case type Harassment. (source: classification)",
    },
    {
        "name": "illegal_activity",
        "data_type": "number",
        "description": "Cases with case type Illegal Activity. (source: classification)",
    },
    {
        "name": "article_7a",
        "data_type": "number",
        "description": "Cases with case type Article 7A. (source: classification)",
    },
    {
        "name": "breach_of_warrant_of_habitability",
        "data_type": "number",
        "description": (
            "Cases with case type Breach of Warrant of Habitability. (source: classification)"
        ),
    },
    {
        "name": "unclassified",
        "data_type": "number",
        "description": (
            "Cases with any other case type, or with a blank case type. (script)"
        ),
    },
]



# 4. WORK OUT THE LISTS OF COLUMN NAMES
#
# The list in step 3 holds the names together with their facts. Later steps
# need the names alone. This block makes three lists of names:
# - EXPECTED_COLUMN_NAMES holds every column name, in order.
# - COUNT_COLUMN_NAMES holds the names of the columns that hold a number of
#   cases. This is every column except zip, year, and property_group.
# - CASE_TYPE_COLUMN_NAMES holds the names of the columns that count one case
#   type. This is every count column except total_cases.
EXPECTED_COLUMN_NAMES = []
COUNT_COLUMN_NAMES = []
CASE_TYPE_COLUMN_NAMES = []
for column_fact in COLUMN_FACTS:
    column_name = column_fact["name"]
    EXPECTED_COLUMN_NAMES.append(column_name)
    if column_name not in NOT_COUNT_COLUMN_NAMES:
        COUNT_COLUMN_NAMES.append(column_name)
        if column_name != TOTAL_COLUMN_NAME:
            CASE_TYPE_COLUMN_NAMES.append(column_name)



# 5. READ THE ZIP TABLE
#
# This function opens the ZIP table and gives back its rows. Each row is a
# dictionary. A dictionary is a list of pairs, where each pair is a column
# name and the value in that column.
#
# The function stops with a clear message if the file is missing, if the
# column names are not exactly the names in step 3, or if a row has too many
# or too few values.
def read_table():
    # 5.1 Make sure the file exists.
    if not TABLE_PATH.exists():
        raise FileNotFoundError(f"The ZIP table was not found: {TABLE_PATH}")



    # 5.2 Open the file. The first line holds the column names. Compare them
    # with the names in step 3.
    with open(TABLE_PATH, "r", encoding="utf-8", newline="") as table_file:
        reader = csv.DictReader(table_file)
        found_column_names = reader.fieldnames
        if found_column_names != EXPECTED_COLUMN_NAMES:
            raise ValueError(
                f"The ZIP table has different column names than expected. "
                f"Expected: {EXPECTED_COLUMN_NAMES}. Found: {found_column_names}."
            )



        # 5.3 Read every row. A row with too many values gets a pair with the
        # name None. A row with too few values gets a value of None. Stop
        # if either happens.
        rows = []
        for row in reader:
            if None in row or None in row.values():
                raise ValueError(f"Row {len(rows) + 2} of the ZIP table has too many or too few values.")
            rows.append(row)



    # 5.4 Make sure the table is not empty, then give back the rows.
    if len(rows) == 0:
        raise ValueError("The ZIP table has a header but no rows.")
    return rows



# 6. CHECK THE ROWS OF THE ZIP TABLE
#
# This function checks every row. If one check fails, it stops with a clear
# message. It gives back nothing. If it finishes, every check has passed.
def check_rows(rows):
    # 6.1 Check the shape of every value in every row.
    for row in rows:
        row_name = f"ZIP code {row['zip']}, year {row['year']}, group {row['property_group']}"
        if not re.fullmatch(r"[0-9]{5}", row["zip"]):
            raise ValueError(f"A ZIP code is not exactly five digits: {row['zip']!r}")
        if not re.fullmatch(r"[0-9]{4}", row["year"]):
            raise ValueError(f"A year is not exactly four digits in {row_name}.")
        year_number = int(row["year"])
        if year_number < FIRST_YEAR or year_number > LAST_YEAR:
            raise ValueError(f"A year is outside {FIRST_YEAR} to {LAST_YEAR} in {row_name}.")
        if row["property_group"] not in PROPERTY_GROUP_ORDER:
            raise ValueError(f"A property group is not one of {PROPERTY_GROUP_ORDER} in {row_name}.")
        for column_name in COUNT_COLUMN_NAMES:
            if not re.fullmatch(r"[0-9]+", row[column_name]):
                raise ValueError(f"The value in column {column_name} is not a whole number in {row_name}.")



    # 6.2 Check that the table has one row for every ZIP code, every year,
    # and both property groups, and that no row appears twice.
    zip_codes = set()
    years = set()
    groups = set()
    keys_in_file = []
    for row in rows:
        zip_codes.add(row["zip"])
        years.add(row["year"])
        groups.add(row["property_group"])
        group_position = PROPERTY_GROUP_ORDER.index(row["property_group"])
        keys_in_file.append((row["zip"], int(row["year"]), group_position))
    expected_years = set()
    for year_number in range(FIRST_YEAR, LAST_YEAR + 1):
        expected_years.add(str(year_number))
    if years != expected_years:
        raise ValueError(f"The years in the table are not every year from {FIRST_YEAR} to {LAST_YEAR}.")
    if groups != set(PROPERTY_GROUP_ORDER):
        raise ValueError(f"The property groups in the table are not exactly {PROPERTY_GROUP_ORDER}.")
    expected_row_count = len(zip_codes) * len(years) * len(groups)
    if len(rows) != expected_row_count:
        raise ValueError(f"The table has {len(rows)} rows, but {expected_row_count} were expected.")
    if len(set(keys_in_file)) != len(keys_in_file):
        raise ValueError("The table has the same ZIP code, year, and property group twice.")



    # 6.3 Check that the rows are sorted by ZIP code, then year, then
    # property group.
    if keys_in_file != sorted(keys_in_file):
        raise ValueError("The rows are not sorted by ZIP code, then year, then property group.")



    # 6.4 Check that the case type columns add up to the total in every row.
    for row in rows:
        total_from_columns = 0
        for column_name in CASE_TYPE_COLUMN_NAMES:
            total_from_columns = total_from_columns + int(row[column_name])
        if total_from_columns != int(row[TOTAL_COLUMN_NAME]):
            raise ValueError(
                f"The case type columns add up to {total_from_columns}, but {TOTAL_COLUMN_NAME} is "
                f"{row[TOTAL_COLUMN_NAME]} for ZIP code {row['zip']}, year {row['year']}, group {row['property_group']}."
            )



# 7. MAKE THE LINES OF THE SPECIFICATION
#
# This function builds the text of the specification, one line at a time. It
# gives back a list of lines. It does not write anything to disk.
def make_specification_lines(rows):
    # 7.1 Count the ZIP codes, years, and property groups in the table.
    zip_codes = set()
    years = set()
    groups = set()
    for row in rows:
        zip_codes.add(row["zip"])
        years.add(row["year"])
        groups.add(row["property_group"])
    row_summary = (
        f"{len(rows):,} ({len(zip_codes)} ZIP codes times {len(years)} years "
        f"times {len(groups)} property groups)"
    )
    created_text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")



    # 7.2 Write the summary lines at the top. Each summary item has a label
    # and one or more lines of text. The label is only written on the first
    # line of the item.
    summary_items = [
        ("Table", ["Housing Court cases by ZIP code (ZIP code is the Zone Improvement Plan code)"]),
        ("File", [TABLE_PATH.name]),
        ("Built by", [BUILDER_FILE_NAME]),
        (
            "Source",
            [
                "Housing Data Coalition (HDC) extract of Office of Court Administration (OCA) Housing Court records,",
                "tables oca_index and oca_addresses, https://oca-2-dev.s3.amazonaws.com/public/",
            ],
        ),
        (
            "ZIP code list",
            ["the ZIP codes on at least one New York City tax lot in PLUTO (Primary Land Use Tax Lot Output)"],
        ),
        ("Created", [created_text]),
        ("Number of columns", [str(len(COLUMN_FACTS))]),
        ("Number of rows", [row_summary]),
    ]
    lines = ["ZIP TABLE SPECIFICATION", ""]
    for label, text_lines in summary_items:
        lines.append(f"{label:<{LABEL_WIDTH}}: {text_lines[0]}")
        for extra_text in text_lines[1:]:
            lines.append(" " * (LABEL_WIDTH + 2) + extra_text)
    lines.append("")



    # 7.3 Write the notes that explain how to read the table.
    lines.append(f"The data types are the types {BUILDER_FILE_NAME} writes.")
    lines.append("This program checked every value in the table against them before it wrote this file.")
    lines.append("")
    lines.append("A CSV (comma-separated values) file stores only text. Read the zip column as text.")
    lines.append("")
    lines.append(f"(script) means {BUILDER_FILE_NAME} decides it.")
    lines.append("(source) means the value comes from a Housing Data Coalition column, named in the line.")
    lines.append("")



    # 7.4 Write the heading of the column list, then one entry for every
    # column. A long sentence is cut into lines. The lines after the first one
    # start under the first letter of the sentence.
    description_start = POSITION_WIDTH + NAME_WIDTH + TYPE_WIDTH
    lines.append(
        f"{'Position':<{POSITION_WIDTH}}{'Column name':<{NAME_WIDTH}}{'Data type':<{TYPE_WIDTH}}What it does"
    )
    lines.append("-" * (description_start + DESCRIPTION_WIDTH))
    position_number = 0
    for column_fact in COLUMN_FACTS:
        position_number = position_number + 1
        sentence_lines = textwrap.wrap(
            column_fact["description"],
            width=DESCRIPTION_WIDTH,
            break_on_hyphens=False,
            break_long_words=False,
        )
        lines.append(
            f"{position_number:<{POSITION_WIDTH}}{column_fact['name']:<{NAME_WIDTH}}"
            f"{column_fact['data_type']:<{TYPE_WIDTH}}{sentence_lines[0]}"
        )
        for extra_sentence_line in sentence_lines[1:]:
            lines.append(" " * description_start + extra_sentence_line)
    lines.append("")



    # 7.5 Write the rules. The first list holds the rules that this program
    # checked in the real table. The second list holds the rules that come
    # from the project decisions and from the table builder. This program
    # cannot check them from the table alone.
    checked_rules = [
        "In every row, the case type columns, including unclassified, add up to total_cases.",
        "Every ZIP code has a row for every year and for both property groups. A count is 0 when there were no cases.",
        "Rows are sorted by ZIP code, then year, then property group, with residential first.",
        "Every value except zip and property_group is a whole number made of digits only. So the table cannot hold a name, an address, or a case code in those columns.",
    ]
    decision_rules = [
        "Every value is a count of cases. The table has no rates.",
        "Only cases from the Bronx, Kings, New York, Queens, and Richmond County Civil Courts, the Harlem Community Justice Center, and the Redhook Community Justice Center are counted. The last two are assumed to be New York City by name. This is not confirmed.",
        f"Cases filed from {FIRST_YEAR} to {LAST_YEAR} are counted. Cases filed in {LAST_YEAR + 1} or later are not in the table, because those years were not finished when the table was built.",
        "Cases with a ZIP code that is not in the PLUTO list are not in the table.",
        "The table describes a neighborhood. It does not describe one building. A ZIP code count must never be called a building-level fact.",
    ]
    lines.append("Rules this program checked in the table")
    lines.append("")
    rule_number = 0
    for rule_text in checked_rules:
        rule_number = rule_number + 1
        lines.extend(textwrap.wrap(rule_text, width=110, initial_indent=f"{rule_number}. ", subsequent_indent="   "))
    lines.append("")
    lines.append("Rules from the project decisions and the table builder. This program cannot check them from the table alone.")
    lines.append("")
    rule_number = 0
    for rule_text in decision_rules:
        rule_number = rule_number + 1
        lines.extend(textwrap.wrap(rule_text, width=110, initial_indent=f"{rule_number}. ", subsequent_indent="   "))



    # 7.6 Give back the lines.
    return lines



# 8. SAVE THE SPECIFICATION
#
# This function writes the lines to the specification file. It makes the
# folder first if the folder does not exist yet. A file with the same name is
# replaced.
def write_specification(lines):
    # 8.1 Make the folder, then write one line after another.
    SPECIFICATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SPECIFICATION_PATH, "w", encoding="utf-8") as specification_file:
        for line in lines:
            specification_file.write(line + "\n")



# 9. WRITE THE SPECIFICATION
#
# This function runs the steps in order: read the table, check the rows, make
# the lines, and save them. If something is wrong, it prints what went wrong
# and ends with a failure code. In that case, nothing is written.
def main():
    # 9.1 Run the steps. Stop with a clear message if one of them fails.
    try:
        rows = read_table()
        check_rows(rows)
        lines = make_specification_lines(rows)
        write_specification(lines)
    except (OSError, ValueError) as error:
        print(f"FAILED. Nothing was written. {error}")
        sys.exit(1)



    # 9.2 Tell what was done.
    print(f"Read {len(rows):,} rows from {TABLE_PATH}.")
    print("All checks passed.")
    print(f"Specification saved to: {SPECIFICATION_PATH}")



# 10. START THE FILE
#
# The line "if __name__ == '__main__'" is true only when you start this file
# directly. It is not true when another file imports this file. That way,
# importing this file never writes anything by accident.
if __name__ == "__main__":
    main()