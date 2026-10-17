# ABOUT THIS FILE
#
# What this file does:
# This file asks New York City Open Data for the whole table called
# Buildings Subject to HPD / Housing Preservation and Development Jurisdiction
# (dataset identifier kj4p-ruqc). It first asks how many rows the table has.
# It then downloads the whole table as a CSV (Comma-Separated Values) file and saves it.
# It checks that the number of rows in the saved file is the same as the number the source reported.
# It then reads the saved file one row at a time and profiles every column.
# For each column, the profile says how many values are blank, how many different values
# there are, the shortest and longest value length, and a guess of the type of the values.
# If a column has only a few different values, the profile also lists each value and how often it appears.
# The profile is printed on the screen and saved as a text file.
#
# What this file reads:
# It reads the column names from the first line of the downloaded file.
# It does not assume any column name.
#
# What this file does not do:
# It does not clean, join, count buildings, or build any BBL / Borough, Block, and Lot.
# It does not change any value. The type guess is only a guess from the values seen.
# It is not an official definition of the columns.
#
# Privacy note:
# The table is not expected to hold personal data, but this was not checked.
# The downloaded file and the profile stay on this computer only.
# Never commit them to the ttnyc-data repository.
#
# How to run it:
# In PowerShell, type: python e:/ttnyc-raw/HPD_buildings_column_profile.py
# The downloaded CSV file and the profile text file are saved in the same folder as this file.
# The Socrata app token is read from the environment variable named in step 2.
# If that variable is not set, the file still runs without a token, but the source may slow the download.
# The file never prints the token.
#
# How the numbered steps are ordered:
# 1. Imports.
# 2. Settings.
# 3. Function that reads the app token from the environment.
# 4. Function that sends one request to the source and returns the answer.
# 5. Function that asks how many rows the table has.
# 6. Function that downloads the whole table and saves it.
# 7. Function that guesses the type of one value.
# 8. Function that reads the saved file and profiles every column.
# 9. Function that turns the profile into lines of text.
# 10. Function that runs steps 5 through 9 in order and checks the numbers.
# 11. The line that starts the run.



# 1. These lines bring in tools that Python already has.
# "csv" reads the saved file so that the rows are split correctly.
# "json" reads the row count answer from the source.
# "os" reads the environment variable that holds the app token.
# "re" checks the shape of a value, for example whether it is only digits.
# "pathlib" builds the paths of the saved files.
# "urllib" sends the requests over the internet and safely builds the web address.
import csv
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path



# 2. These are the settings. They are plain values that the later steps read.
# DATASET_IDENTIFIER is the code that New York City Open Data gives this table.
# BASE_ADDRESS is the web address of the table data, without the file ending.
# APP_TOKEN_VARIABLE_NAME is the name of the environment variable that holds the Socrata app token.
# ROW_LIMIT is the most rows the file asks for. If the table has more rows, the file stops with an error.
# SECONDS_BEFORE_GIVING_UP is how long the file waits for the source before it stops with an error.
# BYTES_PER_READ is how many bytes the file reads from the source at one time while downloading.
# MOST_DIFFERENT_VALUES_TO_LIST is the largest number of different values a column can have
# for the profile to list every value. A column with more different values is not listed.
# DOWNLOAD_FILE_PATH is where the downloaded CSV is saved.
# REPORT_FILE_PATH is where the profile text is saved.
DATASET_IDENTIFIER = "kj4p-ruqc"
BASE_ADDRESS = "https://data.cityofnewyork.us/resource/" + DATASET_IDENTIFIER
APP_TOKEN_VARIABLE_NAME = "SOCRATA_APP_TOKEN"
ROW_LIMIT = 2000000
SECONDS_BEFORE_GIVING_UP = 600
BYTES_PER_READ = 1048576
MOST_DIFFERENT_VALUES_TO_LIST = 30
DOWNLOAD_FILE_PATH = Path(__file__).parent / "HPD_buildings_download.csv"
REPORT_FILE_PATH = Path(__file__).parent / "HPD_buildings_column_profile.txt"



# 3. This function reads the Socrata app token from the environment variable.
# It returns the token as text, or None if the variable is not set or is empty.
def read_app_token():
    # 3.1 Look up the variable. An empty value counts as not set.
    token = os.environ.get(APP_TOKEN_VARIABLE_NAME)
    if token is None or token.strip() == "":
        return None
    return token.strip()



# 4. This function sends one request to the source and returns the open answer,
# so that the caller can read it all at once or piece by piece.
# It stops with an error if the source does not answer correctly.
def ask_source(request_address):
    # 4.1 Build the request. Add the app token to the header only if there is one.
    # The token is never printed.
    request = urllib.request.Request(request_address)
    app_token = read_app_token()
    if app_token is not None:
        request.add_header("X-App-Token", app_token)



    # 4.2 Send the request. If the source answers with an error code,
    # or if the internet is not reachable, stop and say so.
    try:
        answer = urllib.request.urlopen(request, timeout=SECONDS_BEFORE_GIVING_UP)
    except urllib.error.HTTPError as problem:
        raise RuntimeError("The source answered with error code " + str(problem.code) + " for " + BASE_ADDRESS)
    except urllib.error.URLError as problem:
        raise RuntimeError("The source could not be reached: " + str(problem.reason))
    return answer



# 5. This function asks the source how many rows the whole table has.
# It returns the number as a whole number.
def ask_how_many_rows():
    # 5.1 Build the web address. The "count(*)" part asks for the number of rows.
    query = urllib.parse.urlencode({"$select": "count(*)"})
    request_address = BASE_ADDRESS + ".json?" + query



    # 5.2 Send the request and read the answer. The answer is a list with one item.
    # The item holds the count as text. Stop with an error if the answer does not look like that.
    with ask_source(request_address) as answer:
        answer_bytes = answer.read()
    try:
        answer_list = json.loads(answer_bytes.decode("utf-8"))
        row_count = int(answer_list[0]["count"])
    except (json.JSONDecodeError, IndexError, KeyError, ValueError, TypeError):
        raise RuntimeError("The row count answer did not look like the expected list with a count.")
    return row_count



# 6. This function downloads the whole table as a CSV and saves it exactly as sent.
# It stops with an error if the table has more rows than ROW_LIMIT, because the file would be cut short.
def download_table(expected_row_count, output_file_path):
    # 6.1 Stop if the file would not hold every row.
    if expected_row_count > ROW_LIMIT:
        raise RuntimeError(
            "The source reports " + str(expected_row_count) + " rows, which is more than ROW_LIMIT "
            + str(ROW_LIMIT) + ". Paging is not written yet."
        )



    # 6.2 Build the web address. "$limit" says how many rows to send at most.
    query = urllib.parse.urlencode({"$limit": str(ROW_LIMIT)})
    request_address = BASE_ADDRESS + ".csv?" + query



    # 6.3 Download the CSV piece by piece and save the bytes without changing them.
    with ask_source(request_address) as answer:
        with open(output_file_path, "wb") as output_file:
            while True:
                piece = answer.read(BYTES_PER_READ)
                if len(piece) == 0:
                    break
                output_file.write(piece)
    return output_file_path



# 7. This function guesses the type of one value. The value is never blank when this function is called.
# It returns one of four words: "whole number", "decimal number", "date", or "text".
def guess_value_type(value):
    # 7.1 A value made only of digits is a whole number.
    # A leading zero is still counted as a whole number here. The profile does not check for leading zeros.
    if re.fullmatch(r"[0-9]+", value):
        return "whole number"



    # 7.2 A value with digits, one dot, and more digits is a decimal number. A minus sign in front is allowed.
    if re.fullmatch(r"-?[0-9]+\.[0-9]+", value):
        return "decimal number"



    # 7.3 A value shaped like year-month-day is a date. A time after the day is allowed.
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}([T ][0-9:.]+)?", value):
        return "date"



    # 7.4 Anything else is text.
    return "text"



# 8. This function reads the saved CSV one row at a time and profiles every column.
# It returns the column names, the number of data rows, the number of rows with the wrong
# number of values, and one dictionary of facts for each column.
def profile_columns(saved_file_path):
    # 8.1 Open the file as UTF-8 text. The "utf-8-sig" setting removes a hidden mark at the start if there is one.
    # Read the first line as the column names. Stop with an error if the file is empty.
    with open(saved_file_path, "r", encoding="utf-8-sig", newline="") as saved_file:
        reader = csv.reader(saved_file)
        try:
            column_names = next(reader)
        except StopIteration:
            raise RuntimeError("The saved file is empty. It does not even have a header line.")



        # 8.2 Make one empty set of facts for each column.
        # blank_count counts values that are empty or only spaces.
        # value_counts counts how often each different value appears.
        # type_counts counts how often each type guess appears.
        # shortest_length and longest_length stay None until the first value that is not blank.
        column_facts = []
        for column_name in column_names:
            column_facts.append({
                "blank_count": 0,
                "value_counts": {},
                "type_counts": {},
                "shortest_length": None,
                "longest_length": None,
            })



        # 8.3 Read every data row. A row with the wrong number of values is counted and skipped.
        data_row_count = 0
        wrong_length_row_count = 0
        for row in reader:
            data_row_count = data_row_count + 1
            if len(row) != len(column_names):
                wrong_length_row_count = wrong_length_row_count + 1
                continue



            # 8.4 Add the values of this row to the facts of each column.
            for column_position in range(len(column_names)):
                value = row[column_position]
                facts = column_facts[column_position]
                if value.strip() == "":
                    facts["blank_count"] = facts["blank_count"] + 1
                    continue



                # 8.5 The value is not blank. Count it, measure its length, and count its type guess.
                value_length = len(value)
                if facts["shortest_length"] is None or value_length < facts["shortest_length"]:
                    facts["shortest_length"] = value_length
                if facts["longest_length"] is None or value_length > facts["longest_length"]:
                    facts["longest_length"] = value_length
                facts["value_counts"][value] = facts["value_counts"].get(value, 0) + 1
                type_guess = guess_value_type(value)
                facts["type_counts"][type_guess] = facts["type_counts"].get(type_guess, 0) + 1



    # 8.6 Give back the column names, the row counts, and the facts of each column.
    return column_names, data_row_count, wrong_length_row_count, column_facts



# 9. This function turns the profile into a list of lines of text.
# It does not print or save anything. It only builds the lines.
def build_report_lines(column_names, data_row_count, wrong_length_row_count, column_facts, source_row_count):
    # 9.1 Start with the facts about the whole file.
    report_lines = []
    report_lines.append("Profile of Buildings Subject to HPD / Housing Preservation and Development Jurisdiction (" + DATASET_IDENTIFIER + ")")
    report_lines.append("Rows the source reported: " + str(source_row_count))
    report_lines.append("Data rows in the saved file: " + str(data_row_count))
    report_lines.append("Rows with the wrong number of values: " + str(wrong_length_row_count))
    report_lines.append("Columns: " + str(len(column_names)))
    report_lines.append("")



    # 9.2 Write the facts of each column.
    for column_position in range(len(column_names)):
        facts = column_facts[column_position]
        different_value_count = len(facts["value_counts"])
        if data_row_count > 0:
            blank_share = 100.0 * facts["blank_count"] / data_row_count
        else:
            blank_share = 0.0



        # 9.3 Write the type guess. If more than one type was seen, show how often each one appeared.
        type_parts = []
        for type_name in sorted(facts["type_counts"]):
            type_parts.append(type_name + " " + str(facts["type_counts"][type_name]))
        if len(type_parts) == 0:
            type_text = "no values that are not blank"
        elif len(type_parts) == 1:
            type_text = sorted(facts["type_counts"])[0]
        else:
            type_text = "mixed: " + ", ".join(type_parts)



        # 9.4 Write the lines of this column.
        report_lines.append(str(column_position + 1) + ". " + column_names[column_position])
        report_lines.append("   Blank values: " + str(facts["blank_count"]) + " (" + format(blank_share, ".1f") + " percent)")
        report_lines.append("   Different values: " + str(different_value_count))
        report_lines.append("   Shortest value length: " + str(facts["shortest_length"]))
        report_lines.append("   Longest value length: " + str(facts["longest_length"]))
        report_lines.append("   Type guess: " + type_text)



        # 9.5 If the column has only a few different values, list each value and how often it appears.
        # The most common value comes first.
        if 0 < different_value_count <= MOST_DIFFERENT_VALUES_TO_LIST:
            report_lines.append("   Values and counts:")
            value_pairs = sorted(facts["value_counts"].items(), key=lambda pair: (-pair[1], pair[0]))
            for value, value_count in value_pairs:
                report_lines.append("      " + value + ": " + str(value_count))
        report_lines.append("")



    # 9.6 Give back the lines.
    return report_lines



# 10. This function runs the work in order: ask how many rows the table has, download it,
# profile the saved file, check the numbers, and print and save the profile.
def main():
    # 10.1 Ask the source how many rows the table has.
    source_row_count = ask_how_many_rows()
    print("Rows the source says the table has: " + str(source_row_count))



    # 10.2 Download the table and save it.
    saved_path = download_table(source_row_count, DOWNLOAD_FILE_PATH)



    # 10.3 Profile the saved file.
    column_names, data_row_count, wrong_length_row_count, column_facts = profile_columns(saved_path)



    # 10.4 Check that the saved file has the same number of rows as the source reported.
    # Stop with an error if it does not.
    if data_row_count != source_row_count:
        raise RuntimeError(
            "The saved file has " + str(data_row_count) + " rows, but the source reported "
            + str(source_row_count) + " rows."
        )



    # 10.5 Build the profile lines, print them, and save them as a text file.
    report_lines = build_report_lines(column_names, data_row_count, wrong_length_row_count, column_facts, source_row_count)
    for report_line in report_lines:
        print(report_line)
    with open(REPORT_FILE_PATH, "w", encoding="utf-8") as report_file:
        report_file.write("\n".join(report_lines) + "\n")



    # 10.6 Tell the user where the files are.
    print("Downloaded file saved: " + str(saved_path))
    print("Profile saved: " + str(REPORT_FILE_PATH))



# 11. Python runs main() only when this file is started directly.
# It does not run when another file imports this file.
if __name__ == "__main__":
    main()