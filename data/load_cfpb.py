"""
CFPB Complaint Database Loader

Downloads and loads the Consumer Financial Protection Bureau complaint data
into the Django database for training ML models and data mining analysis.

Dataset: https://www.consumerfinance.gov/data-research/consumer-complaints/
Direct CSV: https://files.consumerfinance.gov/ccdb/complaints.csv.zip

Usage:
    python manage.py load_data           # Download and load (first 100k rows)
    python manage.py load_data --limit 50000  # Custom limit
    python manage.py load_data --file path/to/complaints.csv  # From local file
"""
import csv
import io
import os
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

CFPB_URL = "https://files.consumerfinance.gov/ccdb/complaints.csv.zip"
DATA_DIR = Path(__file__).parent


def download_cfpb_data(output_dir=None):
    """Download CFPB complaint CSV from the official source."""
    if output_dir is None:
        output_dir = DATA_DIR

    zip_path = output_dir / "complaints.csv.zip"
    csv_path = output_dir / "complaints.csv"

    if csv_path.exists():
        print(f"CSV already exists at {csv_path}")
        return csv_path

    print(f"Downloading CFPB data from {CFPB_URL}...")
    urlretrieve(CFPB_URL, zip_path)
    print("Download complete. Extracting...")

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(output_dir)

    if zip_path.exists():
        os.remove(zip_path)

    print(f"Extracted to {csv_path}")
    return csv_path


def parse_cfpb_csv(csv_path, limit=100000):
    """Parse CFPB CSV and yield row dicts."""
    count = 0
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if limit and count >= limit:
                break
            yield row
            count += 1
