# Oracle Lab

A locked, reproducible test of symbolic (I Ching, Tarot, Ifá, Napoleon's Oraculum, Dream-Symbolic)
and statistical (Hot-Cold, Historic Hot-Cold, Prime, Overdue, Recurring Pairs, Unpopular Numbers)
lottery methods against a Random Control, for PA Pick 3 and Pick 4 (with Wild Ball), Powerball and Mega Millions.

- `oracle_lab.py` — the tool (see its header for commands)
- `picks.jsonl` — every locked batch, SHA-256 hash-chained (`python3 oracle_lab.py verify`)
- `results.csv` — official results (first 77 Pick 3 rows came from an earlier ChatGPT ledger, unverified)
- `RUNBOOK.md` — what the daily automated run does
- `dreams/YYYY-MM-DD.txt` — optional dream text for that day's Dream-Symbolic picks
- `reports/` — latest scores and randomness audit

No method can change the odds of a fair draw; this lab measures whether any does better than chance.
