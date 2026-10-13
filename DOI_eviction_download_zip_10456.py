# ABOUT THIS FILE
#
# What this file does:
# This file asks New York City Open Data for every row of the table called
# Department of Investigation Marshal Evictions (dataset identifier 6z8x-wfk4)
# where the ZIP code is 10456 and the executed date is from 2016-01-01 through 2025-12-31.
# It first asks how many rows match. It then downloads those rows as a CSV
# (Comma-Separated Values) file. It checks that the number of rows in the file is the
# same as the number the source reported. It also checks that the file has 20 columns.
#
# What this file keeps:
# Every column and every row is kept exactly as the source sends it. Nothing is removed,
# cleaned, or changed. Residential and commercial rows are both kept. This is on purpose,
# so that the project lead can see everything and decide what to leave out.
#
# Privacy warning:
# The saved file holds apartment numbers, court index numbers, docket numbers, marshal
# names, and coordinates. It must stay on this computer only. Never commit it to the
# ttnyc-data repository. Never upload it to GitHub. Never send it to the website.
#
# What this file does not do:
# It does not geocode, clean, count, or join anything. It does not look at other ZIP codes.
# It matches the ZIP code as exact text. A ZIP code written in another form, such as with
# extra spaces or with a dash and four more digits, would not match. This was not checked.
#
# How to run it:
# In PowerShell, type: python e:/ttnyc-raw/DOI_eviction_download_zip_10456.py
# The CSV file is saved in the same folder as this file.
# The Socrata app token is written in the settings in step 2. The file sends it
# with every request and never prints it.
#
# How the numbered steps are ordered:
# 1. Imports.
# 2. Settings.
# 3. Function that builds the filter text.
# 4. Function that sends one request to the source and returns the answer as bytes.
# 5. Function that asks how many rows match.
# 6. Function that downloads the matching rows as CSV and saves them.
# 7. Function that reads the saved file and counts its rows and columns.
# 8. Function that runs steps 3 through 7 in order and checks the numbers.
# 9. The line that starts the run.



# 1. These lines bring in tools that Python already has.
# "csv" reads the saved file so that the rows can be counted correctly.
# "io" lets the csv tool read text that is already in memory.
# "json" reads the row count answer from the source.
# "pathlib" builds the path of the saved file.
# "urllib" sends the requests over the internet and safely builds the web address.
import csv
import io
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path



# 2. These are the settings. They are plain values that the later steps read.
# DATASET_IDENTIFIER is the code that New York City Open Data gives this table.
# BASE_ADDRESS is the web address of the table data, without the file ending.
# APP_TOKEN is the Socrata app token. It is sent with every request in the header named X-App-Token.
# ZIP_CODE is the ZIP code to keep. It is text, because the source stores it as text.
# FIRST_DATE and LAST_DATE are the first and last moments of the time limit, 2016 through 2025.
# ROW_LIMIT is the most rows the file asks for in one request. If more rows match, the file stops with an error.
# EXPECTED_COLUMN_COUNT is the number of columns the column profile showed on 2026-10-12.
# OUTPUT_FILE_PATH is where the CSV is saved. It is in the same folder as this file.
# SECONDS_BEFORE_GIVING_UP is how long the file waits for the source before it stops with an error.
DATASET_IDENTIFIER = "6z8x-wfk4"
BASE_ADDRESS = "https://data.cityofnewyork.us/resource/" + DATASET_IDENTIFIER
APP_TOKEN = "4opT7rNOQnFEUYmVvYgTnqzY1"
ZIP_CODE = "10456"
FIRST_DATE = "2016-01-01T00:00:00"
LAST_DATE = "2025-12-31T23:59:59"
ROW_LIMIT = 50000
EXPECTED_COLUMN_COUNT = 20
OUTPUT_FILE_PATH = Path(__file__).parent / "DOI_eviction_download_zip_10456.csv"
SECONDS_BEFORE_GIVING_UP = 120



# 3. This function builds the filter text. The filter keeps rows where the ZIP code
# is exactly ZIP_CODE and the executed date is between FIRST_DATE and LAST_DATE.
def build_filter_text():
    # 3.1 Put the settings into the filter sentence that the source understands.
    filter_text = (
        "eviction_zip = '" + ZIP_CODE + "'"
        + " AND executed_date >= '" + FIRST_DATE + "'"
        + " AND executed_date <= '" + LAST_DATE + "'"
    )
    return filter_text



# 4. This function sends one request to the source and returns the answer as bytes.
# It stops with an error if the source does not answer correctly.
def ask_source(request_address):
    # 4.1 Build the request and add the app token to the header. The token is never printed.
    request = urllib.request.Request(request_address)
    request.add_header("X-App-Token", APP_TOKEN)



    # 4.2 Send the request and read the answer. If the source answers with an error code,
    # or if the internet is not reachable, stop and say so.
    try:
        with urllib.request.urlopen(request, timeout=SECONDS_BEFORE_GIVING_UP) as answer:
            answer_bytes = answer.read()
    except urllib.error.HTTPError as problem:
        raise RuntimeError("The source answered with error code " + str(problem.code) + " for " + BASE_ADDRESS)
    except urllib.error.URLError as problem:
        raise RuntimeError("The source could not be reached: " + str(problem.reason))
    return answer_bytes



# 5. This function asks the source how many rows match the filter.
# It returns the number as a whole number.
def ask_how_many_rows_match(filter_text):
    # 5.1 Build the web address. The "count(*)" part asks for the number of matching rows.
    query = urllib.parse.urlencode({"$select": "count(*)", "$where": filter_text})
    request_address = BASE_ADDRESS + ".json?" + query



    # 5.2 Send the request and read the answer. The answer is a list with one item.
    # The item holds the count as text. Stop with an error if the answer does not look like that.
    answer_bytes = ask_source(request_address)
    try:
        answer_list = json.loads(answer_bytes.decode("utf-8"))
        row_count = int(answer_list[0]["count"])
    except (json.JSONDecodeError, IndexError, KeyError, ValueError, TypeError):
        raise RuntimeError("The row count answer did not look like the expected list with a count.")
    return row_count



# 6. This function downloads the matching rows as a CSV and saves them exactly as sent.
# It stops with an error if more rows match than ROW_LIMIT, because the file would be cut short.
def download_matching_rows(filter_text, expected_row_count, output_file_path):
    # 6.1 Stop if the file would not hold every matching row.
    if expected_row_count > ROW_LIMIT:
        raise RuntimeError(
            "The source reports " + str(expected_row_count) + " matching rows, which is more than ROW_LIMIT "
            + str(ROW_LIMIT) + ". Paging is not written yet."
        )



    # 6.2 Build the web address. "$order" sorts the rows by executed date so the file is easy to read.
    # "$limit" says how many rows to send at most.
    query = urllib.parse.urlencode({
        "$where": filter_text,
        "$order": "executed_date",
        "$limit": str(ROW_LIMIT),
    })
    request_address = BASE_ADDRESS + ".csv?" + query



    # 6.3 Download the CSV and save the bytes without changing them.
    answer_bytes = ask_source(request_address)
    with open(output_file_path, "wb") as output_file:
        output_file.write(answer_bytes)
    return output_file_path



# 7. This function reads the saved CSV and returns two numbers: how many data rows it has
# (not counting the header line) and how many columns the header line has.
def count_rows_and_columns(saved_file_path):
    # 7.1 Read the file as UTF-8 text. The "utf-8-sig" setting removes a hidden mark at the start if there is one.
    with open(saved_file_path, "r", encoding="utf-8-sig", newline="") as saved_file:
        file_text = saved_file.read()



    # 7.2 Read the text with the csv tool. The csv tool understands text inside quotation marks,
    # so a comma or a line break inside a quoted value does not split a row by mistake.
    # Stop with an error if the file is empty.
    all_rows = list(csv.reader(io.StringIO(file_text)))
    if len(all_rows) == 0:
        raise RuntimeError("The saved file is empty. It does not even have a header line.")
    column_count = len(all_rows[0])
    data_row_count = len(all_rows) - 1
    return data_row_count, column_count



# 8. This function runs the work in order: build the filter, ask how many rows match,
# download them, read the saved file back, check the numbers, and print the result.
def main():
    # 8.1 Build the filter text.
    filter_text = build_filter_text()



    # 8.2 Ask the source how many rows match.
    expected_row_count = ask_how_many_rows_match(filter_text)
    print("Rows the source says match: " + str(expected_row_count))



    # 8.3 Download the rows and save them.
    saved_path = download_matching_rows(filter_text, expected_row_count, OUTPUT_FILE_PATH)



    # 8.4 Read the saved file back and count its rows and columns.
    saved_row_count, saved_column_count = count_rows_and_columns(saved_path)
    print("Rows in the saved file: " + str(saved_row_count))
    print("Columns in the saved file: " + str(saved_column_count))



    # 8.5 Check that the saved file has the same number of rows as the source reported,
    # and the number of columns the column profile showed. Stop with an error if either differs.
    if saved_row_count != expected_row_count:
        raise RuntimeError(
            "The saved file has " + str(saved_row_count) + " rows, but the source reported "
            + str(expected_row_count) + " rows."
        )
    if saved_column_count != EXPECTED_COLUMN_COUNT:
        raise RuntimeError(
            "The saved file has " + str(saved_column_count) + " columns, but the column profile showed "
            + str(EXPECTED_COLUMN_COUNT) + " columns."
        )



    # 8.6 Tell the user where the file is. Remind the user that the file must stay on this computer.
    print("File saved: " + str(saved_path))
    print("This file holds personal data. Do not commit it or upload it.")



# 9. Python runs main() only when this file is started directly.
# It does not run when another file imports this file.
if __name__ == "__main__":
    main()