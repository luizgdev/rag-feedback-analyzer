import pandas as pd
import pytest
from src.ingest_data import clean_data


def test_clean_data_removes_empty_rows():
    """
    Validates that rows with missing complaint text are removed.
    """
    # 1. Setup: Create mock dirty data
    raw_data = {
        "Ticket #": ["1", "2", "3"],
        "Customer Complaint": [
            "Internet slow",
            None,
            "Billing issue",
        ],  # One None value
        "Status": ["Open", "Closed", "Open"],
    }
    df_raw = pd.DataFrame(raw_data)

    # 2. Action: Run the cleaning function
    df_clean = clean_data(df_raw)

    # 3. Assert: Verify results
    # Should result in 2 rows (removing the None)
    assert len(df_clean) == 2

    # Check if columns were normalized to snake_case
    assert "customer_complaint" in df_clean.columns
    assert "ticket_#" in df_clean.columns


def test_clean_data_normalizes_columns():
    """
    Validates that column names are converted to lowercase snake_case.
    """
    df_raw = pd.DataFrame({"My Column Name": ["Value"], "customer_complaint": ["Text"]})

    df_clean = clean_data(df_raw)

    assert "my_column_name" in df_clean.columns
