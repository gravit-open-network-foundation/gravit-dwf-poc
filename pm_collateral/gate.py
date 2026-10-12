"""
Verifiable collateral for prediction-market positions (Gravit x DWF, iteration 2).

An AI agent proposes to borrow against a basket of prediction-market positions
and declares their value. The gate never trusts the agent's valuation:

1. Hard policy: allowed markets only, no resolved or halted market as
   collateral, loan-to-value cap, per-market concentration cap.
2. Every position's mark price must be a "Verified Fact" for the public Gravit
   Verifier v0.5.0: signed quotes from at least two independent, registered
   price oracles, bound to exactly (market, outcome, price, as_of), fresh.
3. The gate re-values the basket from those corroborated prices and compares
   with the agent's declared value; an overstatement beyond tolerance is
   rejected.

Every decision is appended to a hash-chained log. Oracles, operators and keys
are fictitious TEST fixtures (derived from public seeds).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from gravit_verifier import EpistemicState, EvidenceRecord, VerificationRequest, VerifierKernel
from gravit_verifier.loader import load_bindings_from_dir
from gravit_verifier.registry import (TrustRoot, VerifierRegistry, key_id_for, registry_signing_message,
                                      signing_message)

ORACLES = {
    "oracle-venue-a": "Example Prediction Venue A Inc",
    "oracle-venue-b": "Example Prediction Venue B Ltd",
    "oracle-index-c": "Example Market Index AG",
}
BINDINGS = Path(os.environ.get("GRAVIT_BINDINGS", Path(__file__).resolve().parent.parent / ".deps" / "verifier" / "bindings"))
GENESIS = "0" * 64


def canonical(o: Any) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _key(n: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b"gravit-dwf-test:" + n.encode()).digest())


def _pub(n: str) -> bytes:
    return _key(n).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


def demo_registry() -> VerifierRegistry:
    doc = lambda o: (json.dumps(o, indent=1, sort_keys=True) + "\n").encode()
    roots = [f"root-{i}" for i in range(1, 6)]
    tr = TrustRoot.from_bytes(doc({"trust_root_version": 1, "threshold": 3, "root_keys": [
        {"key_id": key_id_for(_pub(r)), "public_key": base64.b64encode(_pub(r)).decode()} for r in roots]}))
    reg = doc({"registry_version": 1, "verifiers": [
        {"key_id": key_id_for(_pub(n)), "public_key": base64.b64encode(_pub(n)).decode(), "operator": op, "revoked": False}
        for n, op in ORACLES.items()]})
    msg = registry_signing_message(reg)
    sigs = "".join(f"{key_id_for(_pub(r))} {base64.b64encode(_key(r).sign(msg)).decode()}\n" for r in roots[:3])
    return VerifierRegistry.from_bytes(reg, sigs, tr)


def quote_hash(market: str, outcome: str, price: float, as_of: str) -> str:
    return hashlib.sha3_256(canonical({"market": market, "outcome": outcome, "price": price, "as_of": as_of})).hexdigest()


def oracle_quote(oracle: str, request_id: str, market: str, outcome: str, price: float, as_of: str) -> EvidenceRecord:
    r = EvidenceRecord(record_id=f"{oracle}:{request_id}:{market}", theta=0.96, result=True, verifier_id=oracle,
                       timestamp=as_of, provenance=ORACLES.get(oracle, "unregistered"),
                       integrity_hash=quote_hash(market, outcome, price, as_of), key_id=key_id_for(_pub(oracle)))
    r.signature = base64.b64encode(_key(oracle).sign(signing_message(f"{request_id}/{market}", r))).decode()
    return r


@dataclass
class Position:
    market: str
    outcome: str        # "YES" or "NO"
    quantity: float     # contracts paying 1.00 USD if the outcome occurs
    mark_price: float   # price (0..1) the agent used


@dataclass
class LoanRequest:
    request_id: str
    agent_id: str
    positions: List[Position]
    declared_value_usd: float
    loan_usd: float
    as_of: str


@dataclass
class Policy:
    allowed_markets: List[str]
    resolved_or_halted: List[str] = field(default_factory=list)
    max_ltv: float = 0.40
    max_concentration: float = 0.50
    valuation_tolerance: float = 0.01   # agent may differ from the verified value by at most 1 %


class CollateralGate:
    def __init__(self, policy: Policy, registry: Optional[VerifierRegistry] = None, freshness_seconds: int = 120) -> None:
        self.policy = policy
        self.kernel = VerifierKernel(registry or demo_registry())
        for b in load_bindings_from_dir(BINDINGS):
            self.kernel.load_binding(b)
        self.freshness = freshness_seconds
        self.log: List[Dict[str, Any]] = []

    def _price_verified(self, req: LoanRequest, p: Position, quotes: List[EvidenceRecord], now: str) -> Dict[str, Any]:
        h = quote_hash(p.market, p.outcome, p.mark_price, req.as_of)
        bound = [q for q in quotes if q.integrity_hash == h]
        d = self.kernel.verify(VerificationRequest(
            artifact_id=f"{req.request_id}/{p.market}", claimed_state=EpistemicState.VERIFIED_FACT, evidence=bound,
            context={"evaluation_time": now, "freshness_max_age_seconds": self.freshness, "high_impact": True}))
        return {"market": p.market, "state": d.final_epistemic_state.value if d.final_epistemic_state else None,
                "status": d.status.value, "records_bound": len(bound), "decision_id": d.decision_id}

    def decide(self, req: LoanRequest, quotes: Dict[str, List[EvidenceRecord]], now: str) -> Dict[str, Any]:
        pol = self.policy
        for p in req.positions:
            if p.market not in pol.allowed_markets:
                return self._log(req, "REJECTED", f"market {p.market!r} not allowed as collateral")
            if p.market in pol.resolved_or_halted:
                return self._log(req, "REJECTED", f"market {p.market!r} is resolved or halted")
        checks = [self._price_verified(req, p, quotes.get(p.market, []), now) for p in req.positions]
        unverified = [c["market"] for c in checks if c["state"] != "Verified Fact"]
        if unverified:
            return self._log(req, "REJECTED", f"mark price not independently corroborated: {unverified}", checks)
        values = {p.market: p.quantity * p.mark_price for p in req.positions}
        verified_value = round(sum(values.values()), 2)
        if req.declared_value_usd > verified_value * (1 + pol.valuation_tolerance):
            return self._log(req, "REJECTED", f"agent declared {req.declared_value_usd:,.2f} USD, verified value is "
                                              f"{verified_value:,.2f} USD", checks, verified_value)
        top = max(values.values()) / verified_value if verified_value else 1.0
        if top > pol.max_concentration:
            return self._log(req, "REJECTED", f"concentration {top:.0%} above {pol.max_concentration:.0%}", checks, verified_value)
        ltv = req.loan_usd / verified_value if verified_value else float("inf")
        if ltv > pol.max_ltv:
            return self._log(req, "REJECTED", f"LTV {ltv:.1%} above {pol.max_ltv:.0%}", checks, verified_value)
        return self._log(req, "APPROVED", f"LTV {ltv:.1%} on independently verified value {verified_value:,.2f} USD",
                         checks, verified_value)

    def _log(self, req, outcome, reason, checks=None, verified_value=None) -> Dict[str, Any]:
        body = {"request": json.loads(json.dumps(req, default=lambda o: o.__dict__)), "outcome": outcome,
                "reason": reason, "price_checks": checks, "verified_value_usd": verified_value}
        e = {"seq": len(self.log), "prev_hash": self.log[-1]["entry_hash"] if self.log else GENESIS, "body": body}
        e["entry_hash"] = hashlib.sha256(canonical(e)).hexdigest()
        self.log.append(e)
        return e
