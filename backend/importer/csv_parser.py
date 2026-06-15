"""
CSV parser using Pandas. Reads the raw CSV and returns structured row data.
"""
import pandas as pd
import io
import re


def parse_csv(file_content):
    """
    Parse CSV content into a list of row dicts with raw string values preserved.
    Returns (rows, parse_errors) where rows is list of dicts and parse_errors is list of issues.
    """
    parse_errors = []

    try:
        # Read with all columns as strings to preserve raw data
        df = pd.read_csv(
            io.StringIO(file_content),
            dtype=str,
            keep_default_na=False,
            skipinitialspace=True
        )
    except Exception as e:
        return [], [{'row': 0, 'error': f'Failed to parse CSV: {str(e)}'}]

    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    expected_cols = ['date', 'description', 'paid_by', 'amount', 'currency',
                     'split_type', 'split_with', 'split_details', 'notes']

    missing_cols = [c for c in expected_cols if c not in df.columns]
    if missing_cols:
        parse_errors.append({
            'row': 0,
            'error': f'Missing columns: {", ".join(missing_cols)}'
        })
        return [], parse_errors

    rows = []
    for idx, row in df.iterrows():
        row_num = idx + 2  # +2 because header is row 1, data starts row 2
        row_dict = {
            'row_number': row_num,
            'date': str(row.get('date', '')).strip(),
            'description': str(row.get('description', '')).strip(),
            'paid_by': str(row.get('paid_by', '')).strip(),
            'amount': str(row.get('amount', '')).strip(),
            'currency': str(row.get('currency', '')).strip(),
            'split_type': str(row.get('split_type', '')).strip(),
            'split_with': str(row.get('split_with', '')).strip(),
            'split_details': str(row.get('split_details', '')).strip(),
            'notes': str(row.get('notes', '')).strip(),
        }

        # Skip completely empty rows
        values = [v for k, v in row_dict.items() if k != 'row_number']
        if all(v == '' for v in values):
            continue

        rows.append(row_dict)

    return rows, parse_errors
