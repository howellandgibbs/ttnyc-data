# ABOUT THIS FILE
#
# What this file does:
# This file downloads rows of the table called Housing Preservation and Development
# Housing Maintenance Code Violations (dataset identifier wvxf-dwi5) for one BBL
# (Borough, Block, and Lot) and for one period of years. The BBL and the years are set in step 2.
# A row belongs to the period when the year of its inspectiondate column is between
# the first year and the last year, both included.
# The BBL is split into its three parts: the borough code, the block number, and the lot number.
# The file filters the table on the three separate columns boroid, block, and lot.
# It first asks the source how many rows match. Then it downloads the rows in pages,
# because the source returns only a limited number of rows for each request.
# It saves all pages in one comma-separated values (CSV) file.
# At the end it checks that the number of saved rows equals the number the source reported.
#
# What this file does not do:
# It does not remove any column. The saved file holds all 41 columns, including the
# apartment, latitude, and longitude columns. Treat the saved file as private raw data.
# It does not clean, change, or aggregate any value.
# It does not print any row.
#
# How to run it:
# In PowerShell, type: python e:/ttnyc-raw/HPD_violation_download_bbl_2026100012.py
# The CSV file is saved in the same folder as this file.
# A failed run leaves no finished file, and a finished file from an earlier run is not touched.
#
# How the numbered steps are ordered:
# 1. Imports.
# 2. Settings.
# 3. Function that splits the BBL into borough code, block number, and lot number.
# 4. Function that builds the filter text.
# 5. Function that sends one request and returns the answer text.
# 6. Function that builds a web address from a list of parameters.
# 7. Function that asks the source how many rows match.
# 8. Function that downloads all pages and saves them.
# 9. Function that runs steps 7 and 8 and checks the result.
# 10. The line that starts the run.



# 1. These lines bring in tools that Python already has.
# "csv" reads and writes comma-separated values files.
# "io" lets the csv tool read text that is held in memory.
# "json" reads the row count answer from the source.
# "pathlib" builds the path of the saved file.
# "urllib" sends requests over the internet and safely encodes the web address.
import csv
import io
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path



# 2. These are the settings. They are plain values that the later steps read.
# DATASET_IDENTIFIER is the code that New York City Open Data gives this table.
# TABLE_ADDRESS is the web address of the table. The ending is added in later steps.
# BBL is the Borough, Block, and Lot to download. It is text with exactly 10 digits.
# FIRST_YEAR is the first year of the period. Rows are kept when the year of inspectiondate is this year or later.
# LAST_YEAR is the last year of the period. Rows are kept when the year of inspectiondate is this year or earlier.
# APP_TOKEN is the Socrata app token. It is sent with every request as the parameter named $$app_token.
# ROWS_PER_PAGE is how many rows one request asks for.
# SECONDS_BEFORE_GIVING_UP is how long the file waits for the source before it stops with an error.
# OUTPUT_FILE_PATH is where the finished file is saved.
# UNFINISHED_FILE_PATH is the name used while the download is still running.
DATASET_IDENTIFIER = "wvxf-dwi5"
TABLE_ADDRESS = "https://data.cityofnewyork.us/resource/" + DATASET_IDENTIFIER
BBL = "2026100012"
FIRST_YEAR = 2016
LAST_YEAR = 2025
APP_TOKEN = "4opT7rNOQnFEUYmVvYgTnqzY1"
ROWS_PER_PAGE = 50000
SECONDS_BEFORE_GIVING_UP = 300
OUTPUT_FILE_PATH = Path(__file__).parent / ("HPD_violations_download_bbl_" + BBL + ".csv")
UNFINISHED_FILE_PATH = Path(__file__).parent / ("HPD_violations_download_bbl_" + BBL + ".csv.part")



# 3. This function splits a BBL into three whole numbers: the borough code, the block number,
# and the lot number. The first digit is the borough code. The next five digits are the block.
# The last four digits are the lot. Zeros at the front are dropped because the source stores
# block and lot as plain numbers. The function stops with an error if the BBL is not 10 digits
# or if the borough code is not 1 through 5.
def split_bbl(bbl_text):
    # 3.1 Check that the BBL has exactly 10 characters and that all of them are digits.
    if len(bbl_text) != 10 or not bbl_text.isdigit():
        raise RuntimeError("The BBL must have exactly 10 digits, but it is: " + bbl_text)



    # 3.2 Cut the BBL into its three parts and turn each part into a whole number.
    borough_code = int(bbl_text[0])
    block_number = int(bbl_text[1:6])
    lot_number = int(bbl_text[6:10])



    # 3.3 Check that the borough code is 1 through 5.
    if borough_code < 1 or borough_code > 5:
        raise RuntimeError("The borough code must be 1 through 5, but it is: " + str(borough_code))
    return borough_code, block_number, lot_number



# 4. This function builds the filter text that tells the source which rows to return.
# The text says: borough code equals the borough, AND block equals the block, AND lot equals the lot,
# AND the inspectiondate is on or after January 1 of the first year,
# AND the inspectiondate is before January 1 of the year after the last year.
def make_filter_text():
    # 4.1 Check that the first year is not later than the last year.
    if FIRST_YEAR > LAST_YEAR:
        raise RuntimeError("FIRST_YEAR must not be later than LAST_YEAR.")



    # 4.2 Split the BBL and build the start and end of the period as dates.
    # The end date is the first day after the last year, and rows on that day are not included.
    borough_code, block_number, lot_number = split_bbl(BBL)
    period_start = str(FIRST_YEAR) + "-01-01T00:00:00"
    period_end = str(LAST_YEAR + 1) + "-01-01T00:00:00"
    return (
        "boroid=" + str(borough_code)
        + " AND block=" + str(block_number)
        + " AND lot=" + str(lot_number)
        + " AND inspectiondate >= '" + period_start + "'"
        + " AND inspectiondate < '" + period_end + "'"
    )



# 5. This function sends one request to the source and returns the answer as text.
# It stops with an error if the source answers with an error code or cannot be reached.
def send_request(request_address):
    # 5.1 Build the request and send it. Wait at most SECONDS_BEFORE_GIVING_UP seconds.
    request = urllib.request.Request(request_address)
    try:
        with urllib.request.urlopen(request, timeout=SECONDS_BEFORE_GIVING_UP) as answer:
            answer_text = answer.read().decode("utf-8")
    except urllib.error.HTTPError as problem:
        raise RuntimeError("The source answered with error code " + str(problem.code) + ".")
    except urllib.error.URLError as problem:
        raise RuntimeError("The source could not be reached: " + str(problem.reason))
    return answer_text



# 6. This function builds a full web address from the table address, an ending such as ".csv",
# and a dictionary of parameters. The app token is added to every address.
# The token is never printed.
def build_address(ending, parameters):
    # 6.1 Copy the parameters and add the app token to the copy.
    all_parameters = dict(parameters)
    all_parameters["$$app_token"] = APP_TOKEN



    # 6.2 Turn the parameters into the text that goes after the question mark.
    # Spaces are encoded so that the web address stays valid.
    parameter_text = urllib.parse.urlencode(all_parameters, quote_via=urllib.parse.quote)
    return TABLE_ADDRESS + ending + "?" + parameter_text



# 7. This function asks the source how many rows match the filter text.
# It returns the number as a whole number.
def ask_source_for_row_count():
    # 7.1 Ask for the count of rows that match the filter text.
    parameters = {
        "$select": "count(*)",
        "$where": make_filter_text(),
    }
    request_address = build_address(".json", parameters)
    answer_text = send_request(request_address)



    # 7.2 Read the answer. It must be a list with one item that holds the key "count".
    # Stop with an error if the answer looks different.
    try:
        answer_list = json.loads(answer_text)
        row_count = int(answer_list[0]["count"])
    except (json.JSONDecodeError, IndexError, KeyError, ValueError, TypeError):
        raise RuntimeError("The row count answer from the source could not be read.")
    return row_count



# 8. This function downloads all pages that match the filter text and writes them to the unfinished file.
# It returns the number of data rows written, not counting the header row.
def download_all_pages():
    # 8.1 Prepare the loop. The header holds the column names. It is read from the first page.
    # The page number starts at 0. The number of rows written starts at 0.
    header_row = None
    page_number = 0
    rows_written = 0



    # 8.2 Open the unfinished file for writing. Each pass of the loop downloads one page.
    with open(UNFINISHED_FILE_PATH, "w", encoding="utf-8", newline="") as output_file:
        csv_writer = csv.writer(output_file)
        while True:
            # 8.3 Ask the source for one page. The rows are sorted by violationid so that the
            # pages follow each other in a steady order. The offset says how many rows to skip.
            parameters = {
                "$where": make_filter_text(),
                "$order": "violationid",
                "$limit": str(ROWS_PER_PAGE),
                "$offset": str(page_number * ROWS_PER_PAGE),
            }
            request_address = build_address(".csv", parameters)
            page_text = send_request(request_address)



            # 8.4 Read the page as rows. The first row of every page is the header row.
            # An empty answer means there are no more pages.
            page_rows = list(csv.reader(io.StringIO(page_text)))
            if len(page_rows) == 0:
                break
            page_header = page_rows[0]
            data_rows = page_rows[1:]



            # 8.5 Keep the header from the first page and write it once.
            # Stop with an error if a later page has a different header.
            if header_row is None:
                header_row = page_header
                csv_writer.writerow(header_row)
            elif page_header != header_row:
                raise RuntimeError("Page " + str(page_number + 1) + " has a different header from page 1.")



            # 8.6 Write the data rows of this page and tell the user how many rows the page had.
            for data_row in data_rows:
                csv_writer.writerow(data_row)
            rows_written = rows_written + len(data_rows)
            print("Page " + str(page_number + 1) + ": " + str(len(data_rows)) + " rows")



            # 8.7 If the page had fewer rows than a full page, it was the last page. Stop the loop.
            # Otherwise move on to the next page.
            if len(data_rows) < ROWS_PER_PAGE:
                break
            page_number = page_number + 1
    return rows_written



# 9. This function runs the work in order: ask for the row count, download all pages,
# check that the saved rows equal the reported count, and then give the file its final name.
def main():
    # 9.1 Ask the source how many rows match. Stop with an error if there are none.
    expected_row_count = ask_source_for_row_count()
    print("Rows reported by the source for BBL " + BBL + ", " + str(FIRST_YEAR) + " to " + str(LAST_YEAR) + ": " + str(expected_row_count))
    if expected_row_count == 0:
        raise RuntimeError("The source reports 0 rows for BBL " + BBL + " in this period. Check the settings.")



    # 9.2 Download all pages. If anything goes wrong, delete the unfinished file and stop.
    try:
        rows_written = download_all_pages()
    except Exception:
        if UNFINISHED_FILE_PATH.exists():
            UNFINISHED_FILE_PATH.unlink()
        raise



    # 9.3 Check that the number of saved rows equals the number the source reported.
    # If they differ, delete the unfinished file and stop with an error.
    if rows_written != expected_row_count:
        UNFINISHED_FILE_PATH.unlink()
        raise RuntimeError(
            "Saved " + str(rows_written) + " rows, but the source reported " + str(expected_row_count) + " rows."
        )



    # 9.4 Give the file its final name and tell the user where it is.
    UNFINISHED_FILE_PATH.replace(OUTPUT_FILE_PATH)
    print("Rows saved: " + str(rows_written))
    print("File saved: " + str(OUTPUT_FILE_PATH))



# 10. Python runs main() only when this file is started directly.
# It does not run when another file imports this file.
if __name__ == "__main__":
    main()