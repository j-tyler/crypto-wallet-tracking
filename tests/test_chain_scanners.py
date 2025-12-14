"""
Unit tests for the chain scanner classes.

Tests follow the Given/When/Then pattern for clarity.
"""

import pytest
import responses

from scripts.lib.alchemy_client import AlchemyClient
from scripts.lib.chain_scanners import (
    EVMChainScanner,
    SolanaChainScanner,
    create_scanner,
    format_quantity,
)


class TestFormatQuantity:
    """Tests for the format_quantity helper function."""

    def test_formats_whole_number_without_decimals(self):
        """
        Given a balance that results in a whole number
        When formatting with decimals
        Then trailing zeros should be removed
        """
        # Given
        raw_balance = 1000000
        decimals = 6

        # When
        result = format_quantity(raw_balance, decimals)

        # Then
        assert result == "1"

    def test_formats_fractional_number_trimming_zeros(self):
        """
        Given a balance with trailing zeros after decimal
        When formatting
        Then trailing zeros should be trimmed
        """
        # Given
        raw_balance = 1500000
        decimals = 6

        # When
        result = format_quantity(raw_balance, decimals)

        # Then
        assert result == "1.5"

    def test_preserves_full_precision(self):
        """
        Given a balance with many decimal places
        When formatting
        Then full precision should be preserved
        """
        # Given
        raw_balance = 1234567890123456789
        decimals = 18

        # When
        result = format_quantity(raw_balance, decimals)

        # Then
        assert result == "1.234567890123456789"

    def test_handles_zero_balance(self):
        """
        Given a zero balance
        When formatting
        Then should return "0"
        """
        # Given / When
        result = format_quantity(0, 18)

        # Then
        assert result == "0"

    def test_handles_zero_decimals(self):
        """
        Given a balance with zero decimals
        When formatting
        Then should return the raw integer as string
        """
        # Given
        raw_balance = 12345

        # When
        result = format_quantity(raw_balance, 0)

        # Then
        assert result == "12345"

    def test_handles_small_fractional_amounts(self):
        """
        Given a very small balance
        When formatting
        Then should show the small decimal correctly
        """
        # Given - 0.000001 with 6 decimals
        raw_balance = 1
        decimals = 6

        # When
        result = format_quantity(raw_balance, decimals)

        # Then
        assert result == "0.000001"


class TestCreateScanner:
    """Tests for the create_scanner factory function."""

    def test_creates_evm_scanner_for_ethereum(self, mock_alchemy_api_key):
        """
        Given an Alchemy client
        When creating a scanner for ethereum
        Then an EVMChainScanner should be returned
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When
        scanner = create_scanner(client, "ethereum")

        # Then
        assert isinstance(scanner, EVMChainScanner)
        assert scanner.chain == "ethereum"

    def test_creates_evm_scanner_for_polygon(self, mock_alchemy_api_key):
        """
        Given an Alchemy client
        When creating a scanner for polygon
        Then an EVMChainScanner should be returned
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When
        scanner = create_scanner(client, "polygon")

        # Then
        assert isinstance(scanner, EVMChainScanner)
        assert scanner.chain == "polygon"

    def test_creates_solana_scanner_for_solana(self, mock_alchemy_api_key):
        """
        Given an Alchemy client
        When creating a scanner for solana
        Then a SolanaChainScanner should be returned
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When
        scanner = create_scanner(client, "solana")

        # Then
        assert isinstance(scanner, SolanaChainScanner)
        assert scanner.chain == "solana"

    def test_raises_error_for_unsupported_chain(self, mock_alchemy_api_key):
        """
        Given an Alchemy client
        When creating a scanner for an unsupported chain
        Then a ValueError should be raised
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When / Then
        with pytest.raises(ValueError, match="Unsupported chain"):
            create_scanner(client, "unsupported")


class TestEVMChainScanner:
    """Tests for EVMChainScanner."""

    @responses.activate
    def test_scan_returns_native_balance(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given an EVM wallet with native token balance
        When scanning the wallet
        Then the native balance should be included in results
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        scanner = EVMChainScanner(client, "ethereum")
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"
        nft_url = f"https://eth-mainnet.g.alchemy.com/nft/v3/{mock_alchemy_api_key}/getNFTsForOwner"

        # Mock native balance (1.5 ETH)
        responses.add(
            responses.POST,
            url,
            json={"jsonrpc": "2.0", "id": 1, "result": hex(1500000000000000000)},
            status=200,
        )

        # Mock empty token balances
        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"address": sample_wallet_address, "tokenBalances": []},
            },
            status=200,
        )

        # Mock empty NFTs
        responses.add(
            responses.GET,
            nft_url,
            json={"ownedNfts": [], "totalCount": 0},
            status=200,
        )

        # When
        result = scanner.scan(sample_wallet_address)

        # Then
        assert result.error is None
        assert result.native_count == 1
        assert len(result.assets) == 1
        assert result.assets[0].token_type == "NATIVE"
        assert result.assets[0].symbol == "ETH"
        assert result.assets[0].quantity == "1.5"
        assert result.assets[0].asset_address == "NATIVE"

    @responses.activate
    def test_scan_returns_erc20_tokens(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given an EVM wallet with ERC-20 tokens
        When scanning the wallet
        Then the tokens should be included in results with metadata
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        scanner = EVMChainScanner(client, "ethereum")
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"
        nft_url = f"https://eth-mainnet.g.alchemy.com/nft/v3/{mock_alchemy_api_key}/getNFTsForOwner"

        # Mock zero native balance
        responses.add(
            responses.POST,
            url,
            json={"jsonrpc": "2.0", "id": 1, "result": "0x0"},
            status=200,
        )

        # Mock token balances (100 USDC)
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
                            "tokenBalance": hex(100000000),  # 100 USDC (6 decimals)
                        }
                    ],
                },
            },
            status=200,
        )

        # Mock token metadata
        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"name": "USD Coin", "symbol": "USDC", "decimals": 6},
            },
            status=200,
        )

        # Mock empty NFTs
        responses.add(
            responses.GET,
            nft_url,
            json={"ownedNfts": [], "totalCount": 0},
            status=200,
        )

        # When
        result = scanner.scan(sample_wallet_address)

        # Then
        assert result.error is None
        assert result.token_count == 1
        assert len(result.assets) == 1
        assert result.assets[0].token_type == "ERC20"
        assert result.assets[0].symbol == "USDC"
        assert result.assets[0].asset_name == "USD Coin"
        assert result.assets[0].quantity == "100"

    @responses.activate
    def test_scan_separates_spam_nfts(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given an EVM wallet with spam and non-spam NFTs
        When scanning the wallet
        Then spam NFTs should be in spam_assets list
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        scanner = EVMChainScanner(client, "ethereum")
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"
        nft_url = f"https://eth-mainnet.g.alchemy.com/nft/v3/{mock_alchemy_api_key}/getNFTsForOwner"

        # Mock zero native balance
        responses.add(
            responses.POST,
            url,
            json={"jsonrpc": "2.0", "id": 1, "result": "0x0"},
            status=200,
        )

        # Mock empty token balances
        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"address": sample_wallet_address, "tokenBalances": []},
            },
            status=200,
        )

        # Mock NFTs - one regular, one spam
        responses.add(
            responses.GET,
            nft_url,
            json={
                "ownedNfts": [
                    {
                        "contract": {
                            "address": "0xGoodNFT",
                            "name": "Good Collection",
                            "isSpam": False,
                        },
                        "tokenId": "1",
                        "tokenType": "ERC721",
                        "name": "Good NFT #1",
                        "balance": "1",
                    },
                    {
                        "contract": {
                            "address": "0xSpamNFT",
                            "name": "Spam Collection",
                            "isSpam": True,
                        },
                        "tokenId": "999",
                        "tokenType": "ERC721",
                        "name": "Free Airdrop",
                        "balance": "1",
                    },
                ],
                "totalCount": 2,
            },
            status=200,
        )

        # When
        result = scanner.scan(sample_wallet_address)

        # Then
        assert result.error is None
        assert result.nft_count == 1  # Only non-spam counted
        assert result.spam_count == 1
        assert len(result.assets) == 1
        assert len(result.spam_assets) == 1
        assert result.assets[0].collection_name == "Good Collection"
        assert result.spam_assets[0].collection_name == "Spam Collection"
        assert result.spam_assets[0].is_spam is True

    @responses.activate
    def test_scan_handles_api_error(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given an API that returns an error
        When scanning the wallet
        Then the error should be captured in the result
        """
        # Given
        client = AlchemyClient(
            mock_alchemy_api_key,
            initial_delay=0.001,
            max_retries=0,
        )
        scanner = EVMChainScanner(client, "ethereum")
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        # Mock API error
        responses.add(
            responses.POST,
            url,
            json={"error": {"code": -32600, "message": "Invalid request"}},
            status=200,
        )

        # When
        result = scanner.scan(sample_wallet_address)

        # Then
        assert result.error is not None
        assert "Invalid request" in result.error
        assert len(result.assets) == 0

    @responses.activate
    def test_scan_counts_nft_types(self, mock_alchemy_api_key, sample_wallet_address):
        """
        Given a wallet with ERC-721 and ERC-1155 NFTs
        When scanning
        Then the counts should be accurate
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        scanner = EVMChainScanner(client, "ethereum")
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"
        nft_url = f"https://eth-mainnet.g.alchemy.com/nft/v3/{mock_alchemy_api_key}/getNFTsForOwner"

        responses.add(
            responses.POST,
            url,
            json={"jsonrpc": "2.0", "id": 1, "result": "0x0"},
            status=200,
        )
        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"address": sample_wallet_address, "tokenBalances": []},
            },
            status=200,
        )

        responses.add(
            responses.GET,
            nft_url,
            json={
                "ownedNfts": [
                    {
                        "contract": {"address": "0xNFT1", "name": "C1", "isSpam": False},
                        "tokenId": "1",
                        "tokenType": "ERC721",
                        "balance": "1",
                    },
                    {
                        "contract": {"address": "0xNFT2", "name": "C2", "isSpam": False},
                        "tokenId": "2",
                        "tokenType": "ERC721",
                        "balance": "1",
                    },
                    {
                        "contract": {"address": "0xNFT3", "name": "C3", "isSpam": False},
                        "tokenId": "3",
                        "tokenType": "ERC1155",
                        "balance": "5",
                    },
                ],
                "totalCount": 3,
            },
            status=200,
        )

        # When
        result = scanner.scan(sample_wallet_address)

        # Then
        assert result.nft_count == 3
        assert result.erc721_count == 2
        assert result.erc1155_count == 1


class TestSolanaChainScanner:
    """Tests for SolanaChainScanner."""

    @responses.activate
    def test_scan_returns_native_sol_balance(self, mock_alchemy_api_key, sample_solana_address):
        """
        Given a Solana wallet with native SOL
        When scanning the wallet
        Then the SOL balance should be included as NATIVE
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        scanner = SolanaChainScanner(client, "solana")
        url = f"https://solana-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "total": 1,
                    "limit": 1000,
                    "page": 1,
                    "items": [
                        {
                            "id": "So11111111111111111111111111111111111111112",
                            "interface": "FungibleToken",
                            "content": {"metadata": {"name": "Wrapped SOL", "symbol": "SOL"}},
                            "token_info": {"balance": 2500000000, "decimals": 9},
                        }
                    ],
                },
            },
            status=200,
        )

        # When
        result = scanner.scan(sample_solana_address)

        # Then
        assert result.error is None
        assert result.native_count == 1
        native = next(a for a in result.assets if a.token_type == "NATIVE")
        assert native.symbol == "SOL"
        assert native.quantity == "2.5"
        assert native.asset_address == "NATIVE"

    @responses.activate
    def test_scan_returns_spl_tokens(self, mock_alchemy_api_key, sample_solana_address):
        """
        Given a Solana wallet with SPL tokens
        When scanning the wallet
        Then the tokens should be included in results
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        scanner = SolanaChainScanner(client, "solana")
        url = f"https://solana-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "total": 1,
                    "limit": 1000,
                    "page": 1,
                    "items": [
                        {
                            "id": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                            "interface": "FungibleToken",
                            "content": {"metadata": {"name": "USD Coin", "symbol": "USDC"}},
                            "token_info": {"balance": 50000000, "decimals": 6},
                        }
                    ],
                },
            },
            status=200,
        )

        # When
        result = scanner.scan(sample_solana_address)

        # Then
        assert result.error is None
        assert result.token_count == 1
        token = result.assets[0]
        assert token.token_type == "SPL"
        assert token.symbol == "USDC"
        assert token.quantity == "50"

    @responses.activate
    def test_scan_returns_nfts(self, mock_alchemy_api_key, sample_solana_address):
        """
        Given a Solana wallet with NFTs
        When scanning the wallet
        Then the NFTs should be included in results
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        scanner = SolanaChainScanner(client, "solana")
        url = f"https://solana-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "total": 1,
                    "limit": 1000,
                    "page": 1,
                    "items": [
                        {
                            "id": "NFTMintAddress123",
                            "interface": "V1_NFT",
                            "content": {"metadata": {"name": "Cool Solana NFT", "symbol": "COOL"}},
                        }
                    ],
                },
            },
            status=200,
        )

        # When
        result = scanner.scan(sample_solana_address)

        # Then
        assert result.error is None
        assert result.nft_count == 1
        nft = result.assets[0]
        assert nft.token_type == "NFT"
        assert nft.asset_name == "Cool Solana NFT"
        assert nft.quantity == "1"
        assert nft.is_spam is False  # Spam detection not available

    @responses.activate
    def test_scan_never_returns_spam_for_solana(self, mock_alchemy_api_key, sample_solana_address):
        """
        Given a Solana wallet
        When scanning the wallet
        Then spam_assets should always be empty (spam detection not available)
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        scanner = SolanaChainScanner(client, "solana")
        url = f"https://solana-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"total": 0, "limit": 1000, "page": 1, "items": []},
            },
            status=200,
        )

        # When
        result = scanner.scan(sample_solana_address)

        # Then
        assert len(result.spam_assets) == 0

    @responses.activate
    def test_scan_handles_programmable_nfts(self, mock_alchemy_api_key, sample_solana_address):
        """
        Given a Solana wallet with pNFTs
        When scanning the wallet
        Then they should be identified with correct token type
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        scanner = SolanaChainScanner(client, "solana")
        url = f"https://solana-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "total": 1,
                    "limit": 1000,
                    "page": 1,
                    "items": [
                        {
                            "id": "pNFTMintAddress",
                            "interface": "ProgrammableNFT",
                            "content": {"metadata": {"name": "Programmable NFT", "symbol": "PNFT"}},
                        }
                    ],
                },
            },
            status=200,
        )

        # When
        result = scanner.scan(sample_solana_address)

        # Then
        assert result.nft_count == 1
        assert result.assets[0].token_type == "pNFT"

    @responses.activate
    def test_scan_handles_api_error(self, mock_alchemy_api_key, sample_solana_address):
        """
        Given a Solana scanner and an API that returns an error
        When scanning the wallet
        Then the error should be captured in the result
        """
        # Given
        client = AlchemyClient(
            mock_alchemy_api_key,
            initial_delay=0.001,
            max_retries=0,
        )
        scanner = SolanaChainScanner(client, "solana")
        url = f"https://solana-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        responses.add(
            responses.POST,
            url,
            json={"error": {"code": -32600, "message": "Invalid request"}},
            status=200,
        )

        # When
        result = scanner.scan(sample_solana_address)

        # Then
        assert result.error is not None
        assert "Invalid request" in result.error
        assert len(result.assets) == 0

    @responses.activate
    def test_scan_uses_raw_interface_for_unknown_types(
        self, mock_alchemy_api_key, sample_solana_address
    ):
        """
        Given a Solana wallet with an unknown asset interface type
        When scanning the wallet
        Then the raw interface should be used as token_type
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        scanner = SolanaChainScanner(client, "solana")
        url = f"https://solana-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "total": 1,
                    "limit": 1000,
                    "page": 1,
                    "items": [
                        {
                            "id": "UnknownAsset123",
                            "interface": "SomeUnknownInterface",
                            "content": {"metadata": {"name": "Unknown Asset"}},
                        }
                    ],
                },
            },
            status=200,
        )

        # When
        result = scanner.scan(sample_solana_address)

        # Then
        assert result.nft_count == 1
        assert result.assets[0].token_type == "SomeUnknownInterface"

    @responses.activate
    def test_scan_defaults_decimals_to_9_when_not_provided(
        self, mock_alchemy_api_key, sample_solana_address
    ):
        """
        Given a Solana token without decimals specified
        When scanning the wallet
        Then decimals should default to 9
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        scanner = SolanaChainScanner(client, "solana")
        url = f"https://solana-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"

        # Token with balance but no decimals specified
        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "total": 1,
                    "limit": 1000,
                    "page": 1,
                    "items": [
                        {
                            "id": "TokenWithoutDecimals",
                            "interface": "FungibleToken",
                            "content": {"metadata": {"name": "No Decimals Token", "symbol": "NDT"}},
                            "token_info": {"balance": 1000000000},  # No decimals field
                        }
                    ],
                },
            },
            status=200,
        )

        # When
        result = scanner.scan(sample_solana_address)

        # Then
        assert result.token_count == 1
        # 1000000000 / 10^9 = 1
        assert result.assets[0].quantity == "1"


class TestCreateScannerAllChains:
    """Tests for create_scanner with all supported chains."""

    def test_creates_evm_scanner_for_base(self, mock_alchemy_api_key):
        """
        Given an Alchemy client
        When creating a scanner for base
        Then an EVMChainScanner should be returned
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When
        scanner = create_scanner(client, "base")

        # Then
        assert isinstance(scanner, EVMChainScanner)
        assert scanner.chain == "base"

    def test_creates_evm_scanner_for_bnb(self, mock_alchemy_api_key):
        """
        Given an Alchemy client
        When creating a scanner for bnb
        Then an EVMChainScanner should be returned
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)

        # When
        scanner = create_scanner(client, "bnb")

        # Then
        assert isinstance(scanner, EVMChainScanner)
        assert scanner.chain == "bnb"


class TestEVMChainScannerEdgeCases:
    """Tests for EVMChainScanner edge cases."""

    @responses.activate
    def test_scan_excludes_native_token_when_balance_is_zero(
        self, mock_alchemy_api_key, sample_wallet_address
    ):
        """
        Given a wallet with zero native balance
        When scanning the wallet
        Then native token should not be included in results
        """
        # Given
        client = AlchemyClient(mock_alchemy_api_key)
        scanner = EVMChainScanner(client, "ethereum")
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"
        nft_url = f"https://eth-mainnet.g.alchemy.com/nft/v3/{mock_alchemy_api_key}/getNFTsForOwner"

        # Mock zero native balance
        responses.add(
            responses.POST,
            url,
            json={"jsonrpc": "2.0", "id": 1, "result": "0x0"},
            status=200,
        )

        # Mock empty token balances
        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"address": sample_wallet_address, "tokenBalances": []},
            },
            status=200,
        )

        # Mock empty NFTs
        responses.add(
            responses.GET,
            nft_url,
            json={"ownedNfts": [], "totalCount": 0},
            status=200,
        )

        # When
        result = scanner.scan(sample_wallet_address)

        # Then
        assert result.native_count == 0
        assert len(result.assets) == 0
        # Verify no NATIVE type asset exists
        native_assets = [a for a in result.assets if a.token_type == "NATIVE"]
        assert len(native_assets) == 0

    @responses.activate
    def test_scan_skips_tokens_when_metadata_fetch_fails(
        self, mock_alchemy_api_key, sample_wallet_address
    ):
        """
        Given a wallet with tokens where metadata fetch fails
        When scanning the wallet
        Then those tokens should be skipped
        """
        # Given
        client = AlchemyClient(
            mock_alchemy_api_key,
            initial_delay=0.001,
            max_retries=0,
        )
        scanner = EVMChainScanner(client, "ethereum")
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"
        nft_url = f"https://eth-mainnet.g.alchemy.com/nft/v3/{mock_alchemy_api_key}/getNFTsForOwner"

        # Mock zero native balance
        responses.add(
            responses.POST,
            url,
            json={"jsonrpc": "2.0", "id": 1, "result": "0x0"},
            status=200,
        )

        # Mock token balances with two tokens
        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "address": sample_wallet_address,
                    "tokenBalances": [
                        {"contractAddress": "0xGoodToken", "tokenBalance": "0x100"},
                        {"contractAddress": "0xBadToken", "tokenBalance": "0x200"},
                    ],
                },
            },
            status=200,
        )

        # First metadata call succeeds
        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"name": "Good Token", "symbol": "GOOD", "decimals": 18},
            },
            status=200,
        )

        # Second metadata call fails
        responses.add(
            responses.POST,
            url,
            json={"jsonrpc": "2.0", "id": 1, "error": {"message": "Token not found"}},
            status=200,
        )

        # Mock empty NFTs
        responses.add(
            responses.GET,
            nft_url,
            json={"ownedNfts": [], "totalCount": 0},
            status=200,
        )

        # When
        result = scanner.scan(sample_wallet_address)

        # Then
        assert result.token_count == 1  # Only the good token
        assert result.skipped_tokens == 1  # One token was skipped
        assert result.assets[0].symbol == "GOOD"

    @responses.activate
    def test_scan_prints_skipped_tokens_message_to_stderr(
        self, mock_alchemy_api_key, sample_wallet_address, capsys
    ):
        """
        Given a wallet with tokens where metadata fetch fails
        When scanning the wallet
        Then a message should be printed to stderr
        """
        # Given
        client = AlchemyClient(
            mock_alchemy_api_key,
            initial_delay=0.001,
            max_retries=0,
        )
        scanner = EVMChainScanner(client, "ethereum")
        url = f"https://eth-mainnet.g.alchemy.com/v2/{mock_alchemy_api_key}"
        nft_url = (
            f"https://eth-mainnet.g.alchemy.com/nft/v3/{mock_alchemy_api_key}" f"/getNFTsForOwner"
        )

        # Mock zero native balance
        responses.add(
            responses.POST,
            url,
            json={"jsonrpc": "2.0", "id": 1, "result": "0x0"},
            status=200,
        )

        # Mock token balances with one token
        responses.add(
            responses.POST,
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "address": sample_wallet_address,
                    "tokenBalances": [
                        {"contractAddress": "0xBadToken", "tokenBalance": "0x100"},
                    ],
                },
            },
            status=200,
        )

        # Metadata call fails
        responses.add(
            responses.POST,
            url,
            json={"jsonrpc": "2.0", "id": 1, "error": {"message": "Token not found"}},
            status=200,
        )

        # Mock empty NFTs
        responses.add(
            responses.GET,
            nft_url,
            json={"ownedNfts": [], "totalCount": 0},
            status=200,
        )

        # When
        scanner.scan(sample_wallet_address)

        # Then
        captured = capsys.readouterr()
        assert "[ethereum] Skipped 1 token(s)" in captured.err
        assert "metadata fetch failures" in captured.err
