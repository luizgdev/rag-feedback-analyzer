import os
import pandas as pd
import chromadb
import requests
import io
from pathlib import Path

# --- CONFIGURATION & PATHS ---
# This ensures paths work regardless of where you run the script from
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DB_PATH = PROJECT_ROOT / "chroma_db_data"

# Stable URL for the dataset (using the GitHub Raw version we validated)
DATASET_URL = "https://raw.githubusercontent.com/Rahulkumarr2080/Comcast-Telecom-Consumer-Complaints/master/Comcast_telecom_complaints_data.csv"


def download_or_load_data():
    """
    Attempts to download data from GitHub.
    If it fails, looks for a local CSV in data/raw.
    """
    print(f"📂 Setup: Raw Data Directory -> {DATA_RAW_DIR}")
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Try Download
    try:
        print(f"⬇️ Attempting download from GitHub...")
        response = requests.get(DATASET_URL, timeout=10)
        response.raise_for_status()

        # Load directly into Pandas
        df = pd.read_csv(io.StringIO(response.content.decode("utf-8")))
        print(f"✅ Download successful! Loaded {len(df)} rows.")

        # Save a backup locally
        backup_path = DATA_RAW_DIR / "comcast_complaints.csv"
        df.to_csv(backup_path, index=False)
        print(f"💾 Backup saved to: {backup_path}")

        return df

    except Exception as e:
        print(f"⚠️ Download failed: {e}")
        print("🔍 Searching for local files...")

        # 2. Fallback to Local File
        csv_files = list(DATA_RAW_DIR.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(
                f"No CSV found in {DATA_RAW_DIR} and download failed."
            )

        target_file = csv_files[0]
        print(f"✅ Found local file: {target_file.name}")
        return pd.read_csv(target_file)


def clean_data(df):
    """
    Standardizes column names and removes empty rows.
    """
    print("🧹 Cleaning data...")
    # Normalize columns
    df.columns = (
        df.columns.str.lower().str.strip().str.replace(" ", "_").str.replace("-", "_")
    )

    # Identify text column
    text_col = "customer_complaint"
    if text_col not in df.columns:
        raise ValueError(f"Column '{text_col}' not found in dataset.")

    # Drop missing
    initial_count = len(df)
    df = df.dropna(subset=[text_col])
    print(
        f"   Rows: {initial_count} -> {len(df)} (Dropped {initial_count - len(df)} empty rows)"
    )

    return df


def ingest_to_chroma(df):
    """
    Resets the database and inserts new embeddings.
    """
    print(f"⚙️ Connecting to Vector Store at: {DB_PATH}")

    # Initialize Client
    client = chromadb.PersistentClient(path=str(DB_PATH))
    collection_name = "customer_feedback"

    # Get or Create Collection
    collection = client.get_or_create_collection(name=collection_name)

    # 1. Reset (Clear existing data)
    if collection.count() > 0:
        print(f"   Existing docs found: {collection.count()}. Purging...")
        existing_ids = collection.get()["ids"]
        if existing_ids:
            collection.delete(ids=existing_ids)
        print("   ✅ Collection cleared.")

    # 2. Prepare Data (Sample 1000 for performance if needed)
    # Using 1000 to be safe on CPU, remove .head(1000) for full production
    df_subset = df.sample(1000, random_state=42) if len(df) > 1000 else df.copy()

    documents = df_subset["customer_complaint"].tolist()
    ids = [f"ticket_{i}" for i in range(len(documents))]

    metadatas = []
    for _, row in df_subset.iterrows():
        metadatas.append(
            {
                "status": str(row.get("status", "Unknown")),
                "ticket_id": str(row.get("ticket_#", "Unknown")),
                "source": "Production Pipeline",
            }
        )

    # 3. Insert
    print(f"🚀 Ingesting {len(documents)} documents (Generating Embeddings)...")
    collection.add(documents=documents, ids=ids, metadatas=metadatas)

    print(f"🎉 SUCCESS! Database populated with {collection.count()} records.")


def main():
    print("--- 🚀 STARTING INGESTION PIPELINE ---")

    try:
        df = download_or_load_data()
        df_clean = clean_data(df)
        ingest_to_chroma(df_clean)
        print("--- ✅ PIPELINE FINISHED ---")

    except Exception as e:
        print(f"\n❌ PIPELINE FAILED: {e}")


if __name__ == "__main__":
    main()
