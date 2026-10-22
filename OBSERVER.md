# Observer mode: verifiable audit outside the risk path

DWF's feedback on iteration 2: a market maker answers to its clients for their money and cannot put a third party into the risk path. Observer mode respects that completely.

- **Nothing changes in execution.** DWF's own system executes every trade exactly as today. Gravit receives a record of each trade only **after** execution and cannot delay, change or block it. If the observer is slow, offline or wrong, trading is not affected.
- **Every trade is re-checked** against the declared policy with the same rules as the pre-trade gate (independently corroborated prices, valuation, LTV, concentration, resolved markets). The finding (`CONSISTENT` or `EXCEPTION` with the reason) is signed and appended to a hash-chained log.
- **A daily seal.** A Merkle root over all entries of the day, signed. DWF can publish only the seal, no trade details. Later anyone holding the log can prove it was not rewritten: an edited, inserted or deleted entry, or a "nicer" seal, no longer verifies.

```bash
make setup PYTHON=python3.12 && make observe && make test
```

| Executed trade | Finding |
|---|---|
| Basket corroborated by two oracles, LTV within limit | CONSISTENT |
| Loan above the LTV limit | EXCEPTION |
| Agent marks a position above what oracles confirm | EXCEPTION |
| Agent overstates the basket value | EXCEPTION |
| Prices confirmed by one oracle only | EXCEPTION |
| Resolved market used as collateral | EXCEPTION |
| Basket concentrated in one market | EXCEPTION |

Tests show that hiding an exception, deleting or dropping an entry, or publishing a seal with fewer exceptions is detected (`tests/test_observer.py`).

Status: runnable demonstration; trades, oracles and keys are fictitious test fixtures; no connection to DWF or any venue. The observer key would be held by an independent operator; a second operator can co-sign the seal.
