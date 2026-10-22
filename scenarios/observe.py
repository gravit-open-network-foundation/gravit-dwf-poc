#!/usr/bin/env python3
"""
Observer mode: the same seven loans, but executed by the partner's own system
first and checked by Gravit only afterwards. Nothing is blocked; every finding
is signed, chained and sealed. Writes results/observer-*.json* (deterministic).
"""

import json
from dataclasses import asdict
from pathlib import Path

from observer import PostTradeObserver, verify
from pm_collateral.gate import CollateralGate, LoanRequest, Position
from scenarios.run import NOW, POLICY, scenarios

PERIOD = "2026-10-12"


def main() -> int:
    feed = {}       # signed oracle quotes, as the observer receives them from the price feed
    executed = []   # what the partner's system already executed (the observer cannot change it)
    for name, req, q in scenarios():
        feed[req.request_id] = q
        executed.append({"request": asdict(req), "executed_at": NOW, "scenario": name})

    gate = CollateralGate(POLICY)

    def evaluate(rec):
        r = rec["request"]
        req = LoanRequest(r["request_id"], r["agent_id"], [Position(**p) for p in r["positions"]],
                          r["declared_value_usd"], r["loan_usd"], r["as_of"])
        body = gate.decide(req, feed.get(req.request_id, {}), rec["executed_at"])["body"]
        return body["outcome"] == "APPROVED", body["reason"], {"verified_value_usd": body["verified_value_usd"]}

    obs = PostTradeObserver(evaluate, observer_id="observer-gravit-test")
    for rec in executed:
        e = obs.observe(rec)
        print(f"executed  {e['body']['finding']:10} {rec['scenario']:55} {e['body']['reason'][:60]}")
    seal = obs.seal(PERIOD)
    ok, why = verify(obs.entries, seal, seal["public_key"])
    print(f"\nseal {PERIOD}: {seal['entries']} trades, {seal['exceptions']} exceptions, root {seal['merkle_root'][:16]}...  verify: {why}")

    out = Path(__file__).resolve().parent.parent / "results"
    out.mkdir(exist_ok=True)
    (out / "observer-log.jsonl").write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in obs.entries))
    (out / "observer-seal.json").write_text(json.dumps(seal, indent=1, sort_keys=True) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
