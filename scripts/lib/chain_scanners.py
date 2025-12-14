"""
Chain scanner classes for fetching wallet assets across different blockchains.

This module provides chain-specific scanners that use the AlchemyClient to fetch
assets and convert them to the unified Asset model for CSV output.
"""

import sys
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List

from .alchemy_client import AlchemyClient, AlchemyAPIError, NATIVE_TOKENS
from .models import Asset, ScanResult

# Wrapped SOL mint address (native SOL representation in DAS API)
WRAPPED_SOL_MINT = "So11111111111111111111111111111111111111112"


def format_quantity(raw_balance: int, decimals: int) -> str:
    """
    Format balance with full precision, trimming trailing zeros.

    Args:
        raw_balance: Raw balance value (in smallest unit)
        decimals: Number of decimal places

    Returns:
        Formatted balance string with trailing zeros trimmed

    Examples:
        format_quantity(1000000, 6) -> "1"
        format_quantity(1500000, 6) -> "1.5"
        format_quantity(1234567890123456789, 18) -> "1.234567890123456789"
    """
    if raw_balance == 0:
        return "0"

    if decimals == 0:
        return str(raw_balance)

    # Use Decimal for precise arithmetic
    balance = Decimal(raw_balance) / Decimal(10**decimals)

    # Format with full precision and strip trailing zeros
    formatted = format(balance, "f")

    # Remove trailing zeros after decimal point
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")

    return formatted


class BaseChainScanner(ABC):
    """
    Abstract base class for chain scanners.

    Provides common functionality and defines the interface that all
    chain-specific scanners must implement.
    """

    def __init__(self, client: AlchemyClient, chain: str):
        """
        Initialize the scanner.

        Args:
            client: AlchemyClient instance for API calls
            chain: Chain identifier (ethereum, polygon, base, bnb, solana)
        """
        self.client = client
        self.chain = chain

    @abstractmethod
    def scan(self, wallet: str) -> ScanResult:
        """
        Scan a wallet for all assets on this chain.

        Args:
            wallet: Wallet address to scan

        Returns:
            ScanResult containing all assets found
        """
        pass

    def _create_native_asset(self, balance: int, decimals: int, symbol: str, name: str) -> Asset:
        """
        Create an Asset for a native token balance.

        Args:
            balance: Raw balance in smallest unit
            decimals: Token decimals
            symbol: Token symbol (e.g., ETH, MATIC)
            name: Token name

        Returns:
            Asset representing the native token
        """
        return Asset(
            chain=self.chain,
            asset_name=name,
            symbol=symbol,
            asset_address="NATIVE",
            quantity=format_quantity(balance, decimals),
            token_type="NATIVE",
            is_spam=False,
        )


class EVMChainScanner(BaseChainScanner):
    """
    Scanner for EVM-compatible chains (Ethereum, Polygon, Base, BNB).

    Fetches native token balance, ERC-20 tokens, and NFTs (ERC-721/ERC-1155).
    """

    def scan(self, wallet: str) -> ScanResult:
        """
        Scan an EVM wallet for all assets.

        Args:
            wallet: Ethereum-style wallet address (0x...)

        Returns:
            ScanResult with all assets and spam separation
        """
        assets: List[Asset] = []
        spam_assets: List[Asset] = []
        native_count = 0
        token_count = 0
        nft_count = 0
        erc721_count = 0
        erc1155_count = 0

        try:
            # Get native token balance
            native_balance = self.client.get_native_balance(self.chain, wallet)
            if native_balance > 0:
                native_info = NATIVE_TOKENS[self.chain]
                native_asset = self._create_native_asset(
                    balance=native_balance,
                    decimals=native_info["decimals"],
                    symbol=native_info["symbol"],
                    name=native_info["name"],
                )
                assets.append(native_asset)
                native_count = 1

            # Get ERC-20 token balances
            token_balances = self.client.get_token_balances(self.chain, wallet)
            skipped_tokens = 0
            for tb in token_balances:
                try:
                    metadata = self.client.get_token_metadata(self.chain, tb.contract_address)
                    balance_int = int(tb.balance, 16)
                    decimals = metadata.decimals or 18

                    token_asset = Asset(
                        chain=self.chain,
                        asset_name=metadata.name or "",
                        symbol=metadata.symbol or "",
                        asset_address=tb.contract_address,
                        quantity=format_quantity(balance_int, decimals),
                        token_type="ERC20",
                        is_spam=False,
                    )
                    assets.append(token_asset)
                    token_count += 1
                except AlchemyAPIError:
                    # Skip tokens where we can't get metadata
                    skipped_tokens += 1
                    continue

            if skipped_tokens > 0:
                print(
                    f"[{self.chain}] Skipped {skipped_tokens} token(s) "
                    f"due to metadata fetch failures",
                    file=sys.stderr,
                )

            # Get NFTs
            nfts = self.client.get_nfts_for_owner(self.chain, wallet)
            for nft in nfts:
                nft_asset = Asset(
                    chain=self.chain,
                    asset_name=nft.name or "",
                    symbol="",
                    asset_address=nft.contract_address,
                    quantity=nft.balance,
                    token_type=nft.token_type,
                    token_id=nft.token_id,
                    collection_name=nft.collection_name,
                    is_spam=nft.is_spam,
                )

                if nft.is_spam:
                    spam_assets.append(nft_asset)
                else:
                    assets.append(nft_asset)
                    nft_count += 1
                    if nft.token_type == "ERC721":
                        erc721_count += 1
                    elif nft.token_type == "ERC1155":
                        erc1155_count += 1

            return ScanResult(
                chain=self.chain,
                assets=assets,
                spam_assets=spam_assets,
                native_count=native_count,
                token_count=token_count,
                nft_count=nft_count,
                erc721_count=erc721_count,
                erc1155_count=erc1155_count,
                spam_count=len(spam_assets),
                skipped_tokens=skipped_tokens,
            )

        except AlchemyAPIError as e:
            return ScanResult(
                chain=self.chain,
                assets=[],
                spam_assets=[],
                error=str(e),
            )


class SolanaChainScanner(BaseChainScanner):
    """
    Scanner for Solana blockchain using the DAS API.

    Fetches native SOL balance, SPL tokens, and NFTs.
    Note: Spam detection is NOT available for Solana.
    """

    # Solana asset interface to token type mapping
    INTERFACE_TO_TOKEN_TYPE = {
        "FungibleToken": "SPL",
        "FungibleAsset": "SPL",
        "V1_NFT": "NFT",
        "V2_NFT": "NFT",
        "ProgrammableNFT": "pNFT",
        "MplCoreAsset": "MPL",
    }

    def scan(self, wallet: str) -> ScanResult:
        """
        Scan a Solana wallet for all assets.

        Args:
            wallet: Solana wallet public key (base58)

        Returns:
            ScanResult with all assets (spam_assets always empty for Solana)
        """
        assets: List[Asset] = []
        native_count = 0
        token_count = 0
        nft_count = 0

        try:
            # Get all assets via DAS API
            solana_assets = self.client.get_solana_assets(wallet)

            for sa in solana_assets:
                token_type = self.INTERFACE_TO_TOKEN_TYPE.get(sa.interface, sa.interface)

                # Determine if this is a fungible token or NFT
                is_fungible = sa.interface in ("FungibleToken", "FungibleAsset")

                if is_fungible and sa.balance is not None:
                    # Handle fungible tokens (including native SOL)
                    decimals = sa.decimals or 9  # Default to 9 for SOL
                    quantity = format_quantity(sa.balance, decimals)

                    # Check if this is native SOL (special handling)
                    if sa.symbol == "SOL" and sa.asset_id == WRAPPED_SOL_MINT:
                        asset = Asset(
                            chain=self.chain,
                            asset_name=sa.name or "Solana",
                            symbol="SOL",
                            asset_address="NATIVE",
                            quantity=quantity,
                            token_type="NATIVE",
                            is_spam=False,
                        )
                        native_count = 1
                    else:
                        asset = Asset(
                            chain=self.chain,
                            asset_name=sa.name or "",
                            symbol=sa.symbol or "",
                            asset_address=sa.asset_id,
                            quantity=quantity,
                            token_type=token_type,
                            is_spam=False,
                        )
                        token_count += 1

                    assets.append(asset)
                else:
                    # Handle NFTs
                    asset = Asset(
                        chain=self.chain,
                        asset_name=sa.name or "",
                        symbol=sa.symbol or "",
                        asset_address=sa.asset_id,
                        quantity="1",
                        token_type=token_type,
                        token_id=sa.asset_id,  # For Solana NFTs, mint address is the ID
                        collection_name=None,  # Could be enhanced with collection lookup
                        is_spam=False,  # Spam detection not available for Solana
                    )
                    assets.append(asset)
                    nft_count += 1

            return ScanResult(
                chain=self.chain,
                assets=assets,
                spam_assets=[],  # Spam detection not available for Solana
                native_count=native_count,
                token_count=token_count,
                nft_count=nft_count,
            )

        except AlchemyAPIError as e:
            return ScanResult(
                chain=self.chain,
                assets=[],
                spam_assets=[],
                error=str(e),
            )


def create_scanner(client: AlchemyClient, chain: str) -> BaseChainScanner:
    """
    Factory function to create the appropriate scanner for a chain.

    Args:
        client: AlchemyClient instance
        chain: Chain identifier

    Returns:
        Appropriate scanner instance for the chain

    Raises:
        ValueError: If chain is not supported
    """
    if chain in ("ethereum", "polygon", "base", "bnb"):
        return EVMChainScanner(client, chain)
    elif chain == "solana":
        return SolanaChainScanner(client, chain)
    else:
        raise ValueError(f"Unsupported chain: {chain}")
