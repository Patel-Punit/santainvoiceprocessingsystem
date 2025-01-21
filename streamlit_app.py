import streamlit as st # type: ignore
import requests #type: ignore
import copy
import pandas as pd
import numpy as np
from datetime import datetime
import zipfile
from io import BytesIO 
import io  # Import io module
import time
from functions import generate_key, get_month_year, file_to_response_json_santa_fe, file_to_response_json_affine, response_json_to_dataframes, missing_value_check, data_type_check, relation_check, accuracy_check, log_data_in_response_df, log_data_in_response_df_for_no_response, log_data_in_response_df_for_no_dataframes, round_to_nearest_zero, fill_missing_values_line_items_df, log_data_in_output_dataframe, get_file_name, get_listed_files, create_zip, log_data_in_response_df_for_invalid_file

# Function to clear all session state variables
def clear_session_state():
    for key in st.session_state.keys():
        del st.session_state[key]

def main():
    st.title("Invoice Processing System")

    if 'zip_for_download' not in st.session_state:
        st.session_state.zip_for_download = None

    if 'process_completed' not in st.session_state:
        st.session_state.process_completed = False

    # SantaFe or Affine
    api = 'SantaFe'

    uploaded_files = st.file_uploader("Choose PDF files", accept_multiple_files=True, type="pdf")

    # Add a Start Process button
    start_process = st.button("Start Process")

    if start_process:
        if not st.session_state.process_completed:

            st.session_state.clear()

            final_df = pd.DataFrame()
            response_df = pd.DataFrame(columns=['file_name', 'status_code', 'response_json', 'check_passed', 'step', 'remark'])
            file_container = {}
            all_files = []
            processed_files = []
            failed_files = []
            passed_files = []
            invalid_files = []

            error_code_lists = {
                "NOT_AN_INVOICE": [],
                "BANK_STATEMENT": [],
                "CHALLAN_SAMPLE": [],
                "PAYMENT_RECEIPT_SAMPLE": [],
                "INVALID_PDF": [],
                "FILE_NOT_FOUND": [],
                "GSTR_DOCUMENT": [],
                "SALE_RECEIPT": [],
                "MULTIPLE_INVOICES": [],
                "INTERNATIONAL": [],
                "HANDWRITTEN": [],
                "EMPTY_CONTENT": [],
                "NO_TEXT_DETECTED": [],
                "INVALID_FILES": []
            }

            # Create placeholders for dynamic status updates
            total_files_status = st.empty()
            processed_files_status = st.empty()
            invalid_files_status = st.empty()
            passed_files_status = st.empty()
            failed_files_status = st.empty()

            total_files_status.write(f"Total Files: {len(uploaded_files)}")
            processed_files_status.write("Processed Files: 0")
            invalid_files_status.write("Invalid Files: 0")
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

                if api == 'SantaFe':
                    response_json, status_code = file_to_response_json_santa_fe(file)
                else:
                    status_code, response_json, status = file_to_response_json_affine(file)
                    if status_code == 408:
                        response_df = log_data_in_response_df_for_no_response(response_df, file_name, status_code)
                        processed_files.append(file_name)
                        failed_files.append(file_name)

                        # Update the status dynamically
                        processed_files_status.write(f"Processed Files: {len(processed_files)}")
                        invalid_files_status.write(f"Invalid Files: {len(invalid_files)}")
                        passed_files_status.write(f"Passed Files: {len(passed_files)}")
                        failed_files_status.write(f"Failed Files: {len(failed_files)}")

                        # Update progress bar
                        progress_bar.progress((index + 1) / total_files)

                        continue


                    if status_code == 200:
                        if status != 200:
                            processed_files.append(file_name)
                            invalid_files.append(file_name)
                            
                            # Get the error code from the response and append to the appropriate list
                            error_code = 'INVALID_FILES'
                            message = 'INVALID_FILES'
                            error_code_lists['INVALID_FILES'].append(file_name)

                            response_df = log_data_in_response_df_for_invalid_file(response_df, file_name, status_code, error_code, message)

                            # Update the status dynamically
                            processed_files_status.write(f"Processed Files: {len(processed_files)}")
                            invalid_files_status.write(f"Invalid Files: {len(invalid_files)}")
                            passed_files_status.write(f"Passed Files: {len(passed_files)}")
                            failed_files_status.write(f"Failed Files: {len(failed_files)}")

                            # Update progress bar
                            progress_bar.progress((index + 1) / total_files)

                            continue



                # st.write(status_code)
                # st.write(response_json)

                print('')
                print('')
                print('')
                print('')

                try:
                    if not response_json:
                        response_df = log_data_in_response_df_for_no_response(response_df, file_name, status_code)
                        processed_files.append(file_name)
                        failed_files.append(file_name)

                        # Update the status dynamically
                        processed_files_status.write(f"Processed Files: {len(processed_files)}")
                        invalid_files_status.write(f"Invalid Files: {len(invalid_files)}")
                        passed_files_status.write(f"Passed Files: {len(passed_files)}")
                        failed_files_status.write(f"Failed Files: {len(failed_files)}")

                        # Update progress bar
                        progress_bar.progress((index + 1) / total_files)

                        continue


                    # Check if the status code is 435 or 436
                    if str(status_code) in ('435', '436'):
                        processed_files.append(file_name)
                        invalid_files.append(file_name)
                        
                        # Get the error code from the response and append to the appropriate list
                        error_code = response_json.get("error_code")
                        message = response_json.get('message')
                        error_code_lists[error_code].append(file_name)

                        response_df = log_data_in_response_df_for_invalid_file(response_df, file_name, status_code, error_code, message)

                        # Update the status dynamically
                        processed_files_status.write(f"Processed Files: {len(processed_files)}")
                        invalid_files_status.write(f"Invalid Files: {len(invalid_files)}")
                        passed_files_status.write(f"Passed Files: {len(passed_files)}")
                        failed_files_status.write(f"Failed Files: {len(failed_files)}")

                        # Update progress bar
                        progress_bar.progress((index + 1) / total_files)

                        continue

                    invoice_df, line_items_df, total_summary_df = response_json_to_dataframes(response_json, api)

                    if invoice_df.empty or line_items_df.empty or total_summary_df.empty:
                        response_df = log_data_in_response_df_for_no_dataframes(response_df, file_name, response_json, status_code)
                        processed_files.append(file_name)
                        failed_files.append(file_name)

                        # Update the status dynamically
                        processed_files_status.write(f"Processed Files: {len(processed_files)}")
                        invalid_files_status.write(f"Invalid Files: {len(invalid_files)}")
                        passed_files_status.write(f"Passed Files: {len(passed_files)}")
                        failed_files_status.write(f"Failed Files: {len(failed_files)}")

                        # Update progress bar
                        progress_bar.progress((index + 1) / total_files)

                        continue

                    check, step, remark, line_items_df = accuracy_check(invoice_df, line_items_df, total_summary_df)

                    # st.write(check, step, remark)

                    response_df = log_data_in_response_df(response_df, file_name, response_json, check, step, remark, status_code)

                    # st.write(response_df)

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
                    invalid_files_status.write(f"Invalid Files: {len(invalid_files)}")
                    passed_files_status.write(f"Passed Files: {len(passed_files)}")
                    failed_files_status.write(f"Failed Files: {len(failed_files)}")

                    # Update progress bar
                    progress_bar.progress((index + 1) / total_files)

                    print(log_response)


                except:
                    processed_files.append(file_name)
                    all_files.append(file_name)
                    failed_files.append(file_name)

                    # Update the status dynamically
                    processed_files_status.write(f"Processed Files: {len(processed_files)}")
                    invalid_files_status.write(f"Invalid Files: {len(invalid_files)}")
                    passed_files_status.write(f"Passed Files: {len(passed_files)}")
                    failed_files_status.write(f"Failed Files: {len(failed_files)}")

                    # Update progress bar
                    progress_bar.progress((index + 1) / total_files)

                    print(log_response)


            file_name_dict = {
                "all_files": all_files,
                "processed_files": processed_files,
                "invalid_files": invalid_files,
                "failed_files": failed_files,
                "passed_files": passed_files
            }

            # Add only non-blank error code lists to the final dictionary
            non_blank_error_code_lists = {key: value for key, value in error_code_lists.items() if value}
            file_name_dict.update(non_blank_error_code_lists)

            st.session_state.zip_for_download = create_zip(file_container, file_name_dict, final_df, response_df, non_blank_error_code_lists)

            st.session_state.process_completed = True

    if st.session_state.zip_for_download:
        # Provide download button
        if st.download_button(
            label="Download ZIP File",
            data=st.session_state.zip_for_download,
            file_name="output_files.zip",
            mime="application/zip"
        ):
            pass

if __name__ == "__main__":
    main()
