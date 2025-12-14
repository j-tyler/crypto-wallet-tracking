"""
Alchemy API client with automatic rate limit handling and retry logic.

This module provides a centralized client for all Alchemy API interactions,
handling network-specific endpoints, pagination, and 429 rate limit retries.
"""

import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TypeVar

import requests


T = TypeVar("T")

# Network configuration mapping
NETWORK_ENDPOINTS = {
    "ethereum": "eth-mainnet.g.alchemy.com",
    "polygon": "polygon-mainnet.g.alchemy.com",
    "base": "base-mainnet.g.alchemy.com",
    "bnb": "bnb-mainnet.g.alchemy.com",
    "solana": "solana-mainnet.g.alchemy.com",
}

# Native token configuration for each network
NATIVE_TOKENS = {
    "ethereum": {"symbol": "ETH", "name": "Ethereum", "decimals": 18},
    "polygon": {"symbol": "MATIC", "name": "Polygon", "decimals": 18},
    "base": {"symbol": "ETH", "name": "Ethereum", "decimals": 18},
    "bnb": {"symbol": "BNB", "name": "BNB", "decimals": 18},
    "solana": {"symbol": "SOL", "name": "Solana", "decimals": 9},
}

# Retry configuration
DEFAULT_INITIAL_DELAY = 1.0  # seconds
DEFAULT_BACKOFF_MULTIPLIER = 2.0
DEFAULT_MAX_RETRIES = 5
DEFAULT_MAX_DELAY = 32.0  # seconds
DEFAULT_JITTER = 0.1  # ±10%


@dataclass
class TokenBalance:
    """Represents an ERC-20 token balance."""

    contract_address: str
    balance: str  # Hex string


@dataclass
class TokenMetadata:
    """Represents token metadata from Alchemy."""

    name: Optional[str]
    symbol: Optional[str]
    decimals: Optional[int]
    logo: Optional[str]


@dataclass
class NFT:
    """Represents an NFT (ERC-721 or ERC-1155)."""

    contract_address: str
    token_id: str
    token_type: str  # ERC721 or ERC1155
    name: Optional[str]
    collection_name: Optional[str]
    balance: str  # "1" for ERC721, can be >1 for ERC1155
    is_spam: bool


@dataclass
class SolanaAsset:
    """Represents a Solana asset from DAS API."""

    asset_id: str
    interface: str  # FungibleToken, V1_NFT, etc.
    name: Optional[str]
    symbol: Optional[str]
    balance: Optional[int]
    decimals: Optional[int]


class AlchemyAPIError(Exception):
    """Exception raised for Alchemy API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class AlchemyRateLimitError(AlchemyAPIError):
    """Exception raised when rate limit is exceeded and retries are exhausted."""

    pass


class AlchemyClient:
    """
    Centralized Alchemy API client with automatic 429 retry handling.

    All API interactions go through this class, which handles:
    - Network-specific endpoint URLs
    - HTTP 429 rate limit retries with exponential backoff
    - Request/response serialization
    - Pagination for multi-page endpoints
    """

    def __init__(
        self,
        api_key: str,
        initial_delay: float = DEFAULT_INITIAL_DELAY,
        backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_delay: float = DEFAULT_MAX_DELAY,
        jitter: float = DEFAULT_JITTER,
    ):
        """
        Initialize the Alchemy client.

        Args:
            api_key: Alchemy API key
            initial_delay: Initial delay in seconds for retry backoff
            backoff_multiplier: Multiplier for exponential backoff
            max_retries: Maximum number of retry attempts
            max_delay: Maximum delay cap in seconds
            jitter: Jitter factor (±percentage) to randomize delays
        """
        self.api_key = api_key
        self.initial_delay = initial_delay
        self.backoff_multiplier = backoff_multiplier
        self.max_retries = max_retries
        self.max_delay = max_delay
        self.jitter = jitter
        self.session = requests.Session()

    def _sanitize_error_message(self, message: str) -> str:
        """Remove API key from error messages to prevent credential leakage."""
        return message.replace(self.api_key, "[REDACTED]")

    def _get_base_url(self, network: str) -> str:
        """Get the base URL for a network."""
        if network not in NETWORK_ENDPOINTS:
            raise ValueError(f"Unsupported network: {network}")
        endpoint = NETWORK_ENDPOINTS[network]
        return f"https://{endpoint}/v2/{self.api_key}"

    def _get_nft_api_url(self, network: str) -> str:
        """Get the NFT API URL for a network."""
        if network not in NETWORK_ENDPOINTS:
            raise ValueError(f"Unsupported network: {network}")
        endpoint = NETWORK_ENDPOINTS[network]
        return f"https://{endpoint}/nft/v3/{self.api_key}"

    def _apply_jitter(self, delay: float) -> float:
        """Apply random jitter to a delay value."""
        jitter_range = delay * self.jitter
        return delay + random.uniform(-jitter_range, jitter_range)

    def _execute_with_retry(
        self,
        request_func: Callable[[], requests.Response],
    ) -> requests.Response:
        """
        Execute a request function with retry logic for rate limits and server errors.

        Args:
            request_func: A callable that returns a requests.Response

        Returns:
            The successful response

        Raises:
            AlchemyAPIError: For API errors after retries exhausted
            AlchemyRateLimitError: When rate limit retries are exhausted
        """
        delay = self.initial_delay

        for attempt in range(self.max_retries + 1):
            try:
                response = request_func()

                if response.status_code == 429:
                    if attempt < self.max_retries:
                        sleep_time = self._apply_jitter(min(delay, self.max_delay))
                        time.sleep(sleep_time)
                        delay *= self.backoff_multiplier
                        continue
                    raise AlchemyRateLimitError(
                        "Rate limit exceeded and max retries reached",
                        status_code=429,
                    )

                if response.status_code == 401:
                    raise AlchemyAPIError("Invalid API key", status_code=401)

                if response.status_code >= 500:
                    if attempt < self.max_retries:
                        sleep_time = self._apply_jitter(min(delay, self.max_delay))
                        time.sleep(sleep_time)
                        delay *= self.backoff_multiplier
                        continue
                    raise AlchemyAPIError(
                        f"Server error: {response.status_code}",
                        status_code=response.status_code,
                    )

                response.raise_for_status()
                return response

            except requests.RequestException as e:
                if attempt < self.max_retries:
                    sleep_time = self._apply_jitter(min(delay, self.max_delay))
                    time.sleep(sleep_time)
                    delay *= self.backoff_multiplier
                    continue
                sanitized_msg = self._sanitize_error_message(str(e))
                raise AlchemyAPIError(f"Request failed: {sanitized_msg}") from e

        raise AlchemyAPIError("Max retries exceeded")

    def _request(
        self,
        network: str,
        method: str,
        params: Any,
        request_id: int = 1,
    ) -> Dict[str, Any]:
        """
        Make a JSON-RPC request with automatic 429 retry and exponential backoff.

        Args:
            network: Target network (ethereum, polygon, base, bnb, solana)
            method: JSON-RPC method name
            params: Method parameters
            request_id: JSON-RPC request ID

        Returns:
            The 'result' field from the JSON-RPC response

        Raises:
            AlchemyAPIError: For API errors
            AlchemyRateLimitError: When rate limit retries are exhausted
        """
        url = self._get_base_url(network)
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id,
        }

        response = self._execute_with_retry(lambda: self.session.post(url, json=payload))
        data = response.json()

        if "error" in data:
            error = data["error"]
            raise AlchemyAPIError(
                f"API error: {error.get('message', str(error))}",
                status_code=error.get("code"),
            )

        return data.get("result", {})

    def _request_nft_api(
        self,
        network: str,
        endpoint: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Make a REST request to the NFT API with automatic retry.

        Args:
            network: Target network
            endpoint: API endpoint path (e.g., "getNFTsForOwner")
            params: Query parameters

        Returns:
            The JSON response
        """
        base_url = self._get_nft_api_url(network)
        url = f"{base_url}/{endpoint}"

        response = self._execute_with_retry(lambda: self.session.get(url, params=params))
        return response.json()

    def get_native_balance(self, network: str, wallet: str) -> int:
        """
        Get native token balance (ETH, MATIC, BNB) for an EVM wallet.

        Args:
            network: Target network (ethereum, polygon, base, bnb)
            wallet: Wallet address

        Returns:
            Balance in wei (as integer)
        """
        if network == "solana":
            raise ValueError("Use get_solana_assets for Solana native balance")

        result = self._request(network, "eth_getBalance", [wallet, "latest"])
        return int(result, 16)

    def get_token_balances(self, network: str, wallet: str) -> List[TokenBalance]:
        """
        Get all ERC-20 token balances for a wallet.

        Automatically paginates through all results.

        Args:
            network: Target network (ethereum, polygon, base, bnb)
            wallet: Wallet address

        Returns:
            List of TokenBalance objects
        """
        if network == "solana":
            raise ValueError("Use get_solana_assets for Solana tokens")

        all_balances: List[TokenBalance] = []
        page_key: Optional[str] = None

        while True:
            params: List[Any] = [wallet, "erc20"]
            if page_key:
                params.append({"pageKey": page_key})

            result = self._request(network, "alchemy_getTokenBalances", params)
            token_balances = result.get("tokenBalances", [])

            for tb in token_balances:
                # Skip tokens with zero balance
                balance = tb.get("tokenBalance", "0x0")
                if balance and balance != "0x0" and int(balance, 16) > 0:
                    all_balances.append(
                        TokenBalance(
                            contract_address=tb.get("contractAddress", ""),
                            balance=balance,
                        )
                    )

            page_key = result.get("pageKey")
            if not page_key:
                break

        return all_balances

    def get_token_metadata(self, network: str, contract: str) -> TokenMetadata:
        """
        Get metadata (name, symbol, decimals) for a token contract.

        Args:
            network: Target network (ethereum, polygon, base, bnb)
            contract: Token contract address

        Returns:
            TokenMetadata object
        """
        if network == "solana":
            raise ValueError("Use get_solana_assets for Solana token metadata")

        result = self._request(network, "alchemy_getTokenMetadata", [contract])

        return TokenMetadata(
            name=result.get("name"),
            symbol=result.get("symbol"),
            decimals=result.get("decimals"),
            logo=result.get("logo"),
        )

    def get_nfts_for_owner(self, network: str, wallet: str) -> List[NFT]:
        """
        Get all NFTs owned by a wallet.

        Automatically paginates through all results.

        Args:
            network: Target network (ethereum, polygon, base, bnb)
            wallet: Wallet address

        Returns:
            List of NFT objects
        """
        if network == "solana":
            raise ValueError("Use get_solana_assets for Solana NFTs")

        all_nfts: List[NFT] = []
        page_key: Optional[str] = None

        while True:
            params: Dict[str, Any] = {
                "owner": wallet,
                "withMetadata": "true",
                "pageSize": 100,
            }
            if page_key:
                params["pageKey"] = page_key

            result = self._request_nft_api(network, "getNFTsForOwner", params)
            owned_nfts = result.get("ownedNfts", [])

            for nft in owned_nfts:
                contract = nft.get("contract", {})
                all_nfts.append(
                    NFT(
                        contract_address=contract.get("address", ""),
                        token_id=nft.get("tokenId", ""),
                        token_type=nft.get("tokenType", contract.get("tokenType", "")),
                        name=nft.get("name"),
                        collection_name=contract.get("name"),
                        balance=nft.get("balance", "1"),
                        is_spam=nft.get("contract", {}).get("isSpam", False),
                    )
                )

            page_key = result.get("pageKey")
            if not page_key:
                break

        return all_nfts

    def get_solana_assets(self, wallet: str) -> List[SolanaAsset]:
        """
        Get all assets for a Solana wallet via DAS API.

        Automatically paginates through all results.
        Note: Spam detection is NOT available for Solana.

        Args:
            wallet: Solana wallet public key (base58)

        Returns:
            List of SolanaAsset objects
        """
        all_assets: List[SolanaAsset] = []
        page = 1
        limit = 1000

        while True:
            params = {
                "ownerAddress": wallet,
                "page": page,
                "limit": limit,
                "displayOptions": {
                    "showFungible": True,
                    "showNativeBalance": True,
                },
            }

            result = self._request("solana", "getAssetsByOwner", params)
            items = result.get("items", [])

            for item in items:
                content = item.get("content", {})
                metadata = content.get("metadata", {})
                token_info = item.get("token_info", {})

                all_assets.append(
                    SolanaAsset(
                        asset_id=item.get("id", ""),
                        interface=item.get("interface", ""),
                        name=metadata.get("name"),
                        symbol=metadata.get("symbol"),
                        balance=token_info.get("balance"),
                        decimals=token_info.get("decimals"),
                    )
                )

            # Check if we've fetched all items
            if len(items) < limit:
                break

            page += 1

        return all_assets

    def get_native_token_info(self, network: str) -> Dict[str, Any]:
        """
        Get native token info for a network.

        Args:
            network: Target network

        Returns:
            Dict with symbol, name, and decimals
        """
        if network not in NATIVE_TOKENS:
            raise ValueError(f"Unsupported network: {network}")
        return NATIVE_TOKENS[network].copy()
