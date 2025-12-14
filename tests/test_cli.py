"""
Unit tests for the CLI module.

Tests follow the Given/When/Then pattern for clarity.
"""

import pytest

from scripts.show_current_wallet_assets import validate_networks, SUPPORTED_NETWORKS


class TestValidateNetworks:
    """Tests for validate_networks function."""

    def test_normalizes_network_names_to_lowercase(self):
        """
        Given network names in mixed case
        When validating networks
        Then they should be normalized to lowercase
        """
        # Given
        networks = ["ETHEREUM", "Polygon", "Base"]

        # When
        result = validate_networks(networks)

        # Then
        assert result == ["ethereum", "polygon", "base"]

    def test_raises_error_for_unsupported_network(self):
        """
        Given a list with an unsupported network
        When validating networks
        Then a ValueError should be raised
        """
        # Given
        networks = ["ethereum", "unsupported_chain"]

        # When / Then
        with pytest.raises(ValueError, match="Unsupported network: unsupported_chain"):
            validate_networks(networks)

    def test_accepts_all_supported_networks(self):
        """
        Given all supported networks
        When validating networks
        Then all should be accepted
        """
        # Given
        networks = SUPPORTED_NETWORKS.copy()

        # When
        result = validate_networks(networks)

        # Then
        assert result == SUPPORTED_NETWORKS

    def test_validates_single_network(self):
        """
        Given a single valid network
        When validating networks
        Then it should be returned in a list
        """
        # Given
        networks = ["solana"]

        # When
        result = validate_networks(networks)

        # Then
        assert result == ["solana"]
