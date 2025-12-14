"""
Unit tests for the data models.

Tests follow the Given/When/Then pattern for clarity.
"""

from scripts.lib.models import Asset, ScanResult, CSV_COLUMNS


class TestAsset:
    """Tests for the Asset model."""

    def test_to_csv_row_includes_all_columns(self):
        """
        Given an Asset with all fields populated
        When converting to CSV row
        Then all columns should be present in order
        """
        # Given
        asset = Asset(
            chain="ethereum",
            asset_name="Bored Ape #1234",
            symbol="BAYC",
            asset_address="0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
            quantity="1",
            token_type="ERC721",
            token_id="1234",
            collection_name="Bored Ape Yacht Club",
            is_spam=False,
        )

        # When
        row = asset.to_csv_row()

        # Then
        assert len(row) == len(CSV_COLUMNS)
        assert row[0] == "ethereum"  # chain
        assert row[1] == "Bored Ape #1234"  # asset_name
        assert row[2] == "BAYC"  # symbol
        assert row[3] == "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"  # asset_address
        assert row[4] == "1"  # quantity
        assert row[5] == "ERC721"  # token_type
        assert row[6] == "1234"  # token_id
        assert row[7] == "Bored Ape Yacht Club"  # collection_name

    def test_to_csv_row_handles_none_values(self):
        """
        Given an Asset with None values for optional fields
        When converting to CSV row
        Then None should become empty string
        """
        # Given
        asset = Asset(
            chain="ethereum",
            asset_name="ETH",
            symbol="ETH",
            asset_address="NATIVE",
            quantity="1.5",
            token_type="NATIVE",
            token_id=None,
            collection_name=None,
        )

        # When
        row = asset.to_csv_row()

        # Then
        assert row[6] == ""  # token_id
        assert row[7] == ""  # collection_name

    def test_default_is_spam_is_false(self):
        """
        Given an Asset created without is_spam
        When checking is_spam
        Then it should default to False
        """
        # Given / When
        asset = Asset(
            chain="solana",
            asset_name="SOL",
            symbol="SOL",
            asset_address="NATIVE",
            quantity="10",
            token_type="NATIVE",
        )

        # Then
        assert asset.is_spam is False


class TestScanResult:
    """Tests for the ScanResult model."""

    def test_default_counts_are_zero(self):
        """
        Given a ScanResult with just required fields
        When checking counts
        Then they should default to zero
        """
        # Given / When
        result = ScanResult(
            chain="ethereum",
            assets=[],
            spam_assets=[],
        )

        # Then
        assert result.native_count == 0
        assert result.token_count == 0
        assert result.nft_count == 0
        assert result.erc721_count == 0
        assert result.erc1155_count == 0
        assert result.spam_count == 0
        assert result.error is None

    def test_can_store_error_message(self):
        """
        Given a ScanResult with an error
        When accessing error
        Then the error message should be available
        """
        # Given / When
        result = ScanResult(
            chain="ethereum",
            assets=[],
            spam_assets=[],
            error="API request failed: 503 Service Unavailable",
        )

        # Then
        assert result.error is not None
        assert "503" in result.error


class TestCSVColumns:
    """Tests for CSV_COLUMNS constant."""

    def test_csv_columns_has_correct_order(self):
        """
        Given the CSV_COLUMNS constant
        When checking column order
        Then columns should be in the expected order
        """
        # Then
        assert CSV_COLUMNS == [
            "chain",
            "asset_name",
            "symbol",
            "asset_address",
            "quantity",
            "token_type",
            "token_id",
            "collection_name",
        ]
