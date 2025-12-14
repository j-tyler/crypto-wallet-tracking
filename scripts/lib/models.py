"""
Data models for crypto wallet tracking.

This module defines the unified Asset model used for CSV output
and other data structures for wallet scanning operations.
"""

from dataclasses import dataclass
from typing import List, Optional


# CSV column order for output
CSV_COLUMNS = [
    "chain",
    "asset_name",
    "symbol",
    "asset_address",
    "quantity",
    "token_type",
    "token_id",
    "collection_name",
]


@dataclass
class Asset:
    """
    Unified asset model for CSV output.

    This model represents any type of asset across all supported chains:
    native tokens, ERC-20/SPL tokens, and NFTs (ERC-721/ERC-1155/Metaplex).
    """

    chain: str
    asset_name: str  # Empty string if unavailable
    symbol: str  # Empty string if unavailable
    asset_address: str  # "NATIVE" for native tokens, contract/mint address otherwise
    quantity: str  # Full precision, trailing zeros trimmed. "1" for ERC721
    token_type: str  # NATIVE, ERC20, ERC721, ERC1155, SPL, NFT (Solana)
    token_id: Optional[str] = None  # For NFTs only
    collection_name: Optional[str] = None  # For NFTs only
    is_spam: bool = False  # Always False for Solana (not supported)

    def to_csv_row(self) -> List[str]:
        """Convert asset to a CSV row (list of strings)."""
        return [
            self.chain,
            self.asset_name,
            self.symbol,
            self.asset_address,
            self.quantity,
            self.token_type,
            self.token_id or "",
            self.collection_name or "",
        ]


@dataclass
class ScanResult:
    """
    Result of scanning a single chain for assets.

    Separates assets into main (non-spam) and spam lists.
    """

    chain: str
    assets: List[Asset]
    spam_assets: List[Asset]
    native_count: int = 0
    token_count: int = 0
    nft_count: int = 0
    erc721_count: int = 0
    erc1155_count: int = 0
    spam_count: int = 0
    skipped_tokens: int = 0  # Tokens skipped due to metadata fetch failures
    error: Optional[str] = None  # Error message if scan failed
