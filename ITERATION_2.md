# Iteration 2 — verifiable collateral for prediction-market positions

Agreed with DWF (Andrei Grachev, Managing Partner) in October 2026. Builds the core of the idea
on the public [Gravit Verifier](https://github.com/gravit-open-network-foundation/verifier) v0.5.0;
the earlier concept material stays in the repository for the record (see CORRECTION.md).

An AI agent proposes a loan against a basket of prediction-market positions. The gate
(`pm_collateral/gate.py`) never trusts the agent's valuation: every mark price must be confirmed
by signed quotes from two independent oracles; the gate re-values the basket itself and enforces
allowed markets, no resolved/halted markets, LTV and concentration limits. Decisions are written
to a hash-chained log.

```bash
make setup PYTHON=python3.12 && make run && make test
```

| Scenario | Outcome |
|---|---|
| Basket corroborated by two oracles, LTV within limit | APPROVED |
| Loan above the LTV limit | REJECTED |
| Agent marks a position above what oracles confirm | REJECTED |
| Agent overstates the basket value | REJECTED |
| Prices confirmed by one oracle only | REJECTED |
| Resolved market used as collateral | REJECTED |
| Basket concentrated in one market | REJECTED |

Status: runnable demonstration; oracles, operators and keys are fictitious test fixtures; no
connection to DWF, Kalshi or any venue; nothing is deployed on any chain.
