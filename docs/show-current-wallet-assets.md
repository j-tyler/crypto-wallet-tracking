# show-current-wallet-assets.py

## Overview

A CLI script that queries a crypto wallet's holdings across multiple blockchain networks and generates a CSV report of all native tokens, fungible tokens, and NFTs (ERC-721/ERC-1155).

## Functional Requirements

### Input
- Wallet address
- Target network(s) to search
- Alchemy API key

### Output
CSV/Excel file with timestamp in filename: `{name}_{YYYYMMDD_HHMMSS}.csv`

**Main File (assets)**
| Column | Description |
|--------|-------------|
| chain | The blockchain network (ethereum, polygon, base, bnb, solana) |
| asset_name | Human-readable name of the asset (empty if unavailable) |
| symbol | Token symbol (e.g., USDC, ETH) - empty if unavailable |
| asset_address | Contract address (or mint address for Solana). "NATIVE" for native tokens |
| quantity | Amount held (full precision, trailing zeros trimmed). "1" for ERC-721 |
| token_type | Asset type: NATIVE, ERC20, ERC721, ERC1155, SPL, Metaplex, etc. |
| token_id | Token ID (for NFTs only, empty for fungible tokens) |
| collection_name | NFT collection name (for NFTs only, empty otherwise) |

**Spam File ({name}_{timestamp}_spam.csv)**
Same columns as main file, but contains assets flagged as spam by Alchemy.

Note: Spam detection is only available for EVM chains (Ethereum, Polygon, Base, BNB). Solana assets are never marked as spam.

### Native Token Support
The script includes native token balances for each queried network:
- Ethereum: ETH
- Polygon: MATIC
- Base: ETH
- BNB Chain: BNB
- Solana: SOL

### Supported Networks
- Ethereum (mainnet)
- Polygon (mainnet)
- Base (mainnet)
- BNB Chain (mainnet)
- Solana (mainnet)

## Technical Requirements

### CLI Interface

```bash
python scripts/show_current_wallet_assets.py \
    --api-key <ALCHEMY_API_KEY> \
    --wallet <WALLET_ADDRESS> \
    --networks <NETWORK1> [NETWORK2 ...] \
    [--output <OUTPUT_FILE>]
```

#### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--api-key` | Yes | - | Alchemy API key |
| `--wallet` | Yes | - | Wallet address to query |
| `--networks` | Yes | - | Space-separated list of networks |
| `--output` | No | stdout | Output file path (timestamp auto-appended) |

#### Output File Naming
When `--output` is provided:
- Main assets: `{name}_{YYYYMMDD_HHMMSS}.csv` or `.xlsx`
- Spam assets: `{name}_{YYYYMMDD_HHMMSS}_spam.csv`

Example: `--output wallet_report.csv` produces:
- `wallet_report_20241214_153022.csv`
- `wallet_report_20241214_153022_spam.csv`

#### Example Usage

```bash
# Query Ethereum and Polygon, output to stdout (main assets only)
python scripts/show_current_wallet_assets.py \
    --api-key abc123 \
    --wallet 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 \
    --networks ethereum polygon

# Query all networks, save to file
python scripts/show_current_wallet_assets.py \
    --api-key abc123 \
    --wallet 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 \
    --networks ethereum polygon base bnb solana \
    --output wallet_report.csv
```

### Console Output

The script outputs progress information to stdout:

```
[ethereum] Starting wallet scan...
[ethereum] Found 1 native token (ETH)
[ethereum] Found 15 ERC-20 tokens
[ethereum] Found 42 NFTs (38 ERC-721, 4 ERC-1155)
[ethereum] 3 assets marked as spam
[polygon] Starting wallet scan...
[polygon] Found 1 native token (MATIC)
[polygon] Found 8 ERC-20 tokens
[polygon] Found 127 NFTs (127 ERC-721, 0 ERC-1155)
[polygon] 12 assets marked as spam
[solana] Starting wallet scan...
[solana] Found 1 native token (SOL)
[solana] Found 5 SPL tokens
[solana] Found 23 NFTs
[solana] Spam detection not available for Solana

Results written to: wallet_report_20241214_153022.csv
Spam assets written to: wallet_report_20241214_153022_spam.csv
```

If a network fails:
```
[bnb] Starting wallet scan...
[bnb] ERROR: API request failed: 503 Service Unavailable. Skipping network.
```

### Rate Limiting & Retry Strategy

Rate limiting is handled internally by the `AlchemyClient` class:

- **No external rate limiter**: The client does not pre-emptively throttle requests
- **429 Handling**: When a 429 (Too Many Requests) response is received, the client automatically retries with exponential backoff
- **Backoff Strategy**:
  - Initial delay: 1 second
  - Multiplier: 2x per retry
  - Maximum retries: 5
  - Maximum delay: 32 seconds
  - Jitter: ±10% randomization to prevent thundering herd

### Pagination Strategy

Each API has different pagination limits. The client automatically paginates through all results:

| API | Max Page Size | Pagination Method |
|-----|---------------|-------------------|
| `getNFTsForOwner` | 100 | `pageKey` cursor |
| `alchemy_getTokenBalances` | 100 | `page` parameter |
| `getAssetsByOwner` (Solana) | 1000 | `page` parameter |

### API Endpoints Used

#### EVM Chains (Ethereum, Polygon, Base, BNB)

1. **Native Balance**: `eth_getBalance`
   - Returns native token balance (ETH, MATIC, BNB)

2. **Token Balances**: `alchemy_getTokenBalances`
   - Returns all ERC-20 token balances for a wallet
   - Use `"erc20"` parameter to get all tokens
   - Paginate through results

3. **Token Metadata**: `alchemy_getTokenMetadata`
   - Returns token name, symbol, decimals, logo
   - Called for each token to get human-readable info

4. **NFT Endpoints**: `getNFTsForOwner`
   - Returns all NFTs (ERC-721 and ERC-1155) owned by a wallet
   - Includes spam classification, collection info, token type
   - Paginate using `pageKey` until exhausted

#### Solana

1. **DAS API**: `getAssetsByOwner`
   - Returns all assets (native SOL, fungible tokens, and NFTs) for a wallet
   - Single unified endpoint for all Solana assets
   - Use `displayOptions.showFungible: true` and `displayOptions.showNativeBalance: true`
   - Paginate through all pages
   - Note: Spam detection NOT available for Solana

### Network Configuration

| Network | Alchemy Base URL |
|---------|------------------|
| Ethereum | `https://eth-mainnet.g.alchemy.com/v2/{api_key}` |
| Polygon | `https://polygon-mainnet.g.alchemy.com/v2/{api_key}` |
| Base | `https://base-mainnet.g.alchemy.com/v2/{api_key}` |
| BNB | `https://bnb-mainnet.g.alchemy.com/v2/{api_key}` |
| Solana | `https://solana-mainnet.g.alchemy.com/v2/{api_key}` |

## Architecture

### Module Structure

```
scripts/
├── show_current_wallet_assets.py    # Main CLI entry point
└── lib/
    ├── __init__.py
    ├── alchemy_client.py            # Single Alchemy API client with retry logic
    ├── models.py                    # Data models (Asset, TokenBalance, NFT)
    ├── formatters.py                # CSV/Excel output formatting
    └── validators.py                # Wallet address validation
```

### Data Flow

```
1. Parse CLI arguments
2. Initialize AlchemyClient (handles all API calls + retries)
3. For each requested network:
   a. Log "[network] Starting wallet scan..."
   b. Query native token balance
   c. Query token balances (paginate through all)
   d. Query NFT holdings (paginate through all)
   e. Log counts by type
   f. If error occurs, log and continue to next network
4. Separate assets into main and spam lists
5. Generate timestamp for filenames
6. Format as CSV/Excel
7. Output to file(s) or stdout
```

### Key Classes/Functions

```python
# scripts/lib/alchemy_client.py

class AlchemyClient:
    """
    Centralized Alchemy API client with automatic 429 retry handling.
    All API interactions go through this class.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()

    def _request(self, network: str, method: str, params: dict) -> dict:
        """
        Make an API request with automatic 429 retry and exponential backoff.
        """
        ...

    def get_native_balance(self, network: str, wallet: str) -> Asset:
        """Get native token balance (ETH, MATIC, BNB, SOL)."""
        ...

    def get_token_balances(self, network: str, wallet: str) -> List[TokenBalance]:
        """Get all ERC-20 token balances for a wallet. Paginates automatically."""
        ...

    def get_token_metadata(self, network: str, contract: str) -> TokenMetadata:
        """Get metadata (name, symbol, decimals) for a token contract."""
        ...

    def get_nfts_for_owner(self, network: str, wallet: str) -> List[NFT]:
        """Get all NFTs owned by a wallet. Paginates automatically."""
        ...

    def get_solana_assets(self, wallet: str) -> List[Asset]:
        """Get all assets for a Solana wallet via DAS API. Paginates automatically."""
        ...
```

```python
# scripts/lib/models.py

@dataclass
class Asset:
    """Unified asset model for CSV output."""
    chain: str
    asset_name: str                  # Empty string if unavailable
    symbol: str                      # Empty string if unavailable
    asset_address: str               # "NATIVE" for native tokens
    quantity: str                    # Full precision, trailing zeros trimmed. "1" for ERC721
    token_type: str                  # NATIVE, ERC20, ERC721, ERC1155, SPL, Metaplex
    token_id: Optional[str]          # None for fungible tokens
    collection_name: Optional[str]   # None for fungible tokens
    is_spam: bool                    # Always False for Solana (not supported)
```

```python
# scripts/lib/formatters.py

def generate_filename(base_path: str) -> Tuple[str, str]:
    """
    Generate timestamped filenames.

    Args:
        base_path: e.g., "wallet_report.csv"

    Returns:
        Tuple of (main_file, spam_file)
        e.g., ("wallet_report_20241214_153022.csv", "wallet_report_20241214_153022_spam.csv")
    """
    ...

def write_csv(assets: List[Asset], spam_assets: List[Asset], output_path: str) -> Tuple[str, str]:
    """
    Write assets to CSV or Excel file with timestamp.

    Returns:
        Tuple of (main_file_path, spam_file_path)
    """
    ...

def format_quantity(raw_balance: int, decimals: int) -> str:
    """
    Format balance with full precision, trimming trailing zeros.

    Examples:
        format_quantity(1000000, 6) -> "1"
        format_quantity(1500000, 6) -> "1.5"
        format_quantity(1234567890123456789, 18) -> "1.234567890123456789"
    """
    ...
```

### Data Models

```python
# CSV Column Mapping
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
```

## Error Handling

| Error Type | Handling |
|------------|----------|
| Invalid API key | Exit with error message |
| Network timeout | Retry with exponential backoff (max 5 attempts) |
| Rate limit (429) | Automatic retry with backoff (handled by AlchemyClient) |
| API error (4xx/5xx) | Log error to stdout, skip network, continue with others |
| Empty results | Output CSV with headers only |
| Network failure | Log "[network] ERROR: {message}. Skipping network." and continue |

## Testing Strategy

### Unit Tests
- CLI argument parsing
- CSV/Excel formatting with timestamps
- Data model conversions
- Spam filtering logic
- Quantity formatting (precision, trailing zeros)

### Integration Tests (with mocked API)
- Full workflow for each network type
- 429 retry behavior
- Pagination handling
- Error handling and continuation
- Native token balance retrieval

### Test Files
```
tests/
├── test_cli.py
├── test_alchemy_client.py
├── test_formatters.py
├── test_models.py
└── test_validators.py
```

## Dependencies

```
requests>=2.31.0      # HTTP client
openpyxl>=3.1.0       # Excel file support
```

## Future Enhancements

- Support for testnets
- Historical balance queries
- Token price lookups (USD values)
- JSON output format
- Caching for metadata queries
- Progress bar for large wallets
- ENS name resolution for wallet addresses
