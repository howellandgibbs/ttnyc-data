# ABOUT THIS FILE
#
# What this file does:
# This file asks New York City Open Data to describe the table called
# Department of Investigation Marshal Evictions (dataset identifier 6z8x-wfk4).
# It reads the list of columns. For each column it records the position, the column
# name, the data type that the source says the column has, and a short explanation
# of what the column holds. It then saves this list as a text file. This text file
# is the table specification.
#
# Where the explanation comes from:
# 1. If the source gives its own description for the column, the file uses it and adds "(source)".
# 2. If not, the file uses the note written in step 2 of this file. The note ends with
#    "(master guide)" when the master guide says it, or "(inferred)" when it is only a
#    guess from the column name and has not been checked.
# 3. If there is no note either, the file writes "No description available."
#
# What this file does not do:
# It does not download any rows of evictions. Because no rows are downloaded,
# no apartment numbers, court index numbers, or other personal data can reach this file.
# It does not check blank counts or real values. It does not clean or change any data.
# The data types are the types the source declares. They are not guessed from values.
#
# How to run it:
# In PowerShell, type: python e:/ttnyc-raw/DOI_eviction_column_profile.py
# The text file is saved in the same folder as this file.
# The Socrata app token is written in the settings in step 2. The file sends it
# with every request and never prints it.
#
# How the numbered steps are ordered:
# 1. Imports.
# 2. Settings, including the notes that explain each column.
# 3. Function that asks the source for its description.
# 4. Function that turns the description into a list of column rows.
# 5. Function that writes the text file.
# 6. Function that runs steps 3, 4, and 5 in order.
# 7. The line that starts the run.



# 1. These lines bring in tools that Python already has.
# "json" reads the answer from the source.
# "textwrap" cuts long explanations into shorter lines.
# "datetime" gives the time of the run.
# "pathlib" builds the path of the text file.
# "urllib" sends the request over the internet and safely encodes the token.
import json
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path



# 2. These are the settings. They are plain values that the later steps read.
# DATASET_IDENTIFIER is the code that New York City Open Data gives this table.
# DESCRIPTION_URL is the web address that returns the description of the table.
# APP_TOKEN is the Socrata app token. It is sent with every request as the parameter named $$app_token.
# OUTPUT_FILE_PATH is where the text file is saved. It is in the same folder as this file.
# SECONDS_BEFORE_GIVING_UP is how long the file waits for the source before it stops with an error.
# EXPLANATION_WIDTH is the most letters allowed in one line of an explanation.
# COLUMN_NOTES holds one short note for each column, written by us.
# A note whose column name is not in the real table is never used. The file does not warn about it.
DATASET_IDENTIFIER = "6z8x-wfk4"
DESCRIPTION_URL = "https://data.cityofnewyork.us/api/views/" + DATASET_IDENTIFIER + ".json"
APP_TOKEN = "4opT7rNOQnFEUYmVvYgTnqzY1"
OUTPUT_FILE_PATH = Path(__file__).parent / "DOI_eviction_column_profile.txt"
SECONDS_BEFORE_GIVING_UP = 60
EXPLANATION_WIDTH = 70
COLUMN_NOTES = {
    "court_index_number": "Court index number of the case. It identifies people, so it is never delivered. (master guide)",
    "eviction_address": "Address of the eviction. It is free text with unit descriptions mixed in. (master guide)",
    "eviction_apt_num": "Apartment number of the eviction. It identifies people, so it is never delivered. (master guide)",
    "executed_date": "Date the marshal carried out the eviction. Used to get the year. (inferred)",
    "residential_commercial_ind": "Whether the eviction is residential or commercial. We keep residential only. (master guide)",
    "borough": "Borough of the eviction. (inferred)",
    "eviction_zip": "ZIP code of the eviction address. (master guide)",
    "ejectment": "Ejectment field. The master guide lists it but does not say what its values mean. (master guide)",
    "eviction_legal_possession": "Eviction or Legal Possession field. The master guide lists it but does not say what its values mean. (master guide)",
    "marshal_first_name": "First name of the marshal. A marshal is a person, so it is never delivered. (inferred)",
    "marshal_last_name": "Last name of the marshal. A marshal is a person, so it is never delivered. (inferred)",
    "latitude": "Latitude. Never delivered, because coordinates finer than the building are not allowed. (master guide)",
    "longitude": "Longitude. Never delivered, because coordinates finer than the building are not allowed. (master guide)",
    "community_board": "Community board of the address. (inferred)",
    "council_district": "City council district of the address. (inferred)",
    "bin": "Building Identification Number. The master guide says the table has it. (master guide)",
    "bbl": "Borough, Block, and Lot. The master guide says 8,246 of 121,642 residential rows have no value here. (master guide)",
    "nta": "Neighborhood Tabulation Area of the address. (inferred)",
}



# 3. This function asks the source to describe the table and returns the answer
# as a Python dictionary. It stops with an error if the source does not answer correctly.
def ask_source_for_description(description_url):
    # 3.1 Build the request. The master guide says to send the app token as the
    # web address parameter named $$app_token. Add the token to the end of the web address.
    # The token is never printed.
    request_address = description_url + "?$$app_token=" + urllib.parse.quote(APP_TOKEN)
    request = urllib.request.Request(request_address)



    # 3.2 Send the request and read the answer as text. If the source answers with an
    # error code, or if the internet is not reachable, stop and say so.
    try:
        with urllib.request.urlopen(request, timeout=SECONDS_BEFORE_GIVING_UP) as answer:
            answer_text = answer.read().decode("utf-8")
    except urllib.error.HTTPError as problem:
        raise RuntimeError("The source answered with error code " + str(problem.code) + " for " + description_url)
    except urllib.error.URLError as problem:
        raise RuntimeError("The source could not be reached: " + str(problem.reason))



    # 3.3 Turn the answer text into a Python dictionary. If the text is not valid
    # JSON (JavaScript Object Notation), stop and say so.
    try:
        description = json.loads(answer_text)
    except json.JSONDecodeError:
        raise RuntimeError("The source answer is not valid JSON (JavaScript Object Notation).")
    return description



# 4. This function reads the description and returns one small dictionary per column.
# Each dictionary holds the position, the column name, the data type, and the explanation.
def make_column_rows(description):
    # 4.1 Find the list of columns inside the description. Stop with an error if the
    # list is missing or empty, because a table specification with no columns is wrong.
    if "columns" not in description:
        raise RuntimeError("The description has no 'columns' list.")
    source_columns = description["columns"]
    if len(source_columns) == 0:
        raise RuntimeError("The 'columns' list is empty.")



    # 4.2 Go through the columns in the order the source lists them. Stop with an error
    # if the column name or the data type is missing.
    # For the explanation, use the source description if it has one. If not, use our
    # note for the column. If there is no note either, say that no description is available.
    column_rows = []
    position = 1
    for source_column in source_columns:
        if "fieldName" not in source_column:
            raise RuntimeError("Column number " + str(position) + " has no 'fieldName'.")
        if "dataTypeName" not in source_column:
            raise RuntimeError("Column number " + str(position) + " has no 'dataTypeName'.")
        column_name = source_column["fieldName"]
        source_description = source_column.get("description", "").strip()
        if source_description != "":
            explanation = source_description + " (source)"
        elif column_name in COLUMN_NOTES:
            explanation = COLUMN_NOTES[column_name]
        else:
            explanation = "No description available."
        column_row = {
            "position": position,
            "column_name": column_name,
            "data_type": source_column["dataTypeName"],
            "explanation": explanation,
        }
        column_rows.append(column_row)
        position = position + 1
    return column_rows



# 5. This function writes the table specification as a text file.
# It takes the table name, the list of column rows, and the path of the file.
def write_specification_file(table_name, column_rows, output_file_path):
    # 5.1 Find the widest value in each of the first three columns of the specification,
    # so that the text lines up in neat columns.
    width_of_position = len("Position")
    width_of_column_name = len("Column name")
    width_of_data_type = len("Data type")
    for column_row in column_rows:
        width_of_position = max(width_of_position, len(str(column_row["position"])))
        width_of_column_name = max(width_of_column_name, len(column_row["column_name"]))
        width_of_data_type = max(width_of_data_type, len(column_row["data_type"]))



    # 5.2 Build the top lines of the file. They say what the file is and how it was made.
    # The labels are padded to the same width so that the colons line up.
    lines = []
    lines.append("DOI Eviction TABLE SPECIFICATION")
    lines.append("")
    lines.append("Table".ljust(22) + ": " + table_name)
    lines.append("Dataset identifier".ljust(22) + ": " + DATASET_IDENTIFIER)
    lines.append("Source".ljust(22) + ": New York City Open Data, " + DESCRIPTION_URL)
    lines.append("Created".ljust(22) + ": " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("Number of columns".ljust(22) + ": " + str(len(column_rows)))
    lines.append("")
    lines.append("The data types are the types the source declares.")
    lines.append("")
    lines.append("They were not guessed from values.")
    lines.append("")
    lines.append("No rows were downloaded for this file.")
    lines.append("")
    lines.append("(master guide) means the master guide says it. (inferred) means it is a guess from the column name and is not checked.")
    lines.append("")



    # 5.3 Build the header line, a line of dashes, and one block of lines for each column.
    # A long explanation is cut into several lines. The extra lines are moved to the right
    # so that they stay under the explanation column.
    header_start = (
        "Position".ljust(width_of_position) + "  "
        + "Column name".ljust(width_of_column_name) + "  "
        + "Data type".ljust(width_of_data_type) + "  "
    )
    header_line = header_start + "What it does"
    lines.append(header_line)
    lines.append("-" * (len(header_start) + EXPLANATION_WIDTH))
    for column_row in column_rows:
        column_start = (
            str(column_row["position"]).ljust(width_of_position) + "  "
            + column_row["column_name"].ljust(width_of_column_name) + "  "
            + column_row["data_type"].ljust(width_of_data_type) + "  "
        )
        explanation_lines = textwrap.wrap(column_row["explanation"], width=EXPLANATION_WIDTH)
        lines.append(column_start + explanation_lines[0])
        for extra_line in explanation_lines[1:]:
            lines.append(" " * len(column_start) + extra_line)



    # 5.4 Save the lines to the file as UTF-8 text (Unicode Transformation Format, 8-bit),
    # with one line per row. Then return the path so the caller can show it.
    with open(output_file_path, "w", encoding="utf-8") as output_file:
        output_file.write("\n".join(lines) + "\n")
    return output_file_path



# 6. This function runs the work in order: ask the source, make the column rows,
# write the file, and print where the file is and how many columns it holds.
def main():
    # 6.1 Ask the source for the description of the table.
    description = ask_source_for_description(DESCRIPTION_URL)



    # 6.2 Read the table name. If the source gives no name, use the dataset identifier.
    table_name = description.get("name", DATASET_IDENTIFIER)



    # 6.3 Turn the description into one row per column.
    column_rows = make_column_rows(description)



    # 6.4 Write the text file and tell the user where it is.
    saved_path = write_specification_file(table_name, column_rows, OUTPUT_FILE_PATH)
    print("Columns found: " + str(len(column_rows)))
    print("File saved: " + str(saved_path))



# 7. Python runs main() only when this file is started directly.
# It does not run when another file imports this file.
if __name__ == "__main__":
    main()