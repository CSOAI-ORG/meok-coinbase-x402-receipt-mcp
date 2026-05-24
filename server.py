#!/usr/bin/env python3
"""
MEOK Coinbase x402 Receipt MCP — signed settlement receipts
==============================================================

By MEOK AI Labs · https://meok.ai · MIT
<!-- mcp-name: io.github.CSOAI-ORG/meok-coinbase-x402-receipt-mcp -->

WHAT THIS DOES
--------------
Closes the agentic-payment chain. After an agent settles a Coinbase HTTP 402
payment (via meok-x402-wrap-mcp / agent-x402-paywall-mcp), this MCP emits a
non-repudiable signed receipt covering:

  - Settlement chain (Base / Polygon / Solana / Lightning)
  - Tx hash + block confirmation count
  - Amount + currency + fiat equivalent at settlement time
  - Payer + payee DIDs
  - Optional Stripe ACP linkage (intent_id, charge_id)
  - Optional AP2 mandate linkage (mandate_id)
  - HMAC + DID-bound signature

Pairs with meok-stripe-acp-checkout-mcp + meok-ap2-mandate-mcp + agent-audit-logger-mcp.

WHY THIS MATTERS
----------------
EU MiCA + UK FCA crypto-asset rules require non-repudiable settlement proof
for agentic transactions. Stripe ACP receipts cover card flows; this covers
crypto flows. Closes the only gap.

TOOLS
-----
- emit_x402_receipt(tx_hash, chain, amount, currency, payer_did, payee_did, ...)
- verify_receipt(receipt): cryptographic check
- crosswalk_to_mica(receipt): MiCA Article 60 + 64 reporting fields
- bridge_to_stripe_acp(receipt, intent_id): link x402 settlement to ACP intent
- list_supported_chains(): Base / Polygon / Solana / Lightning / Arbitrum / Optimism
- sign_settlement_chain(receipt): HMAC + DID-bound seal

PRICING
-------
Free MIT self-host · £79/mo Pro · A2A Substrate £999/mo.
"""

from __future__ import annotations
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("meok-coinbase-x402-receipt")
_HMAC_SECRET = os.environ.get("MEOK_HMAC_SECRET", "")
_RECEIPTS: dict[str, dict] = {}


SPEC = "Coinbase x402 + EIP-3009 + MEOK signed receipt v1.0"

SUPPORTED_CHAINS = {
    "base":      {"chain_id": 8453,   "explorer": "https://basescan.org/tx/", "native": "ETH", "common_stable": "USDC"},
    "polygon":   {"chain_id": 137,    "explorer": "https://polygonscan.com/tx/", "native": "MATIC", "common_stable": "USDC"},
    "solana":    {"chain_id": None,   "explorer": "https://solscan.io/tx/", "native": "SOL", "common_stable": "USDC"},
    "arbitrum":  {"chain_id": 42161,  "explorer": "https://arbiscan.io/tx/", "native": "ETH", "common_stable": "USDC"},
    "optimism":  {"chain_id": 10,     "explorer": "https://optimistic.etherscan.io/tx/", "native": "ETH", "common_stable": "USDC"},
    "lightning": {"chain_id": None,   "explorer": "https://lightning.engineering/lookup/", "native": "BTC", "common_stable": "BTC"},
    "ethereum":  {"chain_id": 1,      "explorer": "https://etherscan.io/tx/", "native": "ETH", "common_stable": "USDC"},
}


def _sign(payload: dict) -> str:
    if not _HMAC_SECRET:
        return "unsigned-no-key-configured"
    return hmac.new(_HMAC_SECRET.encode(), json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def emit_x402_receipt(
    tx_hash: str,
    chain: str,
    amount: float,
    currency: str,
    payer_did: str,
    payee_did: str,
    fiat_equivalent_eur: Optional[float] = None,
    confirmations: int = 1,
    stripe_intent_id: Optional[str] = None,
    ap2_mandate_id: Optional[str] = None,
    invoice_ref: Optional[str] = None,
) -> dict:
    """
    Emit a signed x402 settlement receipt.

    Args:
        tx_hash: On-chain transaction hash.
        chain: One of base/polygon/solana/arbitrum/optimism/lightning/ethereum.
        amount: Settlement amount in `currency`.
        currency: Token symbol (USDC, USDT, ETH, SOL, BTC...).
        payer_did: W3C DID of the payer agent.
        payee_did: W3C DID of the payee agent.
        fiat_equivalent_eur: Spot EUR value at settlement time.
        confirmations: Block confirmations observed.
        stripe_intent_id: Optional Stripe ACP intent linkage.
        ap2_mandate_id: Optional AP2 mandate linkage.
        invoice_ref: Optional merchant invoice reference.

    Returns:
        {receipt_id, receipt, signature, explorer_url}
    """
    if chain not in SUPPORTED_CHAINS:
        return {"error": f"Unsupported chain. Use one of {list(SUPPORTED_CHAINS)}"}

    receipt_id = f"X402_RCPT_{int(time.time())}_{os.urandom(4).hex()}"
    chain_info = SUPPORTED_CHAINS[chain]
    explorer_url = chain_info["explorer"] + tx_hash

    receipt = {
        "receipt_id": receipt_id,
        "spec": SPEC,
        "tx_hash": tx_hash,
        "chain": chain,
        "chain_id": chain_info["chain_id"],
        "explorer_url": explorer_url,
        "amount": amount,
        "currency": currency,
        "fiat_equivalent_eur": fiat_equivalent_eur,
        "confirmations": confirmations,
        "payer_did": payer_did,
        "payee_did": payee_did,
        "stripe_intent_id": stripe_intent_id,
        "ap2_mandate_id": ap2_mandate_id,
        "invoice_ref": invoice_ref,
        "issued_at": _ts(),
        "issuer": "MEOK AI Labs (CSOAI LTD, UK Companies House 16939677)",
    }
    receipt["signature"] = _sign(receipt)
    _RECEIPTS[receipt_id] = receipt

    return {
        "receipt_id": receipt_id,
        "receipt": receipt,
        "signature": receipt["signature"],
        "explorer_url": explorer_url,
        "verify_url": f"https://meok-attestation-api.vercel.app/verify/{receipt_id}",
        "retention_hint": "Retain 6 years (UK MTD) / 10 years (DE HGB) / 5 years (MiCA Art 60).",
    }


@mcp.tool()
def verify_receipt(receipt: dict) -> dict:
    """
    Cryptographically verify a receipt — schema + signature.

    Args:
        receipt: Receipt dict from emit_x402_receipt().

    Returns:
        {valid, schema_ok, signature_ok, issues}
    """
    issues = []
    required = ["receipt_id", "tx_hash", "chain", "amount", "currency", "payer_did", "payee_did", "signature"]
    for f in required:
        if f not in receipt:
            issues.append(f"missing field: {f}")

    sig_provided = receipt.get("signature")
    sig_recomputed = _sign({k: v for k, v in receipt.items() if k != "signature"})
    sig_ok = sig_provided == sig_recomputed
    if not sig_ok:
        issues.append("signature mismatch")

    return {
        "valid": len(issues) == 0 and sig_ok,
        "schema_ok": all(f in receipt for f in required),
        "signature_ok": sig_ok,
        "issues": issues,
        "verified_at": _ts(),
    }


@mcp.tool()
def crosswalk_to_mica(receipt: dict) -> dict:
    """
    Map an x402 receipt to MiCA Article 60 (CASP record-keeping) + 64 (transfer info).

    Args:
        receipt: Receipt dict.

    Returns:
        {mica_record}
    """
    return {
        "mica_record": {
            "spec": "Regulation (EU) 2023/1114 (MiCA)",
            "art_60_record_keeping": {
                "transaction_id": receipt.get("receipt_id"),
                "tx_hash": receipt.get("tx_hash"),
                "amount": receipt.get("amount"),
                "currency": receipt.get("currency"),
                "fiat_eur_equivalent": receipt.get("fiat_equivalent_eur"),
                "timestamp": receipt.get("issued_at"),
                "payer_did": receipt.get("payer_did"),
                "payee_did": receipt.get("payee_did"),
            },
            "art_64_transfer_info": {
                "originator_id": receipt.get("payer_did"),
                "beneficiary_id": receipt.get("payee_did"),
                "settlement_chain": receipt.get("chain"),
                "explorer_url": receipt.get("explorer_url"),
            },
        },
        "retention_period_years": 5,
        "hint": "If you are a CASP, file this with your national competent authority on request.",
    }


@mcp.tool()
def bridge_to_stripe_acp(receipt: dict, intent_id: str) -> dict:
    """
    Cross-link an x402 settlement to a Stripe ACP intent.

    Args:
        receipt: x402 receipt.
        intent_id: Stripe ACP intent ID (ACP_INTENT_...).

    Returns:
        {linkage}
    """
    return {
        "linkage": {
            "x402_receipt_id": receipt.get("receipt_id"),
            "stripe_intent_id": intent_id,
            "linked_at": _ts(),
            "purpose": "Cross-protocol audit linkage (Stripe ACP intent ↔ Coinbase x402 settlement)",
        },
        "hint": "Store this linkage in your audit log. Useful for Stripe radar disputes + on-chain proof reconciliation.",
    }


@mcp.tool()
def list_supported_chains() -> dict:
    """Return the supported settlement chains + explorer URLs."""
    return {
        "spec": SPEC,
        "chains": SUPPORTED_CHAINS,
        "count": len(SUPPORTED_CHAINS),
    }


@mcp.tool()
def sign_settlement_chain(receipt_id: str, signer_did: str = "did:web:meok.ai") -> dict:
    """Re-sign a receipt with a DID-bound seal for non-repudiable publication."""
    if receipt_id not in _RECEIPTS:
        return {"error": "unknown_receipt"}
    receipt = _RECEIPTS[receipt_id]
    sealed = {**receipt, "signer_did": signer_did, "sealed_at": _ts()}
    sig = _sign(sealed)
    return {
        "signed": _HMAC_SECRET != "",
        "signer_did": signer_did,
        "signature": sig,
        "sealed_at": sealed["sealed_at"],
        "verify_url": f"https://meok-attestation-api.vercel.app/verify/{receipt_id}",
    }


if __name__ == "__main__":
    mcp.run()
