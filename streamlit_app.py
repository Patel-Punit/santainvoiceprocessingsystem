import streamlit as st #type:ignore
import requests
import copy
import pandas as pd
import numpy as np
from datetime import datetime
import zipfile
from io import BytesIO 
import io  # Import io module
from functions import file_to_response_json, response_json_to_dataframes, missing_value_check, data_type_check, relation_check, accuracy_check, log_data_in_response_df, log_data_in_response_df_for_no_response, log_data_in_response_df_for_no_dataframes, round_to_nearest_zero, fill_missing_values_line_items_df, log_data_in_output_dataframe, get_file_name, get_listed_files, create_zip

# Function to clear all session state variables
def clear_session_state():
    for key in st.session_state.keys():
        del st.session_state[key]

def main():
    st.title("Invoice Processing System")

    uploaded_files = st.file_uploader("Choose PDF files", accept_multiple_files=True, type="pdf")

    # Add a Start Process button
    start_process = st.button("Start Process")


    if start_process:
        final_df = pd.DataFrame()
        response_df = pd.DataFrame(columns=['file_name', 'response_json', 'check_passed', 'step', 'remark'])
        file_container = {}
        all_files = []
        processed_files = []
        failed_files = []
        passed_files = []

        # Create placeholders for dynamic status updates
        total_files_status = st.empty()
        processed_files_status = st.empty()
        passed_files_status = st.empty()
        failed_files_status = st.empty()

        total_files_status.write(f"Total Files: {len(uploaded_files)}")
        processed_files_status.write("Processed Files: 0")
        passed_files_status.write("Passed Files: 0")
        failed_files_status.write("Failed Files: 0")

        # Initialize progress bar
        progress_bar = st.progress(0)

        uploaded_files_copy = copy.deepcopy(uploaded_files)
        total_files = len(uploaded_files_copy)

        for file in uploaded_files_copy:
            file_data = file.read()
            file_name = file.name
            file_container[file_name] = file_data

        for index, file in enumerate(uploaded_files):
            file_name = get_file_name(file)

            response_json = file_to_response_json(file)

            if not response_json:
                response_df = log_data_in_response_df_for_no_response(response_df, file_name)
                processed_files.append(file_name)
                failed_files.append(file_name)
                continue

            invoice_df, line_items_df, total_summary_df = response_json_to_dataframes(response_json)

            if invoice_df.empty or line_items_df.empty or total_summary_df.empty:
                response_df = log_data_in_response_df_for_no_dataframes(response_df, file_name, response_json)
                processed_files.append(file_name)
                failed_files.append(file_name)
                continue

            check, step, remark = accuracy_check(invoice_df, line_items_df, total_summary_df)

            response_df = log_data_in_response_df(response_df, file_name, response_json, check, step, remark)

            if not check:
                failed_files.append(file_name)
            else:
                passed_files.append(file_name)
                line_items_df = fill_missing_values_line_items_df(line_items_df)
                final_df = log_data_in_output_dataframe(invoice_df, line_items_df, total_summary_df, final_df)

            processed_files.append(file_name)
            all_files.append(file_name)

            # Update the status dynamically
            processed_files_status.write(f"Processed Files: {len(processed_files)}")
            passed_files_status.write(f"Passed Files: {len(passed_files)}")
            failed_files_status.write(f"Failed Files: {len(failed_files)}")

            # Update progress bar
            progress_bar.progress((index + 1) / total_files)

        file_name_dict = {
            "all_files": all_files,
            "processed_files": processed_files,
            "failed_files": failed_files,
            "passed_files": passed_files
        }

        zip_for_download = create_zip(file_container, file_name_dict, final_df, response_df)

        # Provide download button
        st.download_button(
            label="Download ZIP File",
            data=zip_for_download,
            file_name="output_files.zip",
            mime="application/zip"
        )


if __name__ == "__main__":
    main()
