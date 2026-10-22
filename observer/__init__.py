"""
Post-trade observer: verifiable audit outside the risk path.

The partner's own system executes every trade as before. Afterwards it hands
the observer a record of what was executed. The observer re-checks each record
against the declared policy, signs its finding and appends it to a hash-chained
log. It never sees a trade before execution and cannot stop one: if the
observer is slow, offline or wrong, trading is not affected.

Once per period the observer seals the log: a Merkle root over all entry
hashes of the period, signed. The partner can publish only the seal (no trade
details) and anyone can later prove that the log was not rewritten: an edited,
inserted or deleted entry no longer matches the seal.

Keys are fictitious TEST fixtures derived from public seeds.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Callable, Dict, List, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

GENESIS = "0" * 64
CONSISTENT, EXCEPTION = "CONSISTENT", "EXCEPTION"

# evaluate(record) -> (consistent?, reason, details)
Evaluator = Callable[[Dict[str, Any]], Tuple[bool, str, Dict[str, Any]]]


def canonical(o: Any) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def test_key(name: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b"gravit-observer-test:" + name.encode()).digest())


def public_key_b64(key: Ed25519PrivateKey) -> str:
    return base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()


def merkle_root(leaves: List[str]) -> str:
    """SHA-256 binary Merkle tree over hex leaves; an odd node is promoted unchanged."""
    if not leaves:
        return hashlib.sha256(b"").hexdigest()
    level = [bytes.fromhex(h) for h in leaves]
    while len(level) > 1:
        nxt = [hashlib.sha256(b"\x01" + level[i] + level[i + 1]).digest() for i in range(0, len(level) - 1, 2)]
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    return level[0].hex()


class PostTradeObserver:
    def __init__(self, evaluate: Evaluator, observer_id: str = "observer-test", key: Ed25519PrivateKey | None = None):
        self.evaluate = evaluate
        self.observer_id = observer_id
        self.key = key or test_key(observer_id)
        self.entries: List[Dict[str, Any]] = []

    def observe(self, executed: Dict[str, Any]) -> Dict[str, Any]:
        """Record one already executed trade. Never raises on a bad trade: it records an EXCEPTION."""
        try:
            ok, reason, details = self.evaluate(executed)
        except Exception as e:  # a broken record is itself a finding, never a crash of the observer
            ok, reason, details = False, f"record could not be evaluated: {type(e).__name__}: {e}", {}
        body = {"observer": self.observer_id, "executed": executed, "finding": CONSISTENT if ok else EXCEPTION,
                "reason": reason, "details": details}
        e = {"seq": len(self.entries), "prev_hash": self.entries[-1]["entry_hash"] if self.entries else GENESIS, "body": body}
        e["entry_hash"] = hashlib.sha256(canonical(e)).hexdigest()
        e["signature"] = base64.b64encode(self.key.sign(bytes.fromhex(e["entry_hash"]))).decode()
        self.entries.append(e)
        return e

    def seal(self, period: str) -> Dict[str, Any]:
        s = {"observer": self.observer_id, "period": period, "entries": len(self.entries),
             "exceptions": sum(e["body"]["finding"] == EXCEPTION for e in self.entries),
             "last_entry_hash": self.entries[-1]["entry_hash"] if self.entries else GENESIS,
             "merkle_root": merkle_root([e["entry_hash"] for e in self.entries]),
             "public_key": public_key_b64(self.key)}
        s["signature"] = base64.b64encode(self.key.sign(canonical(s))).decode()
        return s


def verify(entries: List[Dict[str, Any]], seal: Dict[str, Any], public_key: str) -> Tuple[bool, str]:
    """Independent check by anyone: chain, every signature, and the seal. Returns (ok, reason)."""
    pk = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key))
    s = {k: v for k, v in seal.items() if k != "signature"}
    try:
        pk.verify(base64.b64decode(seal["signature"]), canonical(s))
    except InvalidSignature:
        return False, "seal signature invalid"
    prev = GENESIS
    for i, e in enumerate(entries):
        if e["seq"] != i or e["prev_hash"] != prev:
            return False, f"chain broken at entry {i}"
        h = hashlib.sha256(canonical({k: e[k] for k in ("seq", "prev_hash", "body")})).hexdigest()
        if h != e["entry_hash"]:
            return False, f"entry {i} was modified"
        try:
            pk.verify(base64.b64decode(e["signature"]), bytes.fromhex(h))
        except InvalidSignature:
            return False, f"entry {i} signature invalid"
        prev = h
    if seal["entries"] != len(entries) or seal["merkle_root"] != merkle_root([e["entry_hash"] for e in entries]):
        return False, "log does not match the seal"
    if seal["exceptions"] != sum(e["body"]["finding"] == EXCEPTION for e in entries):
        return False, "exception count does not match the seal"
    return True, "log matches the seal"
