# ABOUT THIS FILE
#
# What this file does:
# This file downloads every row of the table called Housing Preservation and Development
# Housing Maintenance Code Violations (dataset identifier wvxf-dwi5) for one ZIP code.
# The ZIP code is set in step 2. The file first asks the source how many rows that ZIP code has.
# Then it downloads the rows in pages, because the source returns only a limited number of
# rows for each request. It saves all pages in one comma-separated values (CSV) file.
# At the end it checks that the number of saved rows equals the number the source reported.
#
# What this file does not do:
# It does not remove any column. The saved file holds all 41 columns, including the
# apartment, latitude, and longitude columns. Treat the saved file as private raw data.
# It does not clean, change, or aggregate any value.
# It does not print any row.
#
# How to run it:
# In PowerShell, type: python e:/ttnyc-raw/HPD_violation_zip_download.py
# The CSV file is saved in the same folder as this file.
# A failed run leaves no finished file, and a finished file from an earlier run is not touched.
#
# How the numbered steps are ordered:
# 1. Imports.
# 2. Settings.
# 3. Function that sends one request and returns the answer text.
# 4. Function that builds a web address from a list of parameters.
# 5. Function that asks the source how many rows the ZIP code has.
# 6. Function that downloads all pages and saves them.
# 7. Function that runs steps 5 and 6 and checks the result.
# 8. The line that starts the run.



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
# ZIP_CODE is the ZIP code to download. It is text, not a number.
# APP_TOKEN is the Socrata app token. It is sent with every request as the parameter named $$app_token.
# ROWS_PER_PAGE is how many rows one request asks for.
# SECONDS_BEFORE_GIVING_UP is how long the file waits for the source before it stops with an error.
# OUTPUT_FILE_PATH is where the finished file is saved.
# UNFINISHED_FILE_PATH is the name used while the download is still running.
DATASET_IDENTIFIER = "wvxf-dwi5"
TABLE_ADDRESS = "https://data.cityofnewyork.us/resource/" + DATASET_IDENTIFIER
ZIP_CODE = "10456"
APP_TOKEN = "4opT7rNOQnFEUYmVvYgTnqzY1"
ROWS_PER_PAGE = 50000
SECONDS_BEFORE_GIVING_UP = 300
OUTPUT_FILE_PATH = Path(__file__).parent / ("HPD_violations_download_zip_" + ZIP_CODE + ".csv")
UNFINISHED_FILE_PATH = Path(__file__).parent / ("HPD_violations_download_zip_" + ZIP_CODE + ".csv.part")



# 3. This function sends one request to the source and returns the answer as text.
# It stops with an error if the source answers with an error code or cannot be reached.
def send_request(request_address):
    # 3.1 Build the request and send it. Wait at most SECONDS_BEFORE_GIVING_UP seconds.
    request = urllib.request.Request(request_address)
    try:
        with urllib.request.urlopen(request, timeout=SECONDS_BEFORE_GIVING_UP) as answer:
            answer_text = answer.read().decode("utf-8")
    except urllib.error.HTTPError as problem:
        raise RuntimeError("The source answered with error code " + str(problem.code) + ".")
    except urllib.error.URLError as problem:
        raise RuntimeError("The source could not be reached: " + str(problem.reason))
    return answer_text



# 4. This function builds a full web address from the table address, an ending such as ".csv",
# and a dictionary of parameters. The app token is added to every address.
# The token is never printed.
def build_address(ending, parameters):
    # 4.1 Copy the parameters and add the app token to the copy.
    all_parameters = dict(parameters)
    all_parameters["$$app_token"] = APP_TOKEN



    # 4.2 Turn the parameters into the text that goes after the question mark.
    # Spaces and quote marks are encoded so that the web address stays valid.
    parameter_text = urllib.parse.urlencode(all_parameters, quote_via=urllib.parse.quote)
    return TABLE_ADDRESS + ending + "?" + parameter_text



# 5. This function asks the source how many rows the ZIP code has.
# It returns the number as a whole number.
def ask_source_for_row_count():
    # 5.1 Ask for the count of rows where the zip column equals the ZIP code.
    parameters = {
        "$select": "count(*)",
        "$where": "zip='" + ZIP_CODE + "'",
    }
    request_address = build_address(".json", parameters)
    answer_text = send_request(request_address)



    # 5.2 Read the answer. It must be a list with one item that holds the key "count".
    # Stop with an error if the answer looks different.
    try:
        answer_list = json.loads(answer_text)
        row_count = int(answer_list[0]["count"])
    except (json.JSONDecodeError, IndexError, KeyError, ValueError, TypeError):
        raise RuntimeError("The row count answer from the source could not be read.")
    return row_count



# 6. This function downloads all pages for the ZIP code and writes them to the unfinished file.
# It returns the number of data rows written, not counting the header row.
def download_all_pages():
    # 6.1 Prepare the loop. The header holds the column names. It is read from the first page.
    # The page number starts at 0. The number of rows written starts at 0.
    header_row = None
    page_number = 0
    rows_written = 0



    # 6.2 Open the unfinished file for writing. Each pass of the loop downloads one page.
    with open(UNFINISHED_FILE_PATH, "w", encoding="utf-8", newline="") as output_file:
        csv_writer = csv.writer(output_file)
        while True:
            # 6.3 Ask the source for one page. The rows are sorted by violationid so that the
            # pages follow each other in a steady order. The offset says how many rows to skip.
            parameters = {
                "$where": "zip='" + ZIP_CODE + "'",
                "$order": "violationid",
                "$limit": str(ROWS_PER_PAGE),
                "$offset": str(page_number * ROWS_PER_PAGE),
            }
            request_address = build_address(".csv", parameters)
            page_text = send_request(request_address)



            # 6.4 Read the page as rows. The first row of every page is the header row.
            # An empty answer means there are no more pages.
            page_rows = list(csv.reader(io.StringIO(page_text)))
            if len(page_rows) == 0:
                break
            page_header = page_rows[0]
            data_rows = page_rows[1:]



            # 6.5 Keep the header from the first page and write it once.
            # Stop with an error if a later page has a different header.
            if header_row is None:
                header_row = page_header
                csv_writer.writerow(header_row)
            elif page_header != header_row:
                raise RuntimeError("Page " + str(page_number + 1) + " has a different header from page 1.")



            # 6.6 Write the data rows of this page and tell the user how many rows the page had.
            for data_row in data_rows:
                csv_writer.writerow(data_row)
            rows_written = rows_written + len(data_rows)
            print("Page " + str(page_number + 1) + ": " + str(len(data_rows)) + " rows")



            # 6.7 If the page had fewer rows than a full page, it was the last page. Stop the loop.
            # Otherwise move on to the next page.
            if len(data_rows) < ROWS_PER_PAGE:
                break
            page_number = page_number + 1
    return rows_written



# 7. This function runs the work in order: ask for the row count, download all pages,
# check that the saved rows equal the reported count, and then give the file its final name.
def main():
    # 7.1 Ask the source how many rows the ZIP code has.
    expected_row_count = ask_source_for_row_count()
    print("Rows reported by the source for ZIP " + ZIP_CODE + ": " + str(expected_row_count))
    if expected_row_count == 0:
        raise RuntimeError("The source reports 0 rows for ZIP " + ZIP_CODE + ". Check the ZIP code.")



    # 7.2 Download all pages. If anything goes wrong, delete the unfinished file and stop.
    try:
        rows_written = download_all_pages()
    except Exception:
        if UNFINISHED_FILE_PATH.exists():
            UNFINISHED_FILE_PATH.unlink()
        raise



    # 7.3 Check that the number of saved rows equals the number the source reported.
    # If they differ, delete the unfinished file and stop with an error.
    if rows_written != expected_row_count:
        UNFINISHED_FILE_PATH.unlink()
        raise RuntimeError(
            "Saved " + str(rows_written) + " rows, but the source reported " + str(expected_row_count) + " rows."
        )



    # 7.4 Give the file its final name and tell the user where it is.
    UNFINISHED_FILE_PATH.replace(OUTPUT_FILE_PATH)
    print("Rows saved: " + str(rows_written))
    print("File saved: " + str(OUTPUT_FILE_PATH))



# 8. Python runs main() only when this file is started directly.
# It does not run when another file imports this file.
if __name__ == "__main__":
    main()