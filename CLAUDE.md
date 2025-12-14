# CLAUDE.md

Instructions for Claude Code to work with this project.

## Project Overview

Python scripts for generating crypto wallet reports using the Alchemy API. Supports Ethereum, Polygon, Base, BNB Chain, and Solana.

## Environment

- **Python**: 3.11 (available at `/usr/local/bin/python3`)
- **Pip**: 24.0 (available at `/usr/bin/pip3`)
- **OS**: Linux

## Setup Commands

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (with dev tools)
pip install -e ".[dev]"

# Or install just runtime dependencies
pip install -e .
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=scripts --cov-report=term-missing

# Run specific test file
pytest tests/test_alchemy_client.py -v
```

## Linting & Formatting

```bash
# Format code
black scripts/ tests/

# Check formatting
black --check scripts/ tests/

# Run linter
flake8 scripts/ tests/

# Type checking
mypy scripts/
```

## Running Scripts

Scripts require an Alchemy API key. Example:

```bash
python scripts/show_current_wallet_assets.py \
    --api-key YOUR_ALCHEMY_API_KEY \
    --wallet 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 \
    --networks ethereum polygon
```

## Project Structure

```
crypto-wallet-tracking/
├── scripts/                    # Main CLI scripts
│   ├── show_current_wallet_assets.py
│   └── lib/                    # Shared library code
│       ├── alchemy_client.py   # Alchemy API client with retry logic
│       ├── models.py           # Data models
│       ├── formatters.py       # CSV/Excel output
│       └── validators.py       # Address validation
├── tests/                      # Test files
├── docs/                       # Documentation
│   ├── show-current-wallet-assets.md    # Script design doc
│   └── alchemy-technical-overview.md    # API reference
├── pyproject.toml              # Project config
├── requirements.txt            # Dependencies
└── Makefile                    # Dev commands
```

## Key Design Decisions

1. **Single AlchemyClient**: All API calls go through `scripts/lib/alchemy_client.py` which handles:
   - Network-specific endpoint URLs
   - HTTP 429 rate limit retries with exponential backoff
   - Request/response serialization

2. **Spam Separation**: Assets flagged as spam by Alchemy go in a separate sheet (Excel) or file (CSV).

3. **No Pre-emptive Rate Limiting**: Instead of throttling requests upfront, the client reacts to 429 responses and backs off automatically.

## Supported Networks

| Network | Endpoint Pattern |
|---------|-----------------|
| Ethereum | `eth-mainnet.g.alchemy.com` |
| Polygon | `polygon-mainnet.g.alchemy.com` |
| Base | `base-mainnet.g.alchemy.com` |
| BNB | `bnb-mainnet.g.alchemy.com` |
| Solana | `solana-mainnet.g.alchemy.com` |

## Testing Notes

- Use `responses` library to mock HTTP requests
- Test 429 retry behavior with mock responses
- Test data parsing for each network type separately
