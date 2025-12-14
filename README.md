# Crypto Wallet Tracking

A Python CLI tool for generating crypto wallet asset reports across multiple blockchain networks using the Alchemy API. Query any wallet address and export holdings to CSV format.

## Supported Networks

| Network | Native Token | Features |
|---------|--------------|----------|
| Ethereum | ETH | ERC-20, ERC-721, ERC-1155, spam detection |
| Polygon | MATIC | ERC-20, ERC-721, ERC-1155, spam detection |
| Base | ETH | ERC-20, ERC-721, ERC-1155, spam detection |
| BNB Chain | BNB | ERC-20, ERC-721, ERC-1155, spam detection |
| Solana | SOL | SPL tokens, Metaplex NFTs |

## Sample CSV Output

When you run the tool, you get a CSV file with the following structure:

```csv
chain,asset_name,symbol,asset_address,quantity,token_type,token_id,collection_name
ethereum,Ethereum,ETH,NATIVE,2.5,NATIVE,,
ethereum,USD Coin,USDC,0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48,1500.75,ERC20,,
ethereum,Tether USD,USDT,0xdac17f958d2ee523a2206206994597c13d831ec7,250,ERC20,,
ethereum,Bored Ape #4523,,0xbc4ca0eda7647a8ab7c2061c2e2ad29f71cc8374,1,ERC721,4523,Bored Ape Yacht Club
polygon,Polygon,MATIC,NATIVE,10000,NATIVE,,
polygon,Wrapped Ether,WETH,0x7ceb23fd6bc0add59e62ac25578270cff1b9f619,0.5,ERC20,,
base,Ethereum,ETH,NATIVE,1.25,NATIVE,,
solana,Solana,SOL,NATIVE,50,NATIVE,,
solana,USD Coin,USDC,EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v,500,SPL,,
```

**Column Descriptions:**

| Column | Description |
|--------|-------------|
| `chain` | Blockchain network (ethereum, polygon, base, bnb, solana) |
| `asset_name` | Human-readable asset name |
| `symbol` | Token ticker symbol |
| `asset_address` | Contract address or "NATIVE" for native tokens |
| `quantity` | Amount held |
| `token_type` | NATIVE, ERC20, ERC721, ERC1155, SPL, or NFT |
| `token_id` | Token ID (NFTs only) |
| `collection_name` | NFT collection name (NFTs only) |

**Output Files:**
- Main assets: `wallet_report_20241214_153022.csv`
- Spam assets (separate file): `wallet_report_20241214_153022_spam.csv`

---

## Getting an Alchemy API Key

1. **Create an Alchemy account**
   - Go to [https://www.alchemy.com/](https://www.alchemy.com/)
   - Click "Get started for free" and sign up

2. **Create an app**
   - From the dashboard, click "Create new app"
   - Select the networks you need (Ethereum, Polygon, Base, etc.)
   - Give your app a name

3. **Copy your API key**
   - Go to your app's dashboard
   - Click "API Key" to reveal your key
   - Copy the key (it looks like: `a1B2c3D4e5F6g7H8i9J0...`)

4. **Free tier limits**
   - Free tier includes 300M compute units/month
   - Sufficient for most personal wallet tracking needs
   - Rate limits are handled automatically with retry logic

---

## Installation

### Prerequisites

- Python 3.9 or higher
- Git

### Clone the Repository

```bash
git clone https://github.com/j-tyler/crypto-wallet-tracking.git
cd crypto-wallet-tracking
```

### Setup Instructions by Operating System

#### Linux

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -e .

# Verify installation
show-current-wallet-assets --help
```

#### macOS

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -e .

# Verify installation
show-current-wallet-assets --help
```

#### Windows (Command Prompt)

```cmd
:: Create virtual environment
python -m venv venv

:: Activate virtual environment
venv\Scripts\activate.bat

:: Install dependencies
pip install -e .

:: Verify installation
show-current-wallet-assets --help
```

#### Windows (PowerShell)

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -e .

# Verify installation
show-current-wallet-assets --help
```

> **Note for PowerShell users:** If you get an execution policy error, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

---

## Usage

### Basic Command

```bash
show-current-wallet-assets \
    --api-key YOUR_ALCHEMY_API_KEY \
    --wallet WALLET_ADDRESS \
    --networks NETWORK1 NETWORK2 ...
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--api-key` | Yes | Your Alchemy API key |
| `--wallet` | Yes | Wallet address to query |
| `--networks` | Yes | Space-separated list: `ethereum`, `polygon`, `base`, `bnb`, `solana` |
| `--output` | No | Output file path (omit to print to stdout) |

### Examples

**Query a single network (output to terminal):**

```bash
show-current-wallet-assets \
    --api-key abc123xyz \
    --wallet 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 \
    --networks ethereum
```

**Query multiple networks and save to file:**

```bash
show-current-wallet-assets \
    --api-key abc123xyz \
    --wallet 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 \
    --networks ethereum polygon base \
    --output my_wallet.csv
```

This creates:
- `my_wallet_20241214_153022.csv` (main assets)
- `my_wallet_20241214_153022_spam.csv` (spam assets, if any)

**Query all supported networks:**

```bash
show-current-wallet-assets \
    --api-key abc123xyz \
    --wallet 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 \
    --networks ethereum polygon base bnb solana \
    --output full_report.csv
```

**Query a Solana wallet:**

```bash
show-current-wallet-assets \
    --api-key abc123xyz \
    --wallet 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU \
    --networks solana \
    --output solana_wallet.csv
```

### Using Environment Variables

To avoid passing your API key on every command:

**Linux/macOS:**
```bash
export ALCHEMY_API_KEY="your_api_key_here"

# Then run without --api-key
show-current-wallet-assets \
    --api-key $ALCHEMY_API_KEY \
    --wallet 0x... \
    --networks ethereum
```

**Windows (Command Prompt):**
```cmd
set ALCHEMY_API_KEY=your_api_key_here

show-current-wallet-assets ^
    --api-key %ALCHEMY_API_KEY% ^
    --wallet 0x... ^
    --networks ethereum
```

**Windows (PowerShell):**
```powershell
$env:ALCHEMY_API_KEY = "your_api_key_here"

show-current-wallet-assets `
    --api-key $env:ALCHEMY_API_KEY `
    --wallet 0x... `
    --networks ethereum
```

---

## Running Directly with Python

If you prefer not to install the package, you can run the script directly:

```bash
python scripts/show_current_wallet_assets.py \
    --api-key YOUR_API_KEY \
    --wallet 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 \
    --networks ethereum polygon
```

---

## Development Setup

For contributors who want to run tests and linting:

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=scripts --cov-report=term-missing

# Format code
black scripts/ tests/

# Run linter
flake8 scripts/ tests/

# Type checking
mypy scripts/
```

---

## Troubleshooting

### "Invalid API key" error
- Verify your API key is correct
- Ensure the API key has access to the networks you're querying

### Rate limit errors (HTTP 429)
- The tool automatically retries with exponential backoff
- If persistent, wait a few minutes and try again
- Consider upgrading your Alchemy plan for higher limits

### Network timeout errors
- Check your internet connection
- The tool retries failed requests up to 5 times automatically

### "Module not found" error
- Ensure your virtual environment is activated
- Run `pip install -e .` again

### PowerShell script execution error
- Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

## Documentation

For detailed technical documentation, see:
- [Script Design Document](docs/show-current-wallet-assets.md) - Functional requirements and architecture
- [Alchemy API Reference](docs/alchemy-technical-overview.md) - API endpoints and rate limits

---

## License

MIT License - see LICENSE file for details.
