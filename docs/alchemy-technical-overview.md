# Alchemy API Technical Overview

## Overview

Alchemy provides a unified blockchain development platform with APIs for accessing on-chain data across 80+ supported networks. This document focuses on the APIs relevant to the crypto-wallet-tracking project.

## API Categories

### 1. Token API (EVM Chains)
Query token balances and metadata for ERC-20 tokens.

### 2. NFT API (EVM Chains)
Query NFT ownership and metadata for ERC-721 and ERC-1155 tokens.

### 3. DAS API (Solana)
Digital Asset Standard API for querying Solana assets (both fungible and non-fungible).

---

## Rate Limiting Model

**Important**: Alchemy does NOT use simple "requests per second" rate limiting. Instead, they use **Compute Units (CU)**.

### Compute Units (CU)
- Each API method has a CU cost
- Simple requests (e.g., `eth_blockNumber`): ~10 CU
- Complex requests (e.g., `getNFTsForOwner`): ~26-480 CU
- Token balance queries: ~26 CU
- DAS API methods: 160-480 CU

### Throughput Limits (CU/s)

| Plan | CU/s Limit | Approximate RPS |
|------|------------|-----------------|
| Free | 500 CU/s | ~5-20 RPS (depends on method) |
| Pay-as-you-go | 10,000 CU/s | ~100-400 RPS |
| Enterprise | 20,000+ CU/s | Custom |

### Rate Limit Behavior
- Uses 10-second rolling window with token bucket algorithm
- Free tier: Can burst up to 5,000 CU over 10 seconds
- Exceeding limit returns HTTP 429 (Too Many Requests)

---

## EVM Chain APIs

### Supported Networks
- **Ethereum** (Mainnet, Sepolia, Holesky)
- **Polygon** (Mainnet, Amoy)
- **Base** (Mainnet, Sepolia)
- **BNB Chain** (Mainnet)
- **Arbitrum** (Mainnet, Sepolia)
- **Optimism** (Mainnet, Sepolia)

### Base URLs

```
Ethereum:  https://eth-mainnet.g.alchemy.com/v2/{API_KEY}
Polygon:   https://polygon-mainnet.g.alchemy.com/v2/{API_KEY}
Base:      https://base-mainnet.g.alchemy.com/v2/{API_KEY}
BNB:       https://bnb-mainnet.g.alchemy.com/v2/{API_KEY}
```

---

## Native Token Balance

### eth_getBalance

Retrieves native token balance (ETH, MATIC, BNB) for a wallet address.

**Method**: `eth_getBalance`
**CU Cost**: ~10 CU

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "eth_getBalance",
  "params": ["0xWALLET_ADDRESS", "latest"],
  "id": 1
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": "0x1234567890abcdef"
}
```

**Notes**:
- Returns balance in hex format (wei)
- Native token decimals are always 18
- Use "latest" for current balance

---

## Token API Endpoints

### alchemy_getTokenBalances

Retrieves all ERC-20 token balances for a wallet address.

**Method**: `alchemy_getTokenBalances`
**CU Cost**: ~26 CU

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "alchemy_getTokenBalances",
  "params": [
    "0xWALLET_ADDRESS",
    "erc20"
  ],
  "id": 1
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "address": "0xWALLET_ADDRESS",
    "tokenBalances": [
      {
        "contractAddress": "0xTOKEN_CONTRACT",
        "tokenBalance": "0x1234567890abcdef"
      }
    ],
    "pageKey": "..."
  }
}
```

**Pagination**:
- Default page size: 100
- Use `pageKey` from response to fetch next page
- Continue until `pageKey` is absent or null

**Notes**:
- Returns balances in hex format (wei)
- Does not include token metadata (name, symbol, decimals)
- Requires separate `getTokenMetadata` call for each token

---

### alchemy_getTokenMetadata

Retrieves metadata for a specific token contract.

**Method**: `alchemy_getTokenMetadata`
**CU Cost**: ~10 CU

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "alchemy_getTokenMetadata",
  "params": ["0xTOKEN_CONTRACT"],
  "id": 1
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "name": "USD Coin",
    "symbol": "USDC",
    "decimals": 6,
    "logo": "https://..."
  }
}
```

---

## NFT API Endpoints

### getNFTsForOwner (v3)

Retrieves all NFTs owned by a wallet address.

**Endpoint**: `GET /nft/v3/{API_KEY}/getNFTsForOwner`
**CU Cost**: ~26 CU

**Supported Chains**: Ethereum, Polygon, Base, BNB, Arbitrum, Optimism, and 30+ others

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| owner | string | Yes | Wallet address |
| pageSize | int | No | Results per page (default: 100, max: 100) |
| pageKey | string | No | Pagination cursor |
| withMetadata | bool | No | Include NFT metadata (default: true) |
| excludeFilters | array | No | Exclude spam, airdrops |

**Response**:
```json
{
  "ownedNfts": [
    {
      "contract": {
        "address": "0xCONTRACT",
        "name": "Collection Name",
        "symbol": "SYM",
        "tokenType": "ERC721"
      },
      "tokenId": "1234",
      "tokenType": "ERC721",
      "name": "NFT Name",
      "description": "...",
      "image": {
        "cachedUrl": "https://...",
        "thumbnailUrl": "https://..."
      },
      "balance": "1",
      "timeLastUpdated": "2024-01-01T00:00:00.000Z"
    }
  ],
  "totalCount": 100,
  "pageKey": "..."
}
```

**Pagination**:
- Max page size: 100
- Use `pageKey` cursor from response
- Continue until `pageKey` is absent or null
- Note: `pageKey` expires after 10 minutes

**Key Fields**:
- `tokenType`: "ERC721" or "ERC1155"
- `balance`: Always "1" for ERC721, can be >1 for ERC1155
- `tokenId`: The specific token identifier
- `contract.name`: NFT collection name

**Spam Detection**:
- NFTs include spam classification
- Use `excludeFilters: ["SPAM"]` to exclude spam NFTs from response
- Or process spam separately by checking response metadata

---

## Solana DAS API

### Overview

Alchemy supports the Metaplex Digital Asset Standard (DAS) API for Solana, providing unified access to both fungible tokens and NFTs.

**Base URL**: `https://solana-mainnet.g.alchemy.com/v2/{API_KEY}`

**Status**: Beta

**Important**: Spam detection is NOT available for Solana DAS API. All Solana assets should be treated as non-spam.

### Available Methods

| Method | CU Cost | Description |
|--------|---------|-------------|
| getAsset | 80 | Get single asset details |
| getAssets | 480 | Batch get multiple assets |
| getAssetsByOwner | 480 | Get all assets for a wallet |
| getAssetsByGroup | 480 | Get assets by collection |
| getAssetsByCreator | 480 | Get assets by creator |
| getAssetsByAuthority | 480 | Get assets by authority |
| searchAssets | 480 | Custom search queries |
| getTokenAccounts | 160 | Get token accounts/balances |

---

### getAssetsByOwner

Primary method for getting all Solana assets (native SOL, tokens, and NFTs) for a wallet.

**CU Cost**: 480 CU

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "getAssetsByOwner",
  "params": {
    "ownerAddress": "WALLET_PUBLIC_KEY",
    "page": 1,
    "limit": 1000,
    "displayOptions": {
      "showFungible": true,
      "showNativeBalance": true
    }
  },
  "id": 1
}
```

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| ownerAddress | string | Wallet public key (base58) |
| page | int | Page number (1-indexed) |
| limit | int | Results per page (max 1000) |
| displayOptions.showFungible | bool | Include SPL tokens |
| displayOptions.showNativeBalance | bool | Include SOL balance |

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "total": 150,
    "limit": 1000,
    "page": 1,
    "items": [
      {
        "id": "ASSET_ID",
        "interface": "FungibleToken",
        "content": {
          "metadata": {
            "name": "USD Coin",
            "symbol": "USDC"
          }
        },
        "token_info": {
          "balance": 1000000000,
          "decimals": 6
        }
      },
      {
        "id": "NFT_MINT_ADDRESS",
        "interface": "V1_NFT",
        "content": {
          "metadata": {
            "name": "Cool NFT #123",
            "symbol": "COOL"
          },
          "links": {
            "image": "https://..."
          }
        }
      }
    ]
  }
}
```

**Pagination**:
- Max page size: 1000
- Use `page` parameter (1-indexed)
- Continue until `items` array is empty or fewer than limit

**Asset Interfaces**:
- `FungibleToken`: SPL tokens
- `FungibleAsset`: Fungible tokens with metadata
- `V1_NFT`: Metaplex NFT (v1)
- `V2_NFT`: Metaplex NFT (v2)
- `ProgrammableNFT`: pNFTs
- `MplCoreAsset`: MPL Core standard

---

## Network-Specific Considerations

### Ethereum, Polygon, Base, BNB
- Full support for Token API and NFT API
- Native token balance via `eth_getBalance`
- Spam detection available for NFTs

### Solana
- Uses completely different API (DAS API)
- Different address format (base58 public keys)
- Different asset model (SPL tokens, Metaplex NFTs)
- DAS API is in Beta status
- **Spam detection NOT available**

---

## Authentication

### API Key
All requests require an API key passed in the URL:

```
https://{network}.g.alchemy.com/v2/{API_KEY}
```

### Security Recommendations
- Never commit API keys to source control
- Use environment variables or CLI arguments
- Consider IP allowlisting in Alchemy dashboard

---

## Error Handling

### Common Errors

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 400 | Bad Request | Check parameters |
| 401 | Unauthorized | Check API key |
| 429 | Rate Limited | Implement backoff |
| 500 | Server Error | Retry with backoff |
| 503 | Service Unavailable | Retry with backoff |

### Rate Limit Response
```json
{
  "error": {
    "code": 429,
    "message": "Too Many Requests"
  }
}
```

### Recommended Retry Strategy
1. Initial delay: 1 second
2. Exponential backoff: 2x each retry
3. Maximum retries: 5
4. Maximum delay: 32 seconds
5. Add jitter (±10%) to prevent thundering herd

---

## Additional Data Available

The following additional data is available from these APIs:

### From Token API
- Token logo URL
- Token symbol
- Decimal precision

### From NFT API
- Collection name and metadata
- NFT images (cached, thumbnail, original)
- Token URI and raw metadata
- Spam classification (EVM only)
- Last update timestamp

### From Solana DAS API
- Compression status (compressed vs regular NFTs)
- Token program (standard vs Token-2022)
- Creator addresses and royalty info
- Collection verification status

---

## References

- [Alchemy Documentation](https://www.alchemy.com/docs)
- [Token API Reference](https://www.alchemy.com/docs/reference/token-api-quickstart)
- [NFT API Reference](https://www.alchemy.com/docs/reference/nft-api-quickstart)
- [Solana DAS API](https://www.alchemy.com/docs/reference/alchemy-das-apis-for-solana)
- [Throughput & Rate Limits](https://www.alchemy.com/docs/reference/throughput)
- [Supported Chains](https://www.alchemy.com/docs/chains)
