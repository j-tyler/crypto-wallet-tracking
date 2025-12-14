#!/usr/bin/env python3
"""
Show current wallet assets across multiple blockchain networks.

This script queries a crypto wallet's holdings across Ethereum, Polygon,
Base, BNB Chain, and Solana networks and generates a CSV report of all
native tokens, fungible tokens, and NFTs.
"""

import argparse
import sys
from typing import List, Optional

from scripts.lib.alchemy_client import AlchemyClient
from scripts.lib.chain_scanners import create_scanner
from scripts.lib.formatters import combine_scan_results, write_csv
from scripts.lib.models import ScanResult


SUPPORTED_NETWORKS = ["ethereum", "polygon", "base", "bnb", "solana"]


def log(network: str, message: str) -> None:
    """Log a message with network prefix."""
    print(f"[{network}] {message}", file=sys.stderr)


def scan_network(client: AlchemyClient, network: str, wallet: str) -> ScanResult:
    """
    Scan a single network for wallet assets.

    Args:
        client: AlchemyClient instance
        network: Network to scan
        wallet: Wallet address

    Returns:
        ScanResult with all assets found
    """
    log(network, "Starting wallet scan...")

    scanner = create_scanner(client, network)
    result = scanner.scan(wallet)

    if result.error:
        log(network, f"ERROR: {result.error}. Skipping network.")
        return result

    # Log results
    if result.native_count > 0:
        native_symbol = (
            "SOL"
            if network == "solana"
            else {
                "ethereum": "ETH",
                "polygon": "MATIC",
                "base": "ETH",
                "bnb": "BNB",
            }.get(network, "")
        )
        log(network, f"Found {result.native_count} native token ({native_symbol})")

    if network == "solana":
        log(network, f"Found {result.token_count} SPL tokens")
        log(network, f"Found {result.nft_count} NFTs")
        log(network, "Spam detection not available for Solana")
    else:
        log(network, f"Found {result.token_count} ERC-20 tokens")
        if result.nft_count > 0 or result.erc721_count > 0 or result.erc1155_count > 0:
            log(
                network,
                f"Found {result.nft_count} NFTs ({result.erc721_count} ERC-721, "
                f"{result.erc1155_count} ERC-1155)",
            )
        if result.spam_count > 0:
            log(network, f"{result.spam_count} assets marked as spam")

    return result


def validate_networks(networks: List[str]) -> List[str]:
    """
    Validate and normalize network names.

    Args:
        networks: List of network names

    Returns:
        Validated list of lowercase network names

    Raises:
        ValueError: If any network is not supported
    """
    validated = []
    for network in networks:
        network_lower = network.lower()
        if network_lower not in SUPPORTED_NETWORKS:
            raise ValueError(
                f"Unsupported network: {network}. " f"Supported: {', '.join(SUPPORTED_NETWORKS)}"
            )
        validated.append(network_lower)
    return validated


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description=(
            "Query crypto wallet holdings across multiple networks " "and generate CSV report."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query Ethereum and Polygon, output to stdout
  %(prog)s --api-key YOUR_KEY --wallet 0x... --networks ethereum polygon

  # Query all networks, save to file
  %(prog)s --api-key YOUR_KEY --wallet 0x... \\
    --networks ethereum polygon base bnb solana --output wallet_report.csv
        """,
    )

    parser.add_argument(
        "--api-key",
        required=True,
        help="Alchemy API key",
    )
    parser.add_argument(
        "--wallet",
        required=True,
        help="Wallet address to query",
    )
    parser.add_argument(
        "--networks",
        nargs="+",
        required=True,
        help=f"Networks to query. Supported: {', '.join(SUPPORTED_NETWORKS)}",
    )
    parser.add_argument(
        "--output",
        help="Output file path (timestamp auto-appended). If not specified, outputs to stdout.",
    )

    parsed_args = parser.parse_args(args)

    # Validate networks
    try:
        networks = validate_networks(parsed_args.networks)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Initialize client
    client = AlchemyClient(parsed_args.api_key)

    # Scan each network
    results: List[ScanResult] = []
    for network in networks:
        result = scan_network(client, network, parsed_args.wallet)
        results.append(result)

    # Combine results
    all_assets, all_spam_assets = combine_scan_results(results)

    # Write output
    main_file, spam_file = write_csv(all_assets, all_spam_assets, parsed_args.output)

    if main_file:
        print(f"\nResults written to: {main_file}", file=sys.stderr)
        if spam_file:
            print(f"Spam assets written to: {spam_file}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
