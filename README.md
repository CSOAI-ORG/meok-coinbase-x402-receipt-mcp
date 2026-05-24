# MEOK Coinbase x402 Receipt MCP

> ## 🧱 Part of the MEOK A2A Substrate (£999/mo)
> See [meok.ai/a2a](https://meok.ai/a2a).

# Signed settlement receipts for x402 / Coinbase / on-chain agentic payments

<!-- mcp-name: io.github.CSOAI-ORG/meok-coinbase-x402-receipt-mcp -->

[![PyPI](https://img.shields.io/pypi/v/meok-coinbase-x402-receipt-mcp)](https://pypi.org/project/meok-coinbase-x402-receipt-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## What this does

Closes the agentic-payment chain. After an agent settles a Coinbase HTTP 402 payment (via `meok-x402-wrap-mcp` / `agent-x402-paywall-mcp`), this MCP emits a non-repudiable **signed receipt** covering:

- Settlement chain (Base / Polygon / Solana / Lightning / Arbitrum / Optimism / Ethereum)
- Tx hash + block explorer URL + confirmation count
- Amount + currency + fiat EUR equivalent at settlement time
- Payer + payee DIDs
- Optional Stripe ACP linkage (intent_id, charge_id)
- Optional AP2 mandate linkage (mandate_id)
- HMAC + DID-bound signature

## Why this matters

EU MiCA + UK FCA crypto-asset rules require **non-repudiable settlement proof** for agentic transactions. Stripe ACP receipts cover card flows; this covers crypto flows. This MCP is the only thing that closes that gap.

## Tools

| Tool | Purpose |
|---|---|
| `emit_x402_receipt(tx_hash, chain, amount, currency, payer_did, payee_did, ...)` | Signed receipt |
| `verify_receipt(receipt)` | Cryptographic verification |
| `crosswalk_to_mica(receipt)` | MiCA Article 60 + 64 reporting fields |
| `bridge_to_stripe_acp(receipt, intent_id)` | Cross-protocol audit linkage |
| `list_supported_chains()` | 7 chains catalogued |
| `sign_settlement_chain(receipt_id, signer_did)` | DID-bound seal |

## Sister MCPs

- `agent-x402-paywall-mcp` — produces the on-chain settlement (this MCP receipts it)
- `meok-x402-wrap-mcp` — 1-line USDC paywall
- `meok-stripe-acp-checkout-mcp` — Stripe ACP intent linkage
- `meok-ap2-mandate-mcp` — AP2 mandate linkage
- `agent-audit-logger-mcp` — chain-of-custody log

Full catalogue: [meok.ai/anthropic-registry](https://meok.ai/anthropic-registry)

## Pricing

| Option | Price |
|---|---|
| Self-host MIT | £0 |
| Universal PAYG | £29/mo + £0.0002/call |
| A2A Substrate | £999/mo |
| Defence | £4,990/mo |

Buy: https://meok.ai/a2a

## Wire it up — full stack

The closed agentic-payment chain:

1. **meok-ap2-mandate-mcp** — user signs spend authorisation
2. **meok-stripe-acp-checkout-mcp** OR **agent-x402-paywall-mcp** — initiate
3. **agent-commerce-payments-mcp** (card) OR on-chain settlement
4. **meok-coinbase-x402-receipt-mcp** — this MCP (signs the settlement)
5. **agent-audit-logger-mcp** — chain-of-custody log
6. **a2a-governance-bridge-mcp** — fold into 1 signed event

See [meok.ai/mcp-stack](https://meok.ai/mcp-stack).

## Licence

MIT. By [MEOK AI Labs](https://meok.ai) (CSOAI LTD, UK Companies House 16939677).
