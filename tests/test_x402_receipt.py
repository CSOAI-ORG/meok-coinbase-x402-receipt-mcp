"""Smoke tests for meok-coinbase-x402-receipt-mcp."""
import sys, os, inspect, traceback
os.environ.setdefault("MEOK_HMAC_SECRET", "test-only-secret")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    emit_x402_receipt,
    verify_receipt,
    crosswalk_to_mica,
    bridge_to_stripe_acp,
    list_supported_chains,
    sign_settlement_chain,
    _RECEIPTS,
)


def test_emit_receipt_basic():
    _RECEIPTS.clear()
    r = emit_x402_receipt(
        tx_hash="0xabc123",
        chain="base",
        amount=10.0,
        currency="USDC",
        payer_did="did:web:payer.example",
        payee_did="did:web:payee.example",
        fiat_equivalent_eur=9.15,
    )
    assert r["receipt_id"].startswith("X402_RCPT_")
    assert "basescan.org" in r["explorer_url"]


def test_emit_receipt_unsupported_chain():
    r = emit_x402_receipt("0xabc", "carrier_pigeon", 1.0, "USDC", "did:x", "did:y")
    assert "error" in r


def test_emit_receipt_solana():
    _RECEIPTS.clear()
    r = emit_x402_receipt("solanasig", "solana", 5.0, "USDC", "did:x", "did:y")
    assert "solscan.io" in r["explorer_url"]


def test_emit_receipt_lightning():
    _RECEIPTS.clear()
    r = emit_x402_receipt("lninvoice123", "lightning", 0.0001, "BTC", "did:x", "did:y")
    assert "lightning.engineering" in r["explorer_url"]


def test_verify_receipt_round_trip():
    _RECEIPTS.clear()
    r = emit_x402_receipt("0xabc", "base", 10.0, "USDC", "did:x", "did:y")
    v = verify_receipt(r["receipt"])
    assert v["valid"] is True


def test_verify_receipt_detects_tampering():
    _RECEIPTS.clear()
    r = emit_x402_receipt("0xabc", "base", 10.0, "USDC", "did:x", "did:y")
    r["receipt"]["amount"] = 999999.0
    v = verify_receipt(r["receipt"])
    assert v["signature_ok"] is False


def test_crosswalk_to_mica():
    _RECEIPTS.clear()
    r = emit_x402_receipt("0xabc", "base", 10.0, "USDC", "did:x", "did:y", fiat_equivalent_eur=9.15)
    c = crosswalk_to_mica(r["receipt"])
    assert "Regulation (EU) 2023/1114" in c["mica_record"]["spec"]
    assert c["mica_record"]["art_60_record_keeping"]["fiat_eur_equivalent"] == 9.15


def test_bridge_to_stripe_acp():
    _RECEIPTS.clear()
    r = emit_x402_receipt("0xabc", "base", 10.0, "USDC", "did:x", "did:y")
    b = bridge_to_stripe_acp(r["receipt"], "ACP_INTENT_abc")
    assert b["linkage"]["stripe_intent_id"] == "ACP_INTENT_abc"


def test_list_supported_chains():
    r = list_supported_chains()
    assert r["count"] >= 6
    assert "base" in r["chains"]
    assert "solana" in r["chains"]
    assert "lightning" in r["chains"]


def test_sign_settlement_chain():
    _RECEIPTS.clear()
    r = emit_x402_receipt("0xabc", "base", 10.0, "USDC", "did:x", "did:y")
    s = sign_settlement_chain(r["receipt_id"])
    assert "signature" in s


def test_sign_unknown_receipt():
    r = sign_settlement_chain("X402_FAKE")
    assert "error" in r


if __name__ == "__main__":
    g = dict(globals())
    fns = [v for k, v in g.items() if k.startswith("test_") and inspect.isfunction(v)]
    p = f = 0
    for fn in fns:
        try:
            fn(); print(f"OK {fn.__name__}"); p += 1
        except Exception as e:
            print(f"X  {fn.__name__}: {type(e).__name__}: {e}"); traceback.print_exc(); f += 1
    print(f"\n{p} passed, {f} failed")
