# ABOUT THIS FILE
#
# This file is called ziptable_oca_column_profile.py. It reads two Housing Court
# tables from the Housing Data Coalition, called HDC, from start to end. The
# tables are oca_index and oca_addresses. The Housing Court data is also
# called the OCA data, because the Office of Court Administration collects
# it.
#
# For every column in each table, the file works out:
# - the position of the column and its name,
# - how many values are blank,
# - how many different values there are, counted up to a limit,
# - the shortest and the longest value,
# - what kind of value it looks like: a whole number, a decimal number, a
#   date, a date with a time, true or false, a list in curly or square
#   brackets, a long code made of letters and numbers, or plain text,
# - the most common values, when the column has only a few different values.
#
# A CSV file does not store data types. It stores only text. So the "kind"
# that this file reports is a guess based on the values that it saw. It is
# not an official type.
#
# The file prints the report on the screen and also saves it as a text file,
# so that you can copy it into DATA-DICTIONARY.md.
#
# The file does not save the tables. It reads each table as it arrives and
# keeps only the counts in memory.
#
# The file does not change the Tenant Triage project. It is a separate
# helper.
#
# The file prints a few example values for each column, except for the
# column that holds the case code. The tables have no names of people. Even
# so, do not publish the examples without checking them first.
#
# Python reads this file from top to bottom. The numbered steps below are
# in that same order. Steps 1 and 2 prepare the settings. Steps 3 to 7 each
# prepare one small piece of work. Step 8 puts the pieces together. Step 9
# starts step 8 when you run this file.
#
# This file only uses tools that come with Python. You do not need to
# install anything.
#
# How to run it on your computer:
#     python ziptable_oca_column_profile.py
#         This reads both tables completely. It can take a long time.
#     python ziptable_oca_column_profile.py 200000
#         This reads only the first 200,000 rows of each table. Use it for
#         a quick test.



# 1. BRING IN THE TOOLS THIS FILE NEEDS
#
# Python comes with many ready-made tools. A file has to ask for each tool
# before it can use it. These lines ask for seven tools.
#
# "sys" lets the file read the words that you type after its name.
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
# TABLE_NAMES are the two tables that this file describes.
#
# REPORT_PATH is the place on your computer where the report is saved. It is
# saved in the same folder as this file, so the file works on any computer.
# Do not keep this folder inside OneDrive.
#
# PROGRESS_EVERY is how many rows to read before printing a progress line.
#
# MAX_DISTINCT is how many different values we keep for one column. Some
# columns, such as the case code, have millions of different values, and we
# cannot keep them all. When a column goes past this limit, the report says
# "more than" and stops keeping new values.
#
# SHOW_ALL_VALUES_UP_TO is the largest number of different values for which
# the report lists every value. A column with more values than this shows
# only its most common ones.
#
# MOST_COMMON_SHOWN is how many of the most common values to show for those
# columns.
#
# EXAMPLES_KEPT is how many example values we keep for each column.
#
# VALUE_WIDTH is the longest piece of a value that we print.
#
# CODE_COLUMN is the name of the column that holds the case code. We never
# print examples from it.
BASE_URL = "https://oca-2-dev.s3.amazonaws.com/public/"
TABLE_NAMES = ["oca_index", "oca_addresses"]
REPORT_PATH = Path(__file__).resolve().parent / "ziptable_oca_column_profile.txt"
PROGRESS_EVERY = 500_000
MAX_DISTINCT = 1000
SHOW_ALL_VALUES_UP_TO = 25
MOST_COMMON_SHOWN = 10
EXAMPLES_KEPT = 3
VALUE_WIDTH = 40
CODE_COLUMN = "indexnumberid"



# 3. DECIDE WHAT KIND OF VALUE A PIECE OF TEXT LOOKS LIKE
#
# This function looks at one value that is not blank, and gives back a
# short name for what it looks like. The checks run from the most exact to
# the least exact, and the first one that fits wins.
#
# The names are:
# - "whole number", for example 12 or -5
# - "decimal number", for example 5123.630
# - "date", for example 2016-04-12
# - "date and time", for example 2016-04-12 09:30:00
# - "true or false", for the words true, false, t, or f in any letter size
# - "bracketed list", when the value starts with { or [
# - "code", for a long run of letters and numbers with no spaces
# - "text", for everything else
def classify_value(value):
    # 3.1 Numbers.
    if re.fullmatch(r"-?\d+", value):
        return "whole number"
    if re.fullmatch(r"-?\d+\.\d+", value):
        return "decimal number"



    # 3.2 Dates and dates with a time.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return "date"
    if re.match(r"\d{4}-\d{2}-\d{2}[ T]\d", value):
        return "date and time"



    # 3.3 True or false.
    if value.lower() in ("true", "false", "t", "f"):
        return "true or false"



    # 3.4 Lists in brackets.
    if value[0] in "{[":
        return "bracketed list"



    # 3.5 A long code of letters and numbers, with at least 16 characters
    # and no spaces.
    if re.fullmatch(r"[A-Za-z0-9]{16,}", value):
        return "code"



    # 3.6 Anything else is plain text.
    return "text"



# 4. START AND UPDATE THE NOTES FOR ONE COLUMN
#
# For every column, we keep one small set of notes. These two functions
# create the notes and add one value to them.
def new_column_notes():
    # 4.1 Empty notes. "values" counts the different values. "kinds" counts
    # how many values looked like each kind. The shortest length starts at
    # None, which means "nothing seen yet".
    return {
        "blank": 0,
        "values": Counter(),
        "too_many_values": False,
        "kinds": Counter(),
        "shortest": None,
        "longest": 0,
        "examples": [],
    }



def add_value_to_notes(notes, value):
    # 4.2 A blank value is only counted. It has no kind and no length.
    value = value.strip()
    if not value:
        notes["blank"] += 1
        return



    # 4.3 Keep the value in the count of different values, unless we already
    # went past the limit and the value is new.
    if value in notes["values"] or len(notes["values"]) < MAX_DISTINCT:
        notes["values"][value] += 1
    else:
        notes["too_many_values"] = True



    # 4.4 Count the kind of value, and update the shortest and longest.
    notes["kinds"][classify_value(value)] += 1
    length = len(value)
    if notes["shortest"] is None or length < notes["shortest"]:
        notes["shortest"] = length
    if length > notes["longest"]:
        notes["longest"] = length



    # 4.5 Keep the first few values as examples.
    if len(notes["examples"]) < EXAMPLES_KEPT:
        notes["examples"].append(value)



# 5. READ ONE WHOLE TABLE AND KEEP NOTES FOR EVERY COLUMN
#
# This function opens one table on the internet and reads it row by row. It
# takes the column names from the first row, so it works for any number of
# columns. It keeps one set of notes for each column.
#
# Some rows may have fewer or more values than the header. The file counts
# these rows, because they show a problem with the table. A missing value is
# treated as blank. An extra value is ignored.
#
# It gives back the column names, the notes, the number of rows read, and
# the number of rows with the wrong number of values.
def profile_table(name, max_rows):
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



        # 5.3 The first row holds the column names. If there is no first
        # row, the file is empty, so stop with a clear message.
        column_names = next(reader, None)
        if not column_names:
            raise ValueError(f"{name} is empty")
        notes_by_column = [new_column_notes() for _ in column_names]
        rows_read = 0
        wrong_length_rows = 0



        # 5.4 Go through the rows. Stop early if we reached the row limit.
        for row in reader:
            if max_rows is not None and rows_read >= max_rows:
                break
            rows_read = rows_read + 1
            if len(row) != len(column_names):
                wrong_length_rows = wrong_length_rows + 1



            # 5.5 Add each value to the notes of its column. A missing value
            # counts as blank.
            for position, notes in enumerate(notes_by_column):
                value = row[position] if position < len(row) else ""
                add_value_to_notes(notes, value)



            # 5.6 Print a progress line from time to time.
            if rows_read % PROGRESS_EVERY == 0:
                print(f"  {name}: {rows_read:,} rows read ...")



    # 5.7 Give back what we learned.
    return column_names, notes_by_column, rows_read, wrong_length_rows



# 6. TURN THE NOTES OF ONE COLUMN INTO LINES OF TEXT
#
# This function takes the notes of one column and builds the lines that
# describe it. It gives the lines back as a list. It does not print them.
#
# The guessed type is simple. If every value that is not blank looks like
# the same kind, that kind is the guess. If the values look like different
# kinds, the guess is "mixed", and the lines show how many values looked
# like each kind. If every value is blank, the guess is "all blank".
def describe_column(position, column_name, notes, rows_read):
    # 6.1 Work out the counts and the guessed type.
    filled = rows_read - notes["blank"]
    blank_share = 100 * notes["blank"] / rows_read if rows_read else 0
    kinds = notes["kinds"]
    if not kinds:
        guessed_type = "all blank"
    elif len(kinds) == 1:
        guessed_type = next(iter(kinds))
    elif set(kinds) == {"whole number", "decimal number"}:
        guessed_type = "decimal number (some values have no decimals)"
    else:
        guessed_type = "mixed"



    # 6.2 Say how many different values there are. If we went past the
    # limit, say "more than".
    distinct = len(notes["values"])
    if notes["too_many_values"]:
        distinct_text = f"more than {MAX_DISTINCT:,}"
    else:
        distinct_text = f"{distinct:,}"



    # 6.3 Build the lines for this column.
    lines = [f"{position + 1}. {column_name}"]
    lines.append(f"   Guessed type: {guessed_type}")
    lines.append(f"   Blank values: {notes['blank']:,} ({blank_share:.1f}%). Filled values: {filled:,}.")
    lines.append(f"   Different values: {distinct_text}")
    if notes["shortest"] is not None:
        lines.append(f"   Shortest value: {notes['shortest']} characters. Longest value: {notes['longest']} characters.")
    if len(kinds) > 1:
        mix = ", ".join(f"{kind}: {count:,}" for kind, count in kinds.most_common())
        lines.append(f"   Values looked like: {mix}")



    # 6.4 Show the values. A column with few different values shows all of
    # them. A column with more shows its most common ones. The case code
    # column shows nothing.
    if column_name != CODE_COLUMN and notes["values"]:
        if not notes["too_many_values"] and distinct <= SHOW_ALL_VALUES_UP_TO:
            lines.append("   All values, most common first:")
            shown = notes["values"].most_common()
        else:
            lines.append(f"   Most common values (among the first {MAX_DISTINCT:,} different values seen):")
            shown = notes["values"].most_common(MOST_COMMON_SHOWN)
        for value, count in shown:
            lines.append(f"     {count:>12,}  {value[:VALUE_WIDTH]}")



    # 6.5 Show the first examples. The case code column shows none.
    if column_name != CODE_COLUMN and notes["examples"]:
        examples = " | ".join(value[:VALUE_WIDTH] for value in notes["examples"])
        lines.append(f"   First values seen: {examples}")
    lines.append("")
    return lines



# 7. SAVE THE REPORT
#
# This function writes the report lines into a text file. It makes the
# folder first if it does not exist. It gives back True when the file was
# saved, and False when it could not be saved. The report is already on the
# screen, so a failure here does not lose it.
def save_report(lines):
    # 7.1 Make the folder and write the file.
    try:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as error:
        print(f"The report could not be saved: {error}")
        return False



    # 7.2 Tell the person where the file is.
    print(f"The report was saved to {REPORT_PATH}")
    return True



# 8. PROFILE BOTH TABLES
#
# This function reads the number you typed after the file's name, if any.
# Then it reads the two tables one after the other, builds the report, prints
# it, and saves it. If a table cannot be read, it prints what went wrong and
# ends with a failure code.
def main():
    # 8.1 Read the row limit. No number means no limit.
    max_rows = None
    if len(sys.argv) > 1:
        if not sys.argv[1].isdigit() or int(sys.argv[1]) < 1:
            print("The number after the file name must be a whole number above zero.")
            sys.exit(1)
        max_rows = int(sys.argv[1])



    # 8.2 Read each table and build its part of the report. If the website
    # cannot be reached, or sends an error, print the problem and stop.
    report_lines = ["COLUMN PROFILE OF THE HOUSING COURT TABLES", ""]
    if max_rows is not None:
        report_lines.append(f"Only the first {max_rows:,} rows of each table were read.")
        report_lines.append("")
    try:
        for name in TABLE_NAMES:
            print(f"Reading {name} ...")
            column_names, notes_by_column, rows_read, wrong_length_rows = profile_table(name, max_rows)



            # 8.3 Write the heading of this table, then one description for
            # each column.
            report_lines.append(f"== {name}.csv")
            report_lines.append(f"Rows read: {rows_read:,}. Columns: {len(column_names)}.")
            report_lines.append(f"Rows with the wrong number of values: {wrong_length_rows:,}.")
            report_lines.append("")
            for position, column_name in enumerate(column_names):
                report_lines.extend(describe_column(position, column_name, notes_by_column[position], rows_read))
    except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError, csv.Error) as error:
        print(f"FAILED. {error}")
        sys.exit(1)



    # 8.4 Print the report and save it.
    print()
    print("\n".join(report_lines))
    save_report(report_lines)



# 9. START THE FILE
#
# The line "if __name__ == '__main__'" is true only when you start this
# file directly, by typing "python ziptable_oca_column_profile.py". It is not true
# when another file imports this file. That way, importing this file never
# starts a request by accident.
if __name__ == "__main__":
    main()