# Correction – status of the statements in this repository

**Date of correction:** 11 October 2026 · **Issued by:** Gravit Open Network Foundation

Several documents in this repository describe the Gravit × DWF pilot as launched and live.
**These statements describe a plan, not facts.** No deployment on Solana Mainnet (or any other
mainnet) took place, no capital ("TVL $18.4M", "$5M institutional pilot") was routed, and the
figures (capital efficiency 10.9x, jump risk hedged 97.5 %, etc.) are planning targets, not
measured results. The code in this repository is a concept sketch: it does not compile into a
working system (classes are declared but not implemented).

The joint statement in `dwf_partnership/joint_statement.md` is a **draft** for a possible future
announcement. It was not issued by DWF Ventures.

The original texts are **kept unchanged** below this correction, for the record: history is not
erased, it is corrected by adding to it.

| File | Statement | Status |
|---|---|---|
| `README.md` | "Live on Solana Mainnet with full multi-chain support" | plan |
| `RELEASE_NOTES.md` | "$5M DWF institutional pilot launched" | plan |
| `dwf_partnership/pilot_launch_report.md` | "Successfully Launched", "TVL: $18.4M" and further metrics | plan / targets |
| `dwf_partnership/joint_statement.md` | joint announcement of a successful launch | draft, not issued |
| `dwf_partnership/proposal.md` | "Multi-Chain Pilot Live", "now live on mainnet", "Pilot Results (Launched May 08, 2026)" | plan / targets |
| `pilot/launch_log_2026-05-08.md` | "Pilot successfully launched", "Total routed notional: $18.4M" | plan |
| `docs/multi_chain_defi_liquidity_pools.md` | "Pilot TVL: $18.4M" | target |
| `docs/qpu_roadmap.md` | "Hybrid Grover + VQE (live)" | plan |
| `observability/metrics_collector.cpp`, `market_integration/kalshi_solana_adapter_v2.5.rs`, `.github/workflows/mainnet-ci.yml`, `infrastructure/solana_mainnet/` | printed messages "Total TVL $18.4M", "Connected to Mainnet", "deployed successfully on Solana Mainnet" | demo output, no real connection or deployment |

**Next step:** the pilot is to be rebuilt on the public, tested
[Gravit Verifier](https://github.com/gravit-open-network-foundation/verifier) so that every claim
made here can be reproduced by anyone from code.
