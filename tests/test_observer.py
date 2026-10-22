import copy
import json
from pathlib import Path

from observer import EXCEPTION, PostTradeObserver, verify
from scenarios.observe import main

RESULTS = Path(__file__).resolve().parent.parent / "results"


def load():
    assert main() == 0
    entries = [json.loads(l) for l in (RESULTS / "observer-log.jsonl").read_text().splitlines()]
    seal = json.loads((RESULTS / "observer-seal.json").read_text())
    return entries, seal


def test_every_trade_is_recorded_and_none_is_blocked():
    entries, seal = load()
    assert len(entries) == 7 and seal["entries"] == 7
    # same judgement as the pre-trade gate, but only as findings after execution
    assert [e["body"]["finding"] for e in entries] == ["CONSISTENT"] + ["EXCEPTION"] * 6
    assert verify(entries, seal, seal["public_key"]) == (True, "log matches the seal")


def test_any_rewrite_of_history_is_detected():
    entries, seal = load()
    pk = seal["public_key"]
    edited = copy.deepcopy(entries)
    edited[3]["body"]["finding"] = "CONSISTENT"           # hide an exception
    assert not verify(edited, seal, pk)[0]
    assert not verify(entries[:2] + entries[3:], seal, pk)[0]   # delete an entry
    assert not verify(entries[:-1], seal, pk)[0]                # drop the last entry
    forged = dict(seal, exceptions=0)                            # publish a nicer seal
    assert not verify(entries, forged, pk)[0]


def test_observer_never_crashes_on_a_broken_record():
    obs = PostTradeObserver(lambda rec: (rec["request"]["loan_usd"] < 1, "ok", {}))
    e = obs.observe({"no_request": True})
    assert e["body"]["finding"] == EXCEPTION and "could not be evaluated" in e["body"]["reason"]
    assert verify(obs.entries, obs.seal("t"), obs.seal("t")["public_key"])[0]
