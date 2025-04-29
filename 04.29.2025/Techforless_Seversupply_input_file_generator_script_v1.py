import pandas as pd
from datetime import datetime
import chardet

def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        result = chardet.detect(file.read())
    return result['encoding']

def generate_report(csv_file_path, output_file_path):
    print('Starting to generate the input file')
    
    # Define the 'Strike ID' prefix and initialize counter
    strike_id_prefix = 'TESS'
    status_messages = []  # List to collect status messages
    
    # Detect the encoding of the CSV file
    encoding = detect_encoding(csv_file_path)
    
    # try:
        # Read the CSV file with detected encoding and tab delimiter
    df = pd.read_csv(csv_file_path, encoding=encoding, delimiter='\t')
    status_messages.append(f'Read CSV file successfully. DataFrame shape: {df.shape}')

    # Check the number of columns in the DataFrame
    expected_columns = ['Strike id', 'SKU', 'Model Number', 'Title', 'Product URL', 'Image URL', 'UPC', 'Manufacturer', 'MPN', 'Category', 'ASIN', 'Price', 'Shipping', 'weight', 'dimensions', 'Lip']
    if df.shape[1] != len(expected_columns) - 1:  # Subtract 1 for the 'Strike id' column
        status_messages.append(f'Column mismatch: Expected {len(expected_columns)} columns, but found {df.shape[1] + 1}.')
        print(status_messages[-1])  # Print to console
        return

    # Add 'Strike ID' column
    strike_ids = [f'{strike_id_prefix}{str(i + 1).zfill(6)}' for i in range(len(df))]
    df.insert(0, 'Strike id', strike_ids)  # Insert 'Strike id' as the first column

    # Ensure all columns have appropriate names
    df.columns = expected_columns

    # Write to a text file
    output_file_name = f"{output_file_path}.txt"
    
    try:
        with open(output_file_name, 'w') as file:
            
            # Write rows without header
            for row in df.itertuples(index=False, name=None):
                row_str = '\t'.join(map(lambda x: '' if pd.isna(x) else str(x), row))
                file.write(f'{row_str}\n')
            
            file.write('\n')
            
        print(f'Created the input file: {output_file_name}')
    except PermissionError as e:
        print(f'Permission error: {e}. Please ensure the file is not open or try running the script with different permissions.')
    except Exception as e:
        print(f'An unexpected error occurred: {e}. Exiting.')

# Usage
csv_file_path = 'sap_enterprise.csv'  # Replace with the path to your CSV file
output_file_path = 'input'  # Base name for the output text file
generate_report(csv_file_path, output_file_path)
