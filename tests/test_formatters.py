"""
Unit tests for the formatters module.

Tests follow the Given/When/Then pattern for clarity.
"""

import io
import os
import tempfile
from unittest.mock import patch

from scripts.lib.formatters import (
    combine_scan_results,
    generate_filenames,
    generate_timestamp,
    write_csv,
    write_csv_to_stream,
)
from scripts.lib.models import Asset, ScanResult, CSV_COLUMNS


class TestGenerateTimestamp:
    """Tests for generate_timestamp function."""

    def test_returns_string_in_correct_format(self):
        """
        Given the current time
        When generating a timestamp
        Then it should be in YYYYMMDD_HHMMSS format
        """
        # When
        timestamp = generate_timestamp()

        # Then
        assert len(timestamp) == 15  # YYYYMMDD_HHMMSS
        assert timestamp[8] == "_"
        assert timestamp[:8].isdigit()
        assert timestamp[9:].isdigit()

    @patch("scripts.lib.formatters.datetime")
    def test_uses_current_time(self, mock_datetime):
        """
        Given a specific datetime
        When generating a timestamp
        Then it should format that datetime
        """
        # Given
        mock_datetime.now.return_value.strftime.return_value = "20241214_153022"

        # When
        timestamp = generate_timestamp()

        # Then
        assert timestamp == "20241214_153022"


class TestGenerateFilenames:
    """Tests for generate_filenames function."""

    def test_generates_main_and_spam_filenames(self):
        """
        Given a base path and timestamp
        When generating filenames
        Then both main and spam filenames should be returned
        """
        # Given
        base_path = "wallet_report.csv"
        timestamp = "20241214_153022"

        # When
        main_file, spam_file = generate_filenames(base_path, timestamp)

        # Then
        assert main_file == "wallet_report_20241214_153022.csv"
        assert spam_file == "wallet_report_20241214_153022_spam.csv"

    def test_handles_path_with_directory(self):
        """
        Given a base path with directory
        When generating filenames
        Then directory should be preserved
        """
        # Given
        base_path = "/path/to/wallet_report.csv"
        timestamp = "20241214_153022"

        # When
        main_file, spam_file = generate_filenames(base_path, timestamp)

        # Then
        assert main_file == "/path/to/wallet_report_20241214_153022.csv"
        assert spam_file == "/path/to/wallet_report_20241214_153022_spam.csv"

    def test_generates_timestamp_if_not_provided(self):
        """
        Given a base path without timestamp
        When generating filenames
        Then a timestamp should be automatically generated
        """
        # Given
        base_path = "report.csv"

        # When
        main_file, spam_file = generate_filenames(base_path)

        # Then
        # Should have format: report_YYYYMMDD_HHMMSS.csv
        assert main_file.startswith("report_")
        assert main_file.endswith(".csv")
        assert len(main_file) == len("report_20241214_153022.csv")

    def test_handles_no_extension(self):
        """
        Given a base path without extension
        When generating filenames
        Then .csv should be used as default
        """
        # Given
        base_path = "report"
        timestamp = "20241214_153022"

        # When
        main_file, spam_file = generate_filenames(base_path, timestamp)

        # Then
        assert main_file == "report_20241214_153022.csv"
        assert spam_file == "report_20241214_153022_spam.csv"


class TestWriteCsvToStream:
    """Tests for write_csv_to_stream function."""

    def test_writes_header_row(self):
        """
        Given an empty list of assets
        When writing to stream
        Then only the header should be written
        """
        # Given
        assets = []
        stream = io.StringIO()

        # When
        write_csv_to_stream(assets, stream)

        # Then
        output = stream.getvalue()
        lines = output.strip().split("\n")
        assert len(lines) == 1
        assert lines[0] == ",".join(CSV_COLUMNS)

    def test_writes_asset_rows(self):
        """
        Given a list of assets
        When writing to stream
        Then each asset should be a row
        """
        # Given
        assets = [
            Asset(
                chain="ethereum",
                asset_name="Ethereum",
                symbol="ETH",
                asset_address="NATIVE",
                quantity="1.5",
                token_type="NATIVE",
            ),
            Asset(
                chain="ethereum",
                asset_name="USD Coin",
                symbol="USDC",
                asset_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                quantity="100",
                token_type="ERC20",
            ),
        ]
        stream = io.StringIO()

        # When
        write_csv_to_stream(assets, stream)

        # Then
        output = stream.getvalue()
        lines = output.strip().split("\n")
        assert len(lines) == 3  # Header + 2 assets
        assert "ethereum,Ethereum,ETH,NATIVE,1.5,NATIVE,," in lines[1]
        assert "ethereum,USD Coin,USDC,0xA0b86991" in lines[2]

    def test_handles_nft_with_token_id(self):
        """
        Given an NFT asset with token_id
        When writing to stream
        Then token_id should be in the output
        """
        # Given
        nft = Asset(
            chain="ethereum",
            asset_name="BAYC #1234",
            symbol="",
            asset_address="0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
            quantity="1",
            token_type="ERC721",
            token_id="1234",
            collection_name="Bored Ape Yacht Club",
        )
        stream = io.StringIO()

        # When
        write_csv_to_stream([nft], stream)

        # Then
        output = stream.getvalue()
        assert "1234" in output
        assert "Bored Ape Yacht Club" in output


class TestWriteCsv:
    """Tests for write_csv function."""

    def test_writes_to_stdout_when_no_output_path(self, capsys):
        """
        Given assets and no output path
        When writing CSV
        Then output should go to stdout
        """
        # Given
        assets = [
            Asset(
                chain="ethereum",
                asset_name="ETH",
                symbol="ETH",
                asset_address="NATIVE",
                quantity="1",
                token_type="NATIVE",
            )
        ]

        # When
        main_file, spam_file = write_csv(assets, [], None)

        # Then
        assert main_file is None
        assert spam_file is None
        captured = capsys.readouterr()
        assert "ethereum" in captured.out

    def test_writes_to_files_when_output_path_provided(self):
        """
        Given assets and an output path
        When writing CSV
        Then files should be created with correct names
        """
        # Given
        assets = [
            Asset(
                chain="ethereum",
                asset_name="ETH",
                symbol="ETH",
                asset_address="NATIVE",
                quantity="1",
                token_type="NATIVE",
            )
        ]
        spam_assets = [
            Asset(
                chain="ethereum",
                asset_name="Spam NFT",
                symbol="",
                asset_address="0xSpam",
                quantity="1",
                token_type="ERC721",
                is_spam=True,
            )
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "report.csv")

            # When
            main_file, spam_file = write_csv(assets, spam_assets, output_path)

            # Then
            assert main_file is not None
            assert spam_file is not None
            assert os.path.exists(main_file)
            assert os.path.exists(spam_file)

            # Verify content
            with open(main_file) as f:
                content = f.read()
                assert "ethereum" in content
                assert "ETH" in content

            with open(spam_file) as f:
                content = f.read()
                assert "Spam NFT" in content

    def test_does_not_create_spam_file_when_no_spam(self):
        """
        Given assets with no spam
        When writing CSV
        Then only main file should be created
        """
        # Given
        assets = [
            Asset(
                chain="ethereum",
                asset_name="ETH",
                symbol="ETH",
                asset_address="NATIVE",
                quantity="1",
                token_type="NATIVE",
            )
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "report.csv")

            # When
            main_file, spam_file = write_csv(assets, [], output_path)

            # Then
            assert main_file is not None
            assert spam_file is None
            assert os.path.exists(main_file)


class TestCombineScanResults:
    """Tests for combine_scan_results function."""

    def test_combines_assets_from_multiple_chains(self):
        """
        Given scan results from multiple chains
        When combining results
        Then all assets should be in the combined list
        """
        # Given
        results = [
            ScanResult(
                chain="ethereum",
                assets=[
                    Asset(
                        chain="ethereum",
                        asset_name="ETH",
                        symbol="ETH",
                        asset_address="NATIVE",
                        quantity="1",
                        token_type="NATIVE",
                    )
                ],
                spam_assets=[],
            ),
            ScanResult(
                chain="polygon",
                assets=[
                    Asset(
                        chain="polygon",
                        asset_name="MATIC",
                        symbol="MATIC",
                        asset_address="NATIVE",
                        quantity="100",
                        token_type="NATIVE",
                    )
                ],
                spam_assets=[],
            ),
        ]

        # When
        all_assets, all_spam = combine_scan_results(results)

        # Then
        assert len(all_assets) == 2
        chains = [a.chain for a in all_assets]
        assert "ethereum" in chains
        assert "polygon" in chains

    def test_combines_spam_assets_separately(self):
        """
        Given scan results with spam assets
        When combining results
        Then spam should be in separate list
        """
        # Given
        results = [
            ScanResult(
                chain="ethereum",
                assets=[
                    Asset(
                        chain="ethereum",
                        asset_name="ETH",
                        symbol="ETH",
                        asset_address="NATIVE",
                        quantity="1",
                        token_type="NATIVE",
                    )
                ],
                spam_assets=[
                    Asset(
                        chain="ethereum",
                        asset_name="Spam",
                        symbol="",
                        asset_address="0xSpam",
                        quantity="1",
                        token_type="ERC721",
                        is_spam=True,
                    )
                ],
            ),
        ]

        # When
        all_assets, all_spam = combine_scan_results(results)

        # Then
        assert len(all_assets) == 1
        assert len(all_spam) == 1
        assert all_spam[0].is_spam is True

    def test_skips_results_with_errors(self):
        """
        Given scan results including one with error
        When combining results
        Then error result should be skipped
        """
        # Given
        results = [
            ScanResult(
                chain="ethereum",
                assets=[
                    Asset(
                        chain="ethereum",
                        asset_name="ETH",
                        symbol="ETH",
                        asset_address="NATIVE",
                        quantity="1",
                        token_type="NATIVE",
                    )
                ],
                spam_assets=[],
            ),
            ScanResult(
                chain="polygon",
                assets=[],
                spam_assets=[],
                error="API error",
            ),
        ]

        # When
        all_assets, all_spam = combine_scan_results(results)

        # Then
        assert len(all_assets) == 1
        assert all_assets[0].chain == "ethereum"
