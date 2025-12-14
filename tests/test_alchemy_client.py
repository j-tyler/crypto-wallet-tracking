"""
Unit tests for the Alchemy API client.

Tests follow the Given/When/Then pattern for clarity.
"""

import pytest
import requests
import responses

from scripts.lib.alchemy_client import (
    AlchemyClient,
    AlchemyAPIError,
    AlchemyRateLimitError,
    NETWORK_ENDPOINTS,
    TokenBalance,
    TokenMetadata,
    NFT,
    SolanaAsset,
)


class TestAlchemyClientConfiguration:
    """Tests for client configuration and URL generation."""

    def test_get_base_url_returns_correct_url_for_each_network(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient with a valid API key
        When getting the base URL for each supported network
        Then the correct endpoint URL should be returned
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When / Then
        for network, endpoint in NETWORK_ENDPOINTS.items():
            url = client._get_base_url(network)
            assert url == f"https://{endpoint}/v2/{mock_alchemy_api_key}"

    def test_get_base_url_raises_error_for_unsupported_network(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient
        When requesting the URL for an unsupported network
        Then a ValueError should be raised
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When / Then
        with pytest.raises(ValueError, match="Unsupported network"):
            client._get_base_url("unsupported_network")

    def test_get_nft_api_url_returns_correct_url(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient
        When getting the NFT API URL for a network
        Then the correct NFT API endpoint should be returned
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When
        url = client._get_nft_api_url("ethereum")

        # Then
        assert url == f"https://eth-mainnet.g.alchemy.com/nft/v3/{mock_alchemy_api_key}"

    def test_native_token_info_returns_correct_config(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient
        When requesting native token info for each network
        Then the correct token symbol, name, and decimals should be returned
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When / Then
        eth_info = client.get_native_token_info("ethereum")
        assert eth_info["symbol"] == "ETH"
        assert eth_info["decimals"] == 18

        sol_info = client.get_native_token_info("solana")
        assert sol_info["symbol"] == "SOL"
        assert sol_info["decimals"] == 9


class TestRateLimitHandling:
    """Tests for 429 rate limit retry behavior."""

    @responses.activate
    def test_retries_on_429_with_exponential_backoff(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient configured with retry settings
        When a 429 response is received
        Then the client should retry with exponential backoff
        """
        # Given
        client = AlchemyClient(
            mock_alchemy_api_key,
            initial_delay=0.01,  # Use small delays for testing
            max_retries=3,
            jitter=0,  # Disable jitter for predictable timing
        )

        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        # First two calls return 429, third succeeds
        responses.add(responses.POST, url, status=429)
        responses.add(responses.POST, url, status=429)
        responses.add(
            responses.POST,
            url,
            json={"jsonrpc": "2.0", "id": 1, "result": "0x123"},
            status=200,
        )

        # When
        result = client._request("ethereum", "test_method", [])

        # Then
        assert result == "0x123"
        assert len(responses.calls) == 3

    @responses.activate
    def test_raises_rate_limit_error_after_max_retries(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient with limited retries
        When 429 responses persist beyond max retries
        Then AlchemyRateLimitError should be raised
        """
        # Given
        client = AlchemyClient(
            mock_alchemy_api_key,
            initial_delay=0.001,
            max_retries=2,
            jitter=0,
        )

        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        # All calls return 429
        for _ in range(4):
            responses.add(responses.POST, url, status=429)

        # When / Then
        with pytest.raises(AlchemyRateLimitError) as exc_info:
            client._request("ethereum", "test_method", [])

        assert exc_info.value.status_code == 429
        assert len(responses.calls) == 3  # Initial + 2 retries

    @responses.activate
    def test_retries_on_server_error(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient
        When a 500 server error is received
        Then the client should retry with backoff
        """
        # Given
        client = AlchemyClient(
            mock_alchemy_api_key,
            initial_delay=0.001,
            max_retries=2,
            jitter=0,
        )

        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        # First call returns 500, second succeeds
        responses.add(responses.POST, url, status=500)
        responses.add(
            responses.POST,
            url,
            json={"jsonrpc": "2.0", "id": 1, "result": "0xabc"},
            status=200,
        )

        # When
        result = client._request("ethereum", "test_method", [])

        # Then
        assert result == "0xabc"
        assert len(responses.calls) == 2

    def test_jitter_applies_randomization_to_delay(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient with jitter enabled
        When calculating delay with jitter
        Then the delay should be within the expected range
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key, jitter=0.1)
        base_delay = 1.0

        # When
        jittered_delays = [client._apply_jitter(base_delay) for _ in range(100)]

        # Then
        for delay in jittered_delays:
            assert 0.9 <= delay <= 1.1  # ±10%


class TestErrorHandling:
    """Tests for error handling."""

    @responses.activate
    def test_raises_error_for_invalid_api_key(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient with an invalid API key
        When making a request
        Then AlchemyAPIError should be raised with 401 status
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        responses.add(
            responses.POST,
            url,
            json={"error": {"code": 401, "message": "Invalid API key"}},
            status=401,
        )

        # When / Then
        with pytest.raises(AlchemyAPIError) as exc_info:
            client._request("ethereum", "test_method", [])

        assert exc_info.value.status_code == 401

    @responses.activate
    def test_raises_error_for_api_error_in_response(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient
        When the API returns an error in the response body
        Then AlchemyAPIError should be raised
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32600, "message": "Invalid request"},
            },
            status=200,
        )

        # When / Then
        with pytest.raises(AlchemyAPIError, match="Invalid request"):
            client._request("ethereum", "test_method", [])


class TestGetNativeBalance:
    """Tests for get_native_balance method."""

    @responses.activate
    def test_returns_balance_as_integer(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given an AlchemyClient and a wallet address
        When calling get_native_balance
        Then the balance should be returned as an integer in wei
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        # Balance of 1.5 ETH in wei (hex)
        balance_hex = hex(1500000000000000000)
        responses.add(
            responses.POST,
            url,
            json={"jsonrpc": "2.0", "id": 1, "result": balance_hex},
            status=200,
        )

        # When
        balance = client.get_native_balance("ethereum", sample_wallet_address)

        # Then
        assert balance == 1500000000000000000
        assert isinstance(balance, int)

    def test_raises_error_for_solana_network(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given an AlchemyClient
        When calling get_native_balance for Solana
        Then a ValueError should be raised
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When / Then
        with pytest.raises(ValueError, match="Use get_solana_assets"):
            client.get_native_balance("solana", sample_wallet_address)


class TestGetTokenBalances:
    """Tests for get_token_balances method."""

    @responses.activate
    def test_returns_list_of_token_balances(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given an AlchemyClient and a wallet with ERC-20 tokens
        When calling get_token_balances
        Then a list of TokenBalance objects should be returned
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "address": sample_wallet_address,
                    "tokenBalances": [
                        {
                            "contractAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                            "tokenBalance": "0x5f5e100",  # 100 USDC
                        },
                        {
                            "contractAddress": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
                            "tokenBalance": "0x2540be400",  # 10000 USDT
                        },
                    ],
                },
            },
            status=200,
        )

        # When
        balances = client.get_token_balances("ethereum", sample_wallet_address)

        # Then
        assert len(balances) == 2
        assert isinstance(balances[0], TokenBalance)
        assert balances[0].contract_address == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        assert balances[0].balance == "0x5f5e100"

    @responses.activate
    def test_paginates_through_all_results(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given an AlchemyClient and a wallet with many tokens
        When calling get_token_balances with pagination
        Then all pages should be fetched and combined
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        # First page with pageKey
        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "address": sample_wallet_address,
                    "tokenBalances": [
                        {
                            "contractAddress": "0xToken1",
                            "tokenBalance": "0x100",
                        }
                    ],
                    "pageKey": "next_page_key",
                },
            },
            status=200,
        )

        # Second page without pageKey (last page)
        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "address": sample_wallet_address,
                    "tokenBalances": [
                        {
                            "contractAddress": "0xToken2",
                            "tokenBalance": "0x200",
                        }
                    ],
                },
            },
            status=200,
        )

        # When
        balances = client.get_token_balances("ethereum", sample_wallet_address)

        # Then
        assert len(balances) == 2
        assert balances[0].contract_address == "0xToken1"
        assert balances[1].contract_address == "0xToken2"
        assert len(responses.calls) == 2

    @responses.activate
    def test_skips_zero_balance_tokens(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given an AlchemyClient and a wallet with some zero-balance tokens
        When calling get_token_balances
        Then zero-balance tokens should be filtered out
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "address": sample_wallet_address,
                    "tokenBalances": [
                        {
                            "contractAddress": "0xWithBalance",
                            "tokenBalance": "0x100",
                        },
                        {
                            "contractAddress": "0xZeroBalance",
                            "tokenBalance": "0x0",
                        },
                    ],
                },
            },
            status=200,
        )

        # When
        balances = client.get_token_balances("ethereum", sample_wallet_address)

        # Then
        assert len(balances) == 1
        assert balances[0].contract_address == "0xWithBalance"


class TestGetTokenMetadata:
    """Tests for get_token_metadata method."""

    @responses.activate
    def test_returns_token_metadata(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient and a token contract address
        When calling get_token_metadata
        Then the token metadata should be returned
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"
        usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "name": "USD Coin",
                    "symbol": "USDC",
                    "decimals": 6,
                    "logo": "https://example.com/usdc.png",
                },
            },
            status=200,
        )

        # When
        metadata = client.get_token_metadata("ethereum", usdc_address)

        # Then
        assert isinstance(metadata, TokenMetadata)
        assert metadata.name == "USD Coin"
        assert metadata.symbol == "USDC"
        assert metadata.decimals == 6
        assert metadata.logo == "https://example.com/usdc.png"

    @responses.activate
    def test_handles_missing_metadata_fields(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient and a token with incomplete metadata
        When calling get_token_metadata
        Then missing fields should be None
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "decimals": 18,
                },
            },
            status=200,
        )

        # When
        metadata = client.get_token_metadata("ethereum", "0xSomeToken")

        # Then
        assert metadata.name is None
        assert metadata.symbol is None
        assert metadata.decimals == 18
        assert metadata.logo is None


class TestGetNFTsForOwner:
    """Tests for get_nfts_for_owner method."""

    @responses.activate
    def test_returns_list_of_nfts(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given an AlchemyClient and a wallet with NFTs
        When calling get_nfts_for_owner
        Then a list of NFT objects should be returned
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        url = f"https://eth-mainnet.g.alchemy.com/nft/v3/{mock_alchemy_api_key}/getNFTsForOwner"

        responses.add(
            responses.GET,
            url,
            json={
                "ownedNfts": [
                    {
                        "contract": {
                            "address": "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
                            "name": "Bored Ape Yacht Club",
                            "tokenType": "ERC721",
                            "isSpam": False,
                        },
                        "tokenId": "1234",
                        "tokenType": "ERC721",
                        "name": "BAYC #1234",
                        "balance": "1",
                    }
                ],
                "totalCount": 1,
            },
            status=200,
        )

        # When
        nfts = client.get_nfts_for_owner("ethereum", sample_wallet_address)

        # Then
        assert len(nfts) == 1
        assert isinstance(nfts[0], NFT)
        assert nfts[0].contract_address == "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"
        assert nfts[0].token_id == "1234"
        assert nfts[0].token_type == "ERC721"
        assert nfts[0].collection_name == "Bored Ape Yacht Club"
        assert nfts[0].is_spam is False

    @responses.activate
    def test_paginates_through_all_nfts(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given an AlchemyClient and a wallet with many NFTs
        When calling get_nfts_for_owner with pagination
        Then all pages should be fetched and combined
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        url = f"https://eth-mainnet.g.alchemy.com/nft/v3/{mock_alchemy_api_key}/getNFTsForOwner"

        # First page with pageKey
        responses.add(
            responses.GET,
            url,
            json={
                "ownedNfts": [
                    {
                        "contract": {"address": "0xNFT1", "name": "Collection1"},
                        "tokenId": "1",
                        "tokenType": "ERC721",
                        "balance": "1",
                    }
                ],
                "pageKey": "next_page",
            },
            status=200,
        )

        # Second page without pageKey
        responses.add(
            responses.GET,
            url,
            json={
                "ownedNfts": [
                    {
                        "contract": {"address": "0xNFT2", "name": "Collection2"},
                        "tokenId": "2",
                        "tokenType": "ERC721",
                        "balance": "1",
                    }
                ],
            },
            status=200,
        )

        # When
        nfts = client.get_nfts_for_owner("ethereum", sample_wallet_address)

        # Then
        assert len(nfts) == 2
        assert nfts[0].contract_address == "0xNFT1"
        assert nfts[1].contract_address == "0xNFT2"
        assert len(responses.calls) == 2

    @responses.activate
    def test_identifies_spam_nfts(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given an AlchemyClient and a wallet with spam NFTs
        When calling get_nfts_for_owner
        Then spam NFTs should be marked as is_spam=True
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        url = f"https://eth-mainnet.g.alchemy.com/nft/v3/{mock_alchemy_api_key}/getNFTsForOwner"

        responses.add(
            responses.GET,
            url,
            json={
                "ownedNfts": [
                    {
                        "contract": {
                            "address": "0xSpamNFT",
                            "name": "Free Airdrop",
                            "isSpam": True,
                        },
                        "tokenId": "999",
                        "tokenType": "ERC721",
                        "balance": "1",
                    }
                ],
            },
            status=200,
        )

        # When
        nfts = client.get_nfts_for_owner("ethereum", sample_wallet_address)

        # Then
        assert len(nfts) == 1
        assert nfts[0].is_spam is True


class TestGetSolanaAssets:
    """Tests for get_solana_assets method."""

    @responses.activate
    def test_returns_list_of_solana_assets(self, mock_alchemy_api_key, sample_solana_address):
        """
        Given an AlchemyClient and a Solana wallet
        When calling get_solana_assets
        Then a list of SolanaAsset objects should be returned
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        url = f"https://solana-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "total": 2,
                    "limit": 1000,
                    "page": 1,
                    "items": [
                        {
                            "id": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                            "interface": "FungibleToken",
                            "content": {
                                "metadata": {
                                    "name": "USD Coin",
                                    "symbol": "USDC",
                                }
                            },
                            "token_info": {
                                "balance": 1000000000,
                                "decimals": 6,
                            },
                        },
                        {
                            "id": "SomeNFTMintAddress",
                            "interface": "V1_NFT",
                            "content": {
                                "metadata": {
                                    "name": "Cool NFT #1",
                                    "symbol": "COOL",
                                }
                            },
                        },
                    ],
                },
            },
            status=200,
        )

        # When
        assets = client.get_solana_assets(sample_solana_address)

        # Then
        assert len(assets) == 2
        assert isinstance(assets[0], SolanaAsset)
        assert assets[0].asset_id == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        assert assets[0].interface == "FungibleToken"
        assert assets[0].symbol == "USDC"
        assert assets[0].balance == 1000000000
        assert assets[0].decimals == 6

        assert assets[1].interface == "V1_NFT"
        assert assets[1].name == "Cool NFT #1"

    @responses.activate
    def test_paginates_through_all_solana_assets(self, mock_alchemy_api_key, sample_solana_address):
        """
        Given an AlchemyClient and a Solana wallet with many assets
        When calling get_solana_assets with pagination
        Then all pages should be fetched
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        url = f"https://solana-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        # First page - returns 1000 items (full page)
        first_page_items = [
            {
                "id": f"Asset{i}",
                "interface": "FungibleToken",
                "content": {"metadata": {"name": f"Token {i}"}},
            }
            for i in range(1000)
        ]

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "total": 1500,
                    "limit": 1000,
                    "page": 1,
                    "items": first_page_items,
                },
            },
            status=200,
        )

        # Second page - returns 500 items (partial page, indicating last)
        second_page_items = [
            {
                "id": f"Asset{i}",
                "interface": "FungibleToken",
                "content": {"metadata": {"name": f"Token {i}"}},
            }
            for i in range(1000, 1500)
        ]

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "total": 1500,
                    "limit": 1000,
                    "page": 2,
                    "items": second_page_items,
                },
            },
            status=200,
        )

        # When
        assets = client.get_solana_assets(sample_solana_address)

        # Then
        assert len(assets) == 1500
        assert len(responses.calls) == 2


class TestNFTAPIRetryBehavior:
    """Tests for NFT API retry behavior."""

    @responses.activate
    def test_nft_api_retries_on_429(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given an AlchemyClient making NFT API requests
        When a 429 response is received
        Then the client should retry with backoff
        """
        # Given
        client = AlchemyClient(
            mock_alchemy_api_key,
            initial_delay=0.001,
            max_retries=2,
            jitter=0,
        )
        url = f"https://eth-mainnet.g.alchemy.com/nft/v3/{mock_alchemy_api_key}/getNFTsForOwner"

        # First call returns 429, second succeeds
        responses.add(responses.GET, url, status=429)
        responses.add(
            responses.GET,
            url,
            json={"ownedNfts": [], "totalCount": 0},
            status=200,
        )

        # When
        nfts = client.get_nfts_for_owner("ethereum", sample_wallet_address)

        # Then
        assert nfts == []
        assert len(responses.calls) == 2

    @responses.activate
    def test_nft_api_raises_error_after_max_retries(
        self, mock_alchemy_api_key, sample_wallet_address
    ):
        """
        Given an AlchemyClient making NFT API requests
        When 429 responses persist beyond max retries
        Then AlchemyRateLimitError should be raised
        """
        # Given
        client = AlchemyClient(
            mock_alchemy_api_key,
            initial_delay=0.001,
            max_retries=1,
            jitter=0,
        )
        url = f"https://eth-mainnet.g.alchemy.com/nft/v3/{mock_alchemy_api_key}/getNFTsForOwner"

        # All calls return 429
        for _ in range(3):
            responses.add(responses.GET, url, status=429)

        # When / Then
        with pytest.raises(AlchemyRateLimitError):
            client.get_nfts_for_owner("ethereum", sample_wallet_address)


class TestAdditionalErrorCases:
    """Additional tests for error handling edge cases."""

    def test_get_nft_api_url_raises_error_for_unsupported_network(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient
        When getting NFT API URL for an unsupported network
        Then a ValueError should be raised
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When / Then
        with pytest.raises(ValueError, match="Unsupported network"):
            client._get_nft_api_url("unsupported_network")

    def test_get_token_balances_raises_error_for_solana(
        self, mock_alchemy_api_key, sample_solana_address
    ):
        """
        Given an AlchemyClient
        When calling get_token_balances for Solana
        Then a ValueError should be raised
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When / Then
        with pytest.raises(ValueError, match="Use get_solana_assets"):
            client.get_token_balances("solana", sample_solana_address)

    def test_get_token_metadata_raises_error_for_solana(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient
        When calling get_token_metadata for Solana
        Then a ValueError should be raised
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When / Then
        with pytest.raises(ValueError, match="Use get_solana_assets"):
            client.get_token_metadata("solana", "SomeTokenMint")

    def test_get_nfts_for_owner_raises_error_for_solana(
        self, mock_alchemy_api_key, sample_solana_address
    ):
        """
        Given an AlchemyClient
        When calling get_nfts_for_owner for Solana
        Then a ValueError should be raised
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When / Then
        with pytest.raises(ValueError, match="Use get_solana_assets"):
            client.get_nfts_for_owner("solana", sample_solana_address)

    def test_get_native_token_info_raises_error_for_unsupported_network(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient
        When calling get_native_token_info for an unsupported network
        Then a ValueError should be raised
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When / Then
        with pytest.raises(ValueError, match="Unsupported network"):
            client.get_native_token_info("unsupported_network")


class TestAPIKeySanitization:
    """Tests for API key sanitization in error messages."""

    def test_sanitize_error_message_removes_api_key(self, mock_alchemy_api_key):
        """
        Given an error message containing the API key
        When sanitizing the message
        Then the API key should be replaced with [REDACTED]
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        message = f"Connection failed: url=/v2/{mock_alchemy_api_key}/some/path"

        # When
        sanitized = client._sanitize_error_message(message)

        # Then
        assert mock_alchemy_api_key not in sanitized
        assert "[REDACTED]" in sanitized
        assert "url=/v2/[REDACTED]/some/path" in sanitized

    def test_sanitize_error_message_handles_no_api_key(self, mock_alchemy_api_key):
        """
        Given an error message without the API key
        When sanitizing the message
        Then the message should be unchanged
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        message = "Connection timeout after 30 seconds"

        # When
        sanitized = client._sanitize_error_message(message)

        # Then
        assert sanitized == message

    @responses.activate
    def test_request_exception_does_not_leak_api_key(self, mock_alchemy_api_key):
        """
        Given an AlchemyClient making a request that fails with a network error
        When the error is raised
        Then the API key should not appear in the error message
        """
        # Given
        client = AlchemyClient(
            mock_alchemy_api_key,
            initial_delay=0.001,
            max_retries=0,
        )
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        # Mock a connection error (simulated by raising an exception)
        responses.add(
            responses.POST,
            url,
            body=requests.exceptions.ConnectionError(f"Connection refused: {url}"),
        )

        # When / Then
        with pytest.raises(AlchemyAPIError) as exc_info:
            client._request("ethereum", "test_method", [])

        error_message = str(exc_info.value)
        assert mock_alchemy_api_key not in error_message
        assert "[REDACTED]" in error_message
