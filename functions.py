import streamlit as st #type:ignore
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import zipfile
from io import BytesIO 
import io  # Import io module

def file_to_response_json(file):
    # API Configuration
    api_url = "https://sfrpl.in/invoice/extract_file"
    
    try:
        # Open the PDF file in binary mode
        files = {'invoice_file': file}
        
        # Send the POST request
        print("Sending request to:", api_url)
        response = requests.post(api_url, files=files, timeout=3000)

        # Log the response details
        print("Status Code:", response.status_code)
        print("Response Headers:", response.headers)

        if response.status_code == 200:
            response_json = response.json()
            print("Response:", response_json)
            return response_json
        else:
            print(f"Error: Received status code {response.status_code}")
            print("Response Text:", response.text)
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None
    

def response_json_to_dataframes(response_json):

    try:
        # Extracting DataFrames
        invoice_details = response_json.get("Invoice_Details", {})
        invoice_df = pd.DataFrame([invoice_details])

        line_items = response_json.get("Line_Items", [])
        line_items_df = pd.DataFrame(line_items)

        total_summary = response_json.get("Total_Summary", {})
        total_summary_df = pd.DataFrame([total_summary])

        return invoice_df, line_items_df, total_summary_df
    except:
        return None, None, None


def missing_value_check(invoice_df, line_items_df, total_summary_df):

    invoice_fields = ['invoice_number','invoice_date','place_of_origin','gstin_supplier','supplier_name']

    if (
        pd.isna(invoice_df['invoice_number']).any() or
        pd.isna(invoice_df['invoice_date']).any() or
        pd.isna(invoice_df['place_of_origin']).any() or
        pd.isna(invoice_df['gstin_supplier']).any() or
        pd.isna(invoice_df['supplier_name']).any()
    ):
        return False, 'Missing Values', 'Fields missing in invoice details.'

    state_codes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 97,
                   "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24",
                   "25", "26", "27", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "97"]

    # Convert state codes to strings for consistency
    state_codes = {str(code).zfill(2) for code in state_codes}

    # Validate 'place_of_origin' (must always have a valid value)
    invalid_origin = ~invoice_df['place_of_origin'].astype(str).isin(state_codes)

    # Validate 'place_of_supply' only if there is a value present
    invalid_supply = invoice_df['place_of_supply'].notna() & ~invoice_df['place_of_supply'].astype(str).isin(state_codes)

    # Check for any invalid entries
    if invalid_origin.any():
        return False, 'Not in options.', 'place_of_origin'

    if invalid_supply.any():
        return False, 'Not in options.', 'place_of_supply'
    

    taxable_condition1 = (pd.isna(line_items_df['rate_per_item_after_discount']) | pd.isna(line_items_df['quantity'])).any()
    taxable_condition2 = (pd.isna(line_items_df['final_amount']) | pd.isna(line_items_df['tax_amount'])).any()
    taxable_condition3 = (pd.isna(line_items_df['final_amount']) | pd.isna(line_items_df['tax_rate'])).any()
    taxable_condition4 = (pd.isna(line_items_df['tax_amount']) | pd.isna(line_items_df['tax_rate'])).any()
    taxable_condition5 = (pd.isna(line_items_df['tax_amount']) | (pd.isna(line_items_df['sgst_rate']) & pd.isna(line_items_df['cgst_rate']) & pd.isna(line_items_df['igst_rate']))).any()
    taxable_condition6 = (pd.isna(line_items_df['tax_rate']) | (pd.isna(line_items_df['sgst_amount']) & pd.isna(line_items_df['cgst_amount']) & pd.isna(line_items_df['igst_amount']))).any()
    taxable_condition7 = ((pd.isna(line_items_df['sgst_rate']) & pd.isna(line_items_df['cgst_rate']) & pd.isna(['igst_rate'])) | (pd.isna(line_items_df['sgst_amount']) & pd.isna(line_items_df['cgst_amount']) & pd.isna(['igst_amount']))).any()
    taxable_condition8 = (pd.isna(line_items_df['final_amount']) | (pd.isna(line_items_df['sgst_rate']) & pd.isna(line_items_df['cgst_rate']) & pd.isna(['igst_rate']))).any()
    taxable_condition9 = (pd.isna(line_items_df['final_amount']) | (pd.isna(line_items_df['sgst_amount']) & pd.isna(line_items_df['cgst_amount']) & pd.isna(['igst_amount']))).any()


    if (taxable_condition1 and taxable_condition2 and taxable_condition3 and taxable_condition4 and taxable_condition5 and taxable_condition6
            and taxable_condition7 and taxable_condition8 and taxable_condition9):
        return False, 'Missing Values', 'Not Enough fields in line items. First'
    

    tax_condition1 = (pd.isna(line_items_df['final_amount']) | pd.isna(line_items_df['taxable_value'])).any()
    tax_condition2 = (pd.isna(line_items_df['final_amount']) | pd.isna(line_items_df['tax_rate'])).any()
    tax_condition3 = (pd.isna(line_items_df['taxable_value']) | pd.isna(line_items_df['tax_rate'])).any()
    tax_condition4 = (pd.isna(line_items_df['final_amount']) | (pd.isna(line_items_df['sgst_rate']) & pd.isna(line_items_df['cgst_rate']) & pd.isna(line_items_df['igst_rate']))).any()
    tax_condition5 = (pd.isna(line_items_df['taxable_value']) | (pd.isna(line_items_df['sgst_rate']) & pd.isna(line_items_df['cgst_rate']) & pd.isna(line_items_df['igst_rate']))).any()
    tax_condition6 = (pd.isna(line_items_df['final_amount']) | (pd.isna(line_items_df['rate_per_item_after_discount']) & pd.isna(line_items_df['quantity']))).any()

    if (tax_condition1 and tax_condition2 and tax_condition3 and tax_condition4 and tax_condition5 and tax_condition6):
        return False, 'Missing Values', 'Not Enough fields in line items. Second'

    
    final_condition1 = (pd.isna(line_items_df['taxable_value']) | pd.isna(line_items_df['tax_rate'])).any()
    final_condition2 = (pd.isna(line_items_df['taxable_value']) | pd.isna(line_items_df['tax_amount'])).any()
    final_condition3 = (pd.isna(line_items_df['taxable_value']) | (pd.isna(line_items_df['sgst_rate']) & pd.isna(line_items_df['cgst_rate']) & pd.isna(line_items_df['igst_rate']))).any()
    final_condition4 = (pd.isna(line_items_df['taxable_value']) | (pd.isna(line_items_df['sgst_amount']) & pd.isna(line_items_df['cgst_amount']) & pd.isna(line_items_df['igst_amount']))).any()
    final_condition5 = (pd.isna(line_items_df['tax_amount']) | pd.isna(line_items_df['tax_rate'])).any()
    final_condition6 = (pd.isna(line_items_df['tax_amount']) | (pd.isna(line_items_df['sgst_rate']) & pd.isna(line_items_df['cgst_rate']) & pd.isna(line_items_df['igst_rate']))).any()
    final_condition7 = (pd.isna(line_items_df['tax_rate']) | (pd.isna(line_items_df['sgst_amount']) & pd.isna(line_items_df['cgst_amount']) & pd.isna(line_items_df['igst_amount']))).any()
    final_condition8 = ((pd.isna(line_items_df['sgst_rate']) & pd.isna(line_items_df['cgst_rate']) & pd.isna(['igst_rate'])) | (pd.isna(line_items_df['sgst_amount']) & pd.isna(line_items_df['cgst_amount']) & pd.isna(['igst_amount']))).any()

    if (final_condition1 and final_condition2 and final_condition3 and final_condition4 and final_condition5 and final_condition6 and final_condition7
            and final_condition8):
        return False, 'Missing Values', 'Not Enough fields in line items. Third'


    invoice_condition1 = (pd.isna(invoice_df['taxable_value']) | pd.isna(invoice_df['invoice_value'])).any()
    invoice_condition2 = (pd.isna(invoice_df['tax_amount']) | pd.isna(invoice_df['invoice_value'])).any()
    invoice_condition3 = (pd.isna(invoice_df['tax_amount']) | pd.isna(invoice_df['taxable_value'])).any()

    if (invoice_condition1 or invoice_condition2 or invoice_condition3):
        return False, 'Missing Values', 'Not Enough fields in invoice details.'
    

    total_condition1 = (pd.isna(total_summary_df['total_taxable_value']) | pd.isna(total_summary_df['total_invoice_value'])).any()
    total_condition2 = (pd.isna(total_summary_df['total_tax_amount']) | pd.isna(total_summary_df['total_invoice_value'])).any()
    total_condition3 = (pd.isna(total_summary_df['total_tax_amount']) | pd.isna(total_summary_df['total_taxable_value'])).any()
    total_condition4 = ((pd.isna(total_summary_df['total_sgst_amount']) & pd.isna(total_summary_df['total_cgst_amount']) & pd.isna(total_summary_df['total_igst_amount'])) | pd.isna(total_summary_df['total_invoice_value'])).any()
    total_condition5 = ((pd.isna(total_summary_df['total_sgst_amount']) & pd.isna(total_summary_df['total_cgst_amount']) & pd.isna(total_summary_df['total_igst_amount'])) | pd.isna(total_summary_df['total_taxable_value'])).any()

    if (total_condition1 and total_condition2 and total_condition3 and total_condition4 and total_condition5):
        return False, 'Missing Values', 'Not Enough fields in summary details.'   

    return True, 'No Missing Values', 'Proceed with next check.'         


def data_type_check(invoice_df, line_items_df, total_summary_df):
    try:
        # Replace None with np.nan to standardize missing value handling
        invoice_df.replace({None: np.nan}, inplace=True)
        line_items_df.replace({None: np.nan}, inplace=True)
        total_summary_df.replace({None: np.nan}, inplace=True)
        
        # Validate and convert date columns in invoice_df
        if 'invoice_date' in invoice_df.columns:
            mask = ~invoice_df['invoice_date'].isna()
            invoice_df.loc[mask, 'invoice_date'] = pd.to_datetime(invoice_df.loc[mask, 'invoice_date'], format="%d-%b-%Y", errors='coerce')
            if invoice_df.loc[mask, 'invoice_date'].isna().any():
                invalid_rows = invoice_df[mask & invoice_df['invoice_date'].isna()]
                raise ValueError(f"Invalid date values found in 'invoice_date':\n{invalid_rows}")
        
        # Validate and convert numeric columns in invoice_df
        numeric_cols_invoice = ['taxable_value', 'invoice_value', 'tax_amount']
        for col in numeric_cols_invoice:
            if col in invoice_df.columns:
                mask = ~invoice_df[col].isna()
                invoice_df.loc[mask, col] = pd.to_numeric(invoice_df.loc[mask, col], errors='coerce')
                if invoice_df.loc[mask, col].isna().any():
                    invalid_rows = invoice_df[mask & invoice_df[col].isna()]
                    raise ValueError(f"Invalid numeric values found in '{col}' of invoice_df:\n{invalid_rows}")
        
        # Validate and convert numeric columns in line_items_df
        numeric_cols_items = ['quantity', 'rate_per_item_after_discount', 'taxable_value',
                              'sgst_amount', 'cgst_amount', 'igst_amount', 'tax_amount',
                              'tax_rate', 'final_amount', 'sgst_rate', 'cgst_rate', 'igst_rate']
        for col in numeric_cols_items:
            if col in line_items_df.columns:
                mask = ~line_items_df[col].isna()
                line_items_df.loc[mask, col] = pd.to_numeric(line_items_df.loc[mask, col], errors='coerce')
                if line_items_df.loc[mask, col].isna().any():
                    invalid_rows = line_items_df[mask & line_items_df[col].isna()]
                    raise ValueError(f"Invalid numeric values found in '{col}' of line_items_df:\n{invalid_rows}")
        
        # Validate and convert numeric columns in total_summary_df
        numeric_cols_summary = ['total_taxable_value', 'total_invoice_value', 'total_tax_amount', 
                                 'total_cgst_amount', 'total_sgst_amount', 'total_igst_amount']
        for col in numeric_cols_summary:
            if col in total_summary_df.columns:
                mask = ~total_summary_df[col].isna()
                total_summary_df.loc[mask, col] = pd.to_numeric(total_summary_df.loc[mask, col], errors='coerce')
                if total_summary_df.loc[mask, col].isna().any():
                    invalid_rows = total_summary_df[mask & total_summary_df[col].isna()]
                    raise ValueError(f"Invalid numeric values found in '{col}' of total_summary_df:\n{invalid_rows}")
        
        return True, "Data type validation", "All data types are valid and converted successfully."
    
    except Exception as e:
        return False, "Data type mismatch", f"Error during validation: {str(e)}"


def relation_check(invoice_df, line_items_df, total_summary_df):

    # Replace 0 values with NaN in the specified columns of invoice_df
    invoice_df['tax_amount'] = invoice_df['tax_amount'].replace(0, np.nan)

    # Replace 0 values with NaN in the specified columns of line_items_df
    columns_to_replace_line_items = [
        'tax_rate', 'tax_amount', 'igst_rate', 'sgst_rate', 'cgst_rate',
        'igst_amount', 'sgst_amount', 'cgst_amount'
    ]
    line_items_df[columns_to_replace_line_items] = line_items_df[columns_to_replace_line_items].replace(0, np.nan)

    # Replace 0 values with NaN in the specified columns of total_summary_df
    columns_to_replace_total_summary = [
        'total_tax_amount', 'total_igst_amount', 'total_sgst_amount', 'total_cgst_amount'
    ]
    total_summary_df[columns_to_replace_total_summary] = total_summary_df[columns_to_replace_total_summary].replace(0, np.nan)


    # Perform relation check
    for id, row in invoice_df.iterrows():
        # Check if all values are numeric (not NaN)
        if pd.notna(row['invoice_value']) and pd.notna(row['taxable_value']) and pd.notna(row['tax_amount']):
            # # Ensure all are numeric before comparison
            # if not (isinstance(row['invoice_value'], (int, float)) and 
            #         isinstance(row['taxable_value'], (int, float)) and 
            #         isinstance(row['tax_amount'], (int, float))):
            #     return False, "Relation check", "Non-numeric values present"
            
            # Perform close check
            if not np.isclose(row['invoice_value'], row['taxable_value'] + row['tax_amount'], atol=1, rtol=0):
                return False, "Relation check", "Failed relation check in invoice details."
            

    # total_summary_df checks        
    if not total_summary_df[['total_taxable_value', 'total_invoice_value', 'total_tax_amount']].isnull().any().any():
        for id, row in total_summary_df.iterrows():
            if not np.isclose(row['total_invoice_value'], row['total_taxable_value'] + row['total_tax_amount'], atol=1, rtol=0):
                return False, "Relation check", "Failed relation check in Summary. First"
            
    if not total_summary_df[['total_taxable_value', 'total_invoice_value', 'total_igst_amount']].isnull().any().any():
        for id, row in total_summary_df.iterrows():
            if not np.isclose(row['total_invoice_value'], row['total_taxable_value'] + row['total_igst_amount'], atol=1, rtol=0):
                return False, "Relation check", "Failed relation check in Summary. Second"
            
    if not total_summary_df[['total_taxable_value', 'total_invoice_value', 'total_sgst_amount', 'total_cgst_amount']].isnull().any().any():
        for id, row in total_summary_df.iterrows():
            if not np.isclose(row['total_invoice_value'], row['total_taxable_value'] + (row['total_sgst_amount']+row['total_cgst_amount']), atol=1, rtol=0):
                return False, "Relation check", "Failed relation check in Summary. Third"
            

    # Rate
    if not line_items_df[['rate_per_item_after_discount', 'quantity', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['rate_per_item_after_discount'], row['taxable_value'] / row['quantity'], atol=1, rtol=0):
                return False, 'Relation check', 'Rate.'
            

    # Quantity
    if not line_items_df[['rate_per_item_after_discount', 'quantity', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['quantity'], row['taxable_value'] / row['rate_per_item_after_discount'], atol=1, rtol=0):
                return False, 'Relation check', 'Quantity.'
            


    '''
    
    Taxable Value
    
    '''
    # Taxable Value - from rate & quantity
    if not line_items_df[['rate_per_item_after_discount', 'quantity', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], row['quantity'] * row['rate_per_item_after_discount'], atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from rate & quantity.'
            

    # Taxable Value - from final amount & tax amount
    if not line_items_df[['final_amount', 'tax_amount', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], row['final_amount'] - row['tax_amount'], atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from final amount & tax amount.'
            
    # Taxable Value - from final amount & igst_amount        
    if not line_items_df[['final_amount', 'igst_amount', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], row['final_amount'] - row['igst_amount'], atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from final amount & igst_amount.'
            
    # Taxable Value - from final amount, sgst_amount & cgst_amount         
    if not line_items_df[['final_amount', 'sgst_amount', 'cgst_amount', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], row['final_amount'] - row['sgst_amount'] - row['cgst_amount'], atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from final amount, sgst_amount & cgst_amount.'
            

    # Taxable Value - from final amount & tax rate
    if not line_items_df[['final_amount', 'tax_rate', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], row['final_amount'] * (100/(100+row['tax_rate'])), atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from final amount & tax rate.'
            
    # Taxable Value - from final amount & igst_rate
    if not line_items_df[['final_amount', 'igst_rate', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], row['final_amount'] * (100/(100+row['igst_rate'])), atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from final amount & igst_rate.'
            
    # Taxable Value - from final amount, sgst_rate & cgst_rate
    if not line_items_df[['final_amount', 'sgst_rate', 'cgst_rate', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], row['final_amount'] * (100/(100+(row['cgst_rate']+row['sgst_rate']))), atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from final amount, sgst_rate & cgst_rate.'
            
    
    # Taxable Value - from tax amount & tax rate
    if not line_items_df[['tax_amount', 'tax_rate', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], row['tax_amount'] * (100/row['tax_rate']), atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from tax amount & tax rate.'
            
    # Taxable Value - from igst_amount & tax rate
    if not line_items_df[['igst_amount', 'tax_rate', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], row['igst_amount'] * (100/row['tax_rate']), atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from igst_amount & tax rate.'
            
    # Taxable Value - from tax amount & igst_rate
    if not line_items_df[['tax_amount', 'igst_rate', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], row['tax_amount'] * (100/row['igst_rate']), atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from tax amount & igst_rate.'
            
    # Taxable Value - from igst_amount & igst_rate
    if not line_items_df[['igst_amount', 'igst_rate', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], row['igst_amount'] * (100/row['igst_rate']), atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from igst_amount & igst_rate.'
            
    # Taxable Value - from tax amount, sgst_rate & cgst_rate
    if not line_items_df[['tax_amount', 'sgst_rate','cgst_rate', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], row['tax_amount'] * (100/(row['sgst_rate']+row['cgst_rate'])), atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from tax amount, sgst_rate & cgst_rate.'
            
    # Taxable Value - from sgst_amount, cgst_amount & tax rate
    if not line_items_df[['sgst_amount','cgst_amount', 'tax_rate', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], (row['sgst_amount']+row['cgst_amount']) * (100/row['tax_rate']), atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from sgst_amount, cgst_amount & tax rate.'
            
    # Taxable Value - from sgst_amount, cgst_amount, sgst_rate & cgst_rate
    if not line_items_df[['sgst_amount','cgst_amount', 'sgst_rate','cgst_rate', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['taxable_value'], (row['sgst_amount']+row['cgst_amount']) * (100/(row['sgst_rate']+row['cgst_rate'])), atol=1, rtol=0):
                return False, 'Relation check', 'Taxable Value - from sgst_amount, cgst_amount, sgst_rate & cgst_rate.'
            


    '''
    
    Tax Amount
    
    '''
    # Tax amount - from final amount & taxable value
    if not line_items_df[['final_amount', 'tax_amount', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['tax_amount'], row['final_amount'] - row['taxable_value'], atol=1, rtol=0):
                return False, 'Relation check', 'Tax amount - from final amount & taxable value.'
            
    # igst_amount - from final amount & taxable value
    if not line_items_df[['final_amount', 'igst_amount', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['igst_amount'], row['final_amount'] - row['taxable_value'], atol=1, rtol=0):
                return False, 'Relation check', 'igst_amount - from final amount & taxable value.'
            
    # sgst_amount & cgst_amount - from final amount & taxable value
    if not line_items_df[['final_amount', 'sgst_amount','cgst_amount', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose((row['sgst_amount']+row['cgst_amount']), row['final_amount'] - row['taxable_value'], atol=1, rtol=0):
                return False, 'Relation check', 'sgst_amount & cgst_amount - from final amount & taxable value.'
            
    # Tax amount - from final amount & tax_rate
    if not line_items_df[['final_amount', 'tax_rate', 'tax_amount']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['tax_amount'], row['final_amount'] - ((row['final_amount']*100)/(100+row['tax_rate'])), atol=1, rtol=0):
                return False, 'Relation check', 'Tax amount - from final amount & tax_rate.'
            
    # Tax amount - from final amount & igst_rate
    if not line_items_df[['final_amount', 'igst_rate', 'tax_amount']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['tax_amount'], row['final_amount'] - ((row['final_amount']*100)/(100+row['igst_rate'])), atol=1, rtol=0):
                return False, 'Relation check', 'Tax amount - from final amount & igst_rate.'
                        
    # Tax amount - from final amount, sgst_rate & cgst_rate
    if not line_items_df[['final_amount', 'sgst_rate','cgst_rate', 'tax_amount']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['tax_amount'], row['final_amount'] - ((row['final_amount']*100)/(100+(row['sgst_rate']+row['cgst_rate']))), atol=1, rtol=0):
                return False, 'Relation check', 'Tax amount - from final amount, sgst_rate & sgst_rate.'
            
    # igst_amount - from final amount & tax_rate
    if not line_items_df[['final_amount', 'tax_rate', 'igst_amount']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['igst_amount'], row['final_amount'] - ((row['final_amount']*100)/(100+row['tax_rate'])), atol=1, rtol=0):
                return False, 'Relation check', 'igst_amount - from final amount & tax_rate.'
            
    # sgst_amount & cgst_amount - from final amount & tax_rate
    if not line_items_df[['final_amount', 'tax_rate', 'sgst_amount','cgst_amount']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose((row['sgst_amount']+row['cgst_amount']), row['final_amount'] - ((row['final_amount']*100)/(100+row['tax_rate'])), atol=1, rtol=0):
                return False, 'Relation check', 'sgst_amount & cgst_amount - from final amount & tax_rate.'
            
    # sgst_amount & cgst_amount - from final amount, sgst_rate & cgst_rate
    if not line_items_df[['final_amount', 'tax_rate', 'sgst_amount','cgst_amount']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose((row['sgst_amount']+row['cgst_amount']), row['final_amount'] - ((row['final_amount']*100)/(100+(row['sgst_rate']+row['cgst_rate']))), atol=1, rtol=0):
                return False, 'Relation check', 'sgst_amount & cgst_amount - from final amount, sgst_rate & cgst_rate.'
            
    # igst_amount - from final amount & igst_rate
    if not line_items_df[['final_amount', 'igst_rate','igst_amount']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['igst_amount'], row['final_amount'] - ((row['final_amount']*100)/(100+row['igst_rate'])), atol=1, rtol=0):
                return False, 'Relation check', 'igst_amount - from final amount & igst_rate.'
            


    '''
    
    Final Amount
    
    '''
    # Final amount - from taxable vlue and tax amount
    if not line_items_df[['final_amount', 'tax_amount', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['final_amount'], row['taxable_value'] + row['tax_amount'], atol=1, rtol=0):
                return False, 'Relation check', 'Final amount - from taxable vlue and tax amount.'
            
    # Final amount - from taxable vlue and igst_amount
    if not line_items_df[['final_amount', 'igst_amount', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['final_amount'], row['taxable_value'] + row['igst_amount'], atol=1, rtol=0):
                return False, 'Relation check', 'Final amount - from taxable vlue and igst_amount.'
            
    # Final amount - from taxable vlue, sgst_amount and cgst_amount
    if not line_items_df[['final_amount', 'sgst_amount','cgst_amount', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['final_amount'], row['taxable_value'] + (row['sgst_amount']+row['cgst_amount']), atol=1, rtol=0):
                return False, 'Relation check', 'Final amount - from taxable vlue, sgst_amount and cgst_amount.'
            
    # Final amount - from taxable vlue and tax_rate
    if not line_items_df[['final_amount', 'tax_rate', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['final_amount'], row['taxable_value'] + (row['taxable_value']*row['tax_rate']/100), atol=1, rtol=0):
                return False, 'Relation check', 'Final amount - from taxable vlue and tax_rate.'
            
    # Final amount - from taxable vlue and igst_rate
    if not line_items_df[['final_amount', 'igst_rate', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['final_amount'], row['taxable_value'] + (row['taxable_value']*row['igst_rate']/100), atol=1, rtol=0):
                return False, 'Relation check', 'Final amount - from taxable vlue and igst_rate.'
            
    # Final amount - from taxable vlue, sgst_rate and cgst_rate
    if not line_items_df[['final_amount', 'sgst_rate','cgst_rate', 'taxable_value']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['final_amount'], row['taxable_value'] + (row['taxable_value']*(row['sgst_rate']+row['cgst_rate'])/100), atol=1, rtol=0):
                return False, 'Relation check', 'Final amount - from taxable vlue, sgst_rate and cgst_rate.'
            
    # Final amount - from tax_rate and tax amount
    if not line_items_df[['final_amount', 'tax_amount', 'tax_rate']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['final_amount'], ((100*row['tax_amount'])/row['tax_rate']) + (((100*row['tax_amount'])/row['tax_rate'])*row['tax_rate']/100), atol=1, rtol=0):
                return False, 'Relation check', 'Final amount - from tax_rate and tax amount.'
            
    # Final amount - from tax_rate and igst_amount
    if not line_items_df[['final_amount', 'igst_amount', 'tax_rate']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['final_amount'], ((100*row['igst_amount'])/row['tax_rate']) + (((100*row['igst_amount'])/row['tax_rate'])*row['tax_rate']/100), atol=1, rtol=0):
                return False, 'Relation check', 'Final amount - from tax_rate and igst_amount.'
            
    # Final amount - from igst_rate and igst_amount
    if not line_items_df[['final_amount', 'igst_amount', 'igst_rate']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['final_amount'], ((100*row['igst_amount'])/row['igst_rate']) + (((100*row['igst_amount'])/row['igst_rate'])*row['igst_rate']/100), atol=1, rtol=0):
                return False, 'Relation check', 'Final amount - from igst_rate and igst_amount.'
            
    # Final amount - from igst_rate and tax_amount
    if not line_items_df[['final_amount', 'tax_amount', 'igst_rate']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['final_amount'], ((100*row['tax_amount'])/row['igst_rate']) + (((100*row['tax_amount'])/row['igst_rate'])*row['igst_rate']/100), atol=1, rtol=0):
                return False, 'Relation check', 'Final amount - from igst_rate and tax_amount.'
            
    # Final amount - from tax_rate, sgst_amount and cgst_amount
    if not line_items_df[['final_amount', 'sgst_amount','cgst_amount', 'tax_rate']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['final_amount'], ((100*(row['sgst_amount']+row['cgst_amount']))/row['tax_rate']) + (((100*(row['sgst_amount']+row['cgst_amount']))/row['tax_rate'])*row['tax_rate']/100), atol=1, rtol=0):
                return False, 'Relation check', 'Final amount - from tax_rate and sgst_amount and cgst_amount.'
            
    # Final amount - from sgst_rate, cgst_rate, sgst_amount and cgst_amount
    if not line_items_df[['final_amount', 'sgst_amount','cgst_amount', 'sgst_rate','cgst_rate']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['final_amount'], ((100*(row['sgst_amount']+row['cgst_amount']))/(row['sgst_rate']+row['cgst_rate'])) + (((100*(row['sgst_amount']+row['cgst_amount']))/(row['sgst_rate']+row['cgst_rate']))*(row['sgst_rate']+row['cgst_rate'])/100), atol=1, rtol=0):
                return False, 'Relation check', 'Final amount - from sgst_rate, cgst_rate and sgst_amount and cgst_amount.'
            
    # Final amount - from sgst_rate, cgst_rate and tax_amount
    if not line_items_df[['final_amount', 'tax_amount', 'sgst_rate','cgst_rate']].isnull().any().any():
        for id, row in line_items_df.iterrows():
            if not np.isclose(row['final_amount'], ((100*row['tax_amount'])/(row['sgst_rate']+row['cgst_rate'])) + (((100*row['tax_amount'])/(row['sgst_rate']+row['cgst_rate']))*(row['sgst_rate']+row['cgst_rate'])/100), atol=1, rtol=0):
                return False, 'Relation check', 'Final amount - from sgst_rate, cgst_rate and tax_amount.'
            

    
    '''
    
    Overall check
    
    '''

    # Invoice details vs line items 
    if not line_items_df[['final_amount']].isnull().any().any() and not invoice_df[['invoice_value']].isnull().any().any():
        item_invoice = line_items_df['final_amount'].sum()
        invoice_invoice = invoice_df['invoice_value'].sum()

        if not np.isclose(item_invoice, invoice_invoice, atol=1, rtol=0):
            return False, 'Relation check', 'Invoice value does not match between line items and invoice details.'  

    if not line_items_df[['taxable_value']].isnull().any().any() and not invoice_df[['taxable_value']].isnull().any().any():
        item_taxable = line_items_df['taxable_value'].sum()
        invoice_taxable = invoice_df['taxable_value'].sum()

        if not np.isclose(item_taxable, invoice_taxable, atol=1, rtol=0):
            return False, 'Relation check', 'Taxable value does not match between line items and invoice details.'
        
    if not line_items_df[['tax_amount']].isnull().any().any() and not invoice_df[['tax_amount']].isnull().any().any():
        item_tax = line_items_df['tax_amount'].sum()
        invoice_tax = invoice_df['tax_amount'].sum()

        if not np.isclose(item_tax, invoice_tax, atol=1, rtol=0):
            return False, 'Relation check', 'tax_amount does not match between line items and invoice details.'
        

    # Summary vs line items
    if not line_items_df[['tax_amount']].isnull().any().any() and not total_summary_df[['total_tax_amount']].isnull().any().any():
        item_tax = line_items_df['tax_amount'].sum()
        summary_tax = total_summary_df['total_tax_amount'].sum()

        if not np.isclose(item_tax, summary_tax, atol=1, rtol=0):
            return False, 'Relation check', 'tax_amount does not match between line items and summary details.'
        
    if not line_items_df[['taxable_value']].isnull().any().any() and not total_summary_df[['total_taxable_value']].isnull().any().any():
        item_taxable = line_items_df['taxable_value'].sum()
        summary_taxable = total_summary_df['total_taxable_value'].sum()

        if not np.isclose(item_taxable, summary_taxable, atol=1, rtol=0):
            return False, 'Relation check', 'Taxable value does not match between line items and summary details.'
        
    if not line_items_df[['final_amount']].isnull().any().any() and not total_summary_df[['total_invoice_value']].isnull().any().any():
        item_invoice = line_items_df['final_amount'].sum()
        summary_invoce = total_summary_df['total_invoice_value'].sum()

        if not np.isclose(item_invoice, summary_invoce, atol=1, rtol=0):
            return False, 'Relation check', 'final_amount does not match between line items and summary details.'
        
    if not line_items_df[['cgst_amount']].isnull().any().any() and not total_summary_df[['total_cgst_amount']].isnull().any().any():
        item_c = line_items_df['cgst_amount'].sum()
        summary_c = total_summary_df['total_cgst_amount'].sum()

        if not np.isclose(item_c, summary_c, atol=1, rtol=0):
            return False, 'Relation check', 'cgst_amount does not match between line items and summary details.'
        
    if not line_items_df[['sgst_amount']].isnull().any().any() and not total_summary_df[['total_sgst_amount']].isnull().any().any():
        item_s = line_items_df['sgst_amount'].sum()
        summary_s = total_summary_df['total_sgst_amount'].sum()

        if not np.isclose(item_s, summary_s, atol=1, rtol=0):
            return False, 'Relation check', 'sgst_amount does not match between line items and summary details.'
        
    if not line_items_df[['igst_amount']].isnull().any().any() and not total_summary_df[['total_igst_amount']].isnull().any().any():
        item_i = line_items_df['igst_amount'].sum()
        summary_i = total_summary_df['total_igst_amount'].sum()

        if not np.isclose(item_i, summary_i, atol=1, rtol=0):
            return False, 'Relation check', 'igst_amount does not match between line items and summary details.'
        
    return True, 'Passed Relation check', 'proceed.'
            

def accuracy_check(invoice_df, line_items_df, total_summary_df):

    check, stage, remark = missing_value_check(invoice_df, line_items_df, total_summary_df)
    if check == False:
        return check, stage, remark
    
    check, stage, remark = data_type_check(invoice_df, line_items_df, total_summary_df)
    if check == False:
        return check, stage, remark
    
    check, stage, remark = relation_check(invoice_df, line_items_df, total_summary_df)
    if check == False:
        return check, stage, remark
    
    return True, 'All stages', 'Passed'


def log_data_in_response_df(response_df, file_name, response_json, check, step, remark):
    new_row = {'file_name':file_name, 'response_json':response_json, 'check_passed':check, 'step':step, 'remark':remark}
    response_df = pd.concat([response_df, pd.DataFrame([new_row])], ignore_index=True)

    return response_df


def log_data_in_response_df_for_no_response(response_df, file_name):
    new_row = {'file_name':file_name, 'response_json':None, 'check_passed':None, 'step':None, 'remark':None}
    response_df = pd.concat([response_df, pd.DataFrame([new_row])], ignore_index=True)

    return response_df


def log_data_in_response_df_for_no_dataframes(response_df, file_name, response_json):
    new_row = {'file_name':file_name, 'response_json':response_json, 'check_passed':None, 'step':None, 'remark':'Unknown JSON structure'}
    response_df = pd.concat([response_df, pd.DataFrame([new_row])], ignore_index=True)

    return response_df


def round_to_nearest_zero(value):
    # Check if the difference from the nearest integer is within 0.02
    if abs(value - round(value)) <= 0.02:
        return round(value)
    return value


def fill_missing_values_line_items_df(df):

  # Convert all rate columns to numeric, coercing errors
  df['final_amount'] = pd.to_numeric(df['final_amount'], errors='coerce').fillna(0)
  df['taxable_value'] = pd.to_numeric(df['taxable_value'], errors='coerce').fillna(0)
  df['tax_amount'] = pd.to_numeric(df['tax_amount'], errors='coerce').fillna(0)
  df['tax_rate'] = pd.to_numeric(df['tax_rate'], errors='coerce').fillna(0)
  df['cgst_rate'] = pd.to_numeric(df['cgst_rate'], errors='coerce').fillna(0)
  df['sgst_rate'] = pd.to_numeric(df['sgst_rate'], errors='coerce').fillna(0)
  df['igst_rate'] = pd.to_numeric(df['igst_rate'], errors='coerce').fillna(0)
  df['cgst_amount'] = pd.to_numeric(df['cgst_amount'], errors='coerce').fillna(0)
  df['sgst_amount'] = pd.to_numeric(df['sgst_amount'], errors='coerce').fillna(0)
  df['igst_amount'] = pd.to_numeric(df['igst_amount'], errors='coerce').fillna(0)
  df['rate_per_item_after_discount'] = pd.to_numeric(df['rate_per_item_after_discount'], errors='coerce').fillna(0)
  df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)

  for index, row in df.iterrows():

    final_amount = 0 if pd.isna(row['final_amount']) else row['final_amount']
    taxable_value = 0 if pd.isna(row['taxable_value']) else row['taxable_value']
    tax_amount = 0 if pd.isna(row['tax_amount']) else row['tax_amount']
    gst_rate = 0 if pd.isna(row['tax_rate']) else row['tax_rate']
    cgst_rate = 0 if pd.isna(row['cgst_rate']) else row['cgst_rate']
    sgst_rate = 0 if pd.isna(row['sgst_rate']) else row['sgst_rate']
    igst_rate = 0 if pd.isna(row['igst_rate']) else row['igst_rate']
    rate_per_item_after_discount = 0 if pd.isna(row['rate_per_item_after_discount']) else row['rate_per_item_after_discount']
    quantity = 0 if pd.isna(row['quantity']) else row['quantity']
      
    gst_rate_combined = cgst_rate + sgst_rate + igst_rate

    cgst_amount = 0 if pd.isna(row['cgst_amount']) else row['cgst_amount']
    sgst_amount = 0 if pd.isna(row['sgst_amount']) else row['sgst_amount']
    igst_amount = 0 if pd.isna(row['igst_amount']) else row['igst_amount']
    tax_amount_combined = cgst_amount + sgst_amount + igst_amount

    if taxable_value == 0 and rate_per_item_after_discount != 0 and quantity != 0:
        taxable_value = rate_per_item_after_discount * quantity
        df.at[index, 'taxable_value'] = taxable_value

    if tax_amount == 0 and (tax_amount_combined != 0):
        tax_amount = tax_amount_combined
        df.at[index, 'tax_amount'] = tax_amount

    # Fill gst_rate column & variable from gst_rate_combined if gst_rate is 0
    if gst_rate == 0 and (cgst_rate!=0 or sgst_rate!=0 or igst_rate!=0):
      gst_rate = gst_rate_combined
      df.at[index, 'tax_rate'] = gst_rate

    elif gst_rate == 0 and (cgst_rate==0 and sgst_rate==0 and igst_rate==0):
      gst_rate = 0
      df.at[index, 'tax_rate'] = gst_rate

    # Handle the case where gst_rate is like '0.18'
    if gst_rate >= -0.4 and gst_rate <= 0.4:
        gst_rate = gst_rate * 100
        df.at[index, 'tax_rate'] = gst_rate


    if final_amount != 0 and gst_rate != 0 and taxable_value == 0:
            taxable_value = final_amount * 100 / (100 + gst_rate)
            df.at[index, 'taxable_value'] = taxable_value
            # continue

    elif final_amount != 0 and gst_rate == 0 and taxable_value != 0:
        tax_amount = final_amount - taxable_value
        gst_rate = (tax_amount / taxable_value) * 100
        df.at[index, 'tax_rate'] = gst_rate
        # continue

    elif final_amount != 0 and gst_rate == 0 and taxable_value == 0 and tax_amount != 0:
        taxable_value = final_amount - tax_amount
        gst_rate = (tax_amount / taxable_value) * 100
        df.at[index, 'tax_rate'] = gst_rate
        df.at[index, 'taxable_value'] = taxable_value
        # continue

    elif final_amount != 0 and gst_rate == 0 and taxable_value == 0 and gst_rate_combined != 0:
        gst_rate = gst_rate_combined
        taxable_value = final_amount * 100 / (100 + gst_rate)
        df.at[index, 'tax_rate'] = gst_rate
        df.at[index, 'taxable_value'] = taxable_value
        # continue

    if final_amount == 0 and gst_rate != 0 and taxable_value != 0:
        final_amount = taxable_value + (taxable_value * gst_rate / 100)
        df.at[index, 'final_amount'] = final_amount
        # continue

    if final_amount == 0 and gst_rate != 0 and taxable_value == 0 and tax_amount != 0:
        taxable_value = tax_amount * 100 / gst_rate
        final_amount = taxable_value + tax_amount
        df.at[index, 'final_amount'] = final_amount
        df.at[index, 'taxable_value'] = taxable_value
        # continue

    elif final_amount == 0 and gst_rate == 0 and taxable_value != 0 and tax_amount != 0:
        gst_rate = (tax_amount / taxable_value) * 100
        final_amount = taxable_value + tax_amount
        df.at[index, 'tax_rate'] = gst_rate
        df.at[index, 'final_amount'] = final_amount
        # continue

    elif final_amount == 0 and gst_rate == 0 and taxable_value != 0 and tax_amount == 0 and gst_rate_combined != 0:
        gst_rate = gst_rate_combined
        final_amount = taxable_value + (taxable_value * gst_rate / 100)
        df.at[index, 'tax_rate'] = gst_rate
        df.at[index, 'final_amount'] = final_amount
        continue

    elif final_amount == 0 and gst_rate == 0 and taxable_value == 0 and tax_amount != 0 and gst_rate_combined != 0:
        gst_rate = gst_rate_combined
        taxable_value = tax_amount * 100 / gst_rate
        final_amount = taxable_value + tax_amount
        df.at[index, 'tax_rate'] = gst_rate
        df.at[index, 'taxable_value'] = taxable_value
        df.at[index, 'final_amount'] = final_amount
        # continue

    if tax_amount == 0 and final_amount != 0 and taxable_value != 0:
        tax_amount = final_amount - taxable_value
        df.at[index, 'tax_amount'] = tax_amount

    gst_rate = round_to_nearest_zero(gst_rate)

    df.at[index, 'tax_rate'] = gst_rate

  return df


def log_data_in_output_dataframe(invoice_df, line_items_df, total_summary_df, final_df):
    
    invoice_number = invoice_df['invoice_number'].iloc[0]
    invoice_date = invoice_df['invoice_date'].iloc[0]
    place_of_supply = invoice_df['place_of_supply'].iloc[0]
    place_of_origin = invoice_df['place_of_origin'].iloc[0]
    supplier_name = invoice_df['supplier_name'].iloc[0]
    gstin_supplier = invoice_df['gstin_supplier'].iloc[0]
    receiver_name = invoice_df['receiver_name'].iloc[0]
    gstin_recipient = invoice_df['gstin_recipient'].iloc[0]
    
    invoice_value = line_items_df['final_amount'].sum()

    grouped = line_items_df.groupby("tax_rate").agg({"taxable_value": "sum"}).reset_index()

    for _, row in grouped.iterrows():
        new_row = pd.DataFrame([{
            "gstin_recipient": gstin_recipient,
            "receiver_name": receiver_name,
            "gstin_supplier": gstin_supplier,
            "supplier_name": supplier_name,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "invoice_value": invoice_value,
            "place_of_supply": place_of_supply,
            "place_of_origin": place_of_origin,
            "tax_rate": row["tax_rate"],
            "taxable_value": row["taxable_value"]
        }])
        final_df = pd.concat([final_df, new_row], ignore_index=True)

    return final_df


def get_file_name(file):
    file_name = file.name
    return file_name


def get_listed_files(file_name_list, files_container):
    
    filtered_files = []

    for file in files_container:
        if file.name in file_name_list:
            filtered_files.append(file)

    return filtered_files


def create_zip(file_container, file_name_dict, final_df, response_df):
# Create a BytesIO object to store the zip file in memory
    zip_buffer = BytesIO()

    # Open a ZipFile in write mode
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add files from file_name_dict to the zip file
        for folder, file_names in file_name_dict.items():  # Iterate through folders and file names
            # Ensure folder path in the zip file
            zip_file.writestr(f"{folder}/", "")

            # Process each file name in the folder
            for file_name in file_names:
                if file_name in file_container:
                    file_data = file_container[file_name]
                    zip_file.writestr(f"{folder}/{file_name}", file_data)
                else:
                    print(f"Warning: {file_name} not found in file_container.")

        # Add invoice_df as output.csv
        if final_df is not None:
            csv_data = final_df.to_csv(index=False)
            zip_file.writestr("output.csv", csv_data)

        # Add response_df as accuracy_data.csv
        if response_df is not None:
            csv_data = response_df.to_csv(index=False)
            zip_file.writestr("accuracy_data.csv", csv_data)

    # Seek to the start of the buffer
    zip_buffer.seek(0)

    return zip_buffer








# 
