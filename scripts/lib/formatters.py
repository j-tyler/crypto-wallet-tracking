"""
Output formatters for crypto wallet asset reports.

This module handles CSV file generation with proper formatting,
timestamp-based filenames, and spam asset separation.
"""

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, TextIO, Tuple

from .models import Asset, CSV_COLUMNS, ScanResult


def generate_timestamp() -> str:
    """
    Generate a timestamp string for filenames.

    Returns:
        Timestamp in YYYYMMDD_HHMMSS format
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def generate_filenames(base_path: str, timestamp: Optional[str] = None) -> Tuple[str, str]:
    """
    Generate timestamped filenames for main and spam CSV files.

    Args:
        base_path: Base output path (e.g., "wallet_report.csv")
        timestamp: Optional timestamp to use (generates new one if not provided)

    Returns:
        Tuple of (main_file_path, spam_file_path)

    Examples:
        generate_filenames("wallet_report.csv", "20241214_153022")
        -> ("wallet_report_20241214_153022.csv", "wallet_report_20241214_153022_spam.csv")
    """
    if timestamp is None:
        timestamp = generate_timestamp()

    path = Path(base_path)
    stem = path.stem
    suffix = path.suffix or ".csv"
    parent = path.parent

    main_file = parent / f"{stem}_{timestamp}{suffix}"
    spam_file = parent / f"{stem}_{timestamp}_spam{suffix}"

    return str(main_file), str(spam_file)


def write_csv_to_stream(assets: List[Asset], stream: TextIO) -> None:
    """
    Write assets to a CSV stream.

    Args:
        assets: List of Asset objects to write
        stream: File-like object to write to
    """
    writer = csv.writer(stream)
    writer.writerow(CSV_COLUMNS)

    for asset in assets:
        writer.writerow(asset.to_csv_row())


def write_csv(
    assets: List[Asset],
    spam_assets: List[Asset],
    output_path: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Write assets to CSV files or stdout.

    Args:
        assets: List of main (non-spam) assets
        spam_assets: List of spam assets
        output_path: Base output path. If None, writes main assets to stdout.

    Returns:
        Tuple of (main_file_path, spam_file_path) if output_path provided,
        otherwise (None, None).
    """
    if output_path is None:
        # Write to stdout
        write_csv_to_stream(assets, sys.stdout)
        return None, None

    timestamp = generate_timestamp()
    main_file, spam_file = generate_filenames(output_path, timestamp)

    # Write main assets
    with open(main_file, "w", newline="", encoding="utf-8") as f:
        write_csv_to_stream(assets, f)

    # Write spam assets (only if there are any)
    if spam_assets:
        with open(spam_file, "w", newline="", encoding="utf-8") as f:
            write_csv_to_stream(spam_assets, f)
        return main_file, spam_file

    return main_file, None


def combine_scan_results(
    results: List[ScanResult],
) -> Tuple[List[Asset], List[Asset]]:
    """
    Combine scan results from multiple chains into unified asset lists.

    Args:
        results: List of ScanResult objects from different chains

    Returns:
        Tuple of (all_assets, all_spam_assets) combined from all chains
    """
    all_assets: List[Asset] = []
    all_spam_assets: List[Asset] = []

    for result in results:
        if result.error is None:
            all_assets.extend(result.assets)
            all_spam_assets.extend(result.spam_assets)

    return all_assets, all_spam_assets
