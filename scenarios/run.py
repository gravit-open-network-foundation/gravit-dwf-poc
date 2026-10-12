#!/usr/bin/env python3
"""Seven collateral requests through the gate; writes results/ (deterministic)."""

import json
from pathlib import Path

from pm_collateral.gate import CollateralGate, LoanRequest, Policy, Position, oracle_quote

NOW = "2026-10-12T12:00:00Z"
AS_OF = "2026-10-12T11:59:30Z"
POLICY = Policy(allowed_markets=["FED-CUT-DEC26", "BTC-150K-2026", "EU-AIACT-FINES-2026", "OLD-ELECTION-25"],
                resolved_or_halted=["OLD-ELECTION-25"])
BASKET = [Position("FED-CUT-DEC26", "YES", 40_000, 0.62), Position("BTC-150K-2026", "NO", 30_000, 0.71),
          Position("EU-AIACT-FINES-2026", "YES", 20_000, 0.35)]
TWO = ("oracle-venue-a", "oracle-venue-b")


def quotes(req, oracles=TWO, price_override=None):
    out = {}
    for p in req.positions:
        price = (price_override or {}).get(p.market, p.mark_price)
        out[p.market] = [oracle_quote(o, req.request_id, p.market, p.outcome, price, req.as_of) for o in oracles]
    return out


def value(positions):
    return round(sum(p.quantity * p.mark_price for p in positions), 2)


def scenarios():
    r = LoanRequest("req-01", "dwf-agent-1", BASKET, value(BASKET), 20_000, AS_OF)
    yield "Basket corroborated by two oracles, LTV within limit", r, quotes(r)
    r = LoanRequest("req-02", "dwf-agent-1", BASKET, value(BASKET), 30_000, AS_OF)
    yield "Loan above the LTV limit", r, quotes(r)
    inflated = [Position("FED-CUT-DEC26", "YES", 40_000, 0.80)] + BASKET[1:]
    r = LoanRequest("req-03", "dwf-agent-1", inflated, value(inflated), 20_000, AS_OF)
    yield "Agent marks a position above what oracles confirm", r, quotes(r, price_override={"FED-CUT-DEC26": 0.62})
    r = LoanRequest("req-04", "dwf-agent-1", BASKET, value(BASKET) * 1.15, 20_000, AS_OF)
    yield "Agent overstates the basket value", r, quotes(r)
    r = LoanRequest("req-05", "dwf-agent-1", BASKET, value(BASKET), 20_000, AS_OF)
    yield "Prices confirmed by one oracle only", r, quotes(r, oracles=("oracle-venue-a",))
    resolved = BASKET + [Position("OLD-ELECTION-25", "YES", 10_000, 0.99)]
    r = LoanRequest("req-06", "dwf-agent-1", resolved, value(resolved), 20_000, AS_OF)
    yield "Resolved market used as collateral", r, quotes(r)
    single = [Position("FED-CUT-DEC26", "YES", 60_000, 0.62), Position("BTC-150K-2026", "NO", 5_000, 0.71)]
    r = LoanRequest("req-07", "dwf-agent-1", single, value(single), 5_000, AS_OF)
    yield "Basket concentrated in one market", r, quotes(r)


def main() -> int:
    gate = CollateralGate(POLICY)
    rows = []
    for name, req, q in scenarios():
        e = gate.decide(req, q, NOW)
        rows.append({"scenario": name, "request": req.request_id, "outcome": e["body"]["outcome"], "reason": e["body"]["reason"]})
        print(f"{e['body']['outcome']:9} {name:55} {e['body']['reason'][:80]}")
    out = Path(__file__).resolve().parent.parent / "results"
    out.mkdir(exist_ok=True)
    (out / "decisions.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n")
    (out / "decision-log.jsonl").write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in gate.log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
