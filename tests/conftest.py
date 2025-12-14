"""
Pytest configuration and shared fixtures for crypto-wallet-tracking tests.
"""

import pytest


@pytest.fixture
def sample_wallet_address():
    """Sample Ethereum wallet address for testing."""
    return "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # vitalik.eth


@pytest.fixture
def sample_solana_address():
    """Sample Solana wallet address for testing."""
    return "GKvqsuNcnwWqPzzuhLmGi4rzzh55FhJtGizkhHaEJqiV"


@pytest.fixture
def mock_alchemy_api_key():
    """Mock Alchemy API key for testing."""
    return "test-api-key-12345"
