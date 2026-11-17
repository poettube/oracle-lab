# Oracle Lab — daily automated run

This file is the instruction set for the scheduled "Oracle Lab daily run".
Everything here is fixed. Do not change methods, rules or past picks.

## 0. Setup
- Attach and clone the repo `poettube/oracle-lab` with push access. Work inside the clone.
- `python3 oracle_lab.py selftest` and `python3 oracle_lab.py verify` must both pass.
  If verify reports a BROKEN chain, stop and report it. Do not repair the log.
- Today = the current date in America/New_York.

## 1. Score what has been drawn
For every batch in `picks.jsonl` with no matching row in `results.csv` whose drawing
has already happened (yesterday's Evening Pick 3, any Pick 3 Day/Evening still open,
Powerball or Mega Millions from earlier nights):
- Look up the official numbers with WebSearch, then WebFetch a results page from the
  search results. Prefer palottery.pa.gov, powerball.com, megamillions.com; a second
  well-known results site (lottery.net, lotteryusa.com) is acceptable.
- Pick 3 needs the 3 digits AND the Wild Ball; Pick 4 needs the 4 digits AND the Wild Ball (same Wild Ball as that drawing's Pick 3). Powerball/Mega Millions need 5 white
  balls and the bonus ball (Power Play / multiplier not needed).
- Only enter a number you actually read on a page this run. If two sources disagree
  or none can be read, skip that drawing and list it in the summary as "unscored".
- Enter each with:
  - `python3 oracle_lab.py result pick3 YYYY-MM-DD Day 482 --wild 7`
  - `python3 oracle_lab.py result pick4 YYYY-MM-DD Evening 1071 --wild 2`
  - `python3 oracle_lab.py result powerball YYYY-MM-DD "4 5 15 19 55" --bonus 19`
  - `python3 oracle_lab.py result megamillions YYYY-MM-DD "3 22 34 54 61" --bonus 8`
- Never enter a result for a drawing twice (check results.csv first).

## 2. Lock today's picks (before the drawings)
- Pick 3: `python3 oracle_lab.py predict pick3 TODAY Day` and `... TODAY Evening`.
- Pick 4: `python3 oracle_lab.py predict pick4 TODAY Day` and `... TODAY Evening` (same draw times as Pick 3).
  Day draws are 1:05 PM (Sun–Mon) or 1:35 PM (Tue–Sat); Evening 6:57/6:59 PM ET.
  If it is already past a drawing's time, skip that drawing and say so.
- Powerball draws Mon, Wed, Sat (10:59 PM ET): on those days run
  `python3 oracle_lab.py predict powerball TODAY`.
- Mega Millions draws Tue, Fri (11:00 PM ET): on those days run
  `python3 oracle_lab.py predict megamillions TODAY`.
- If `dreams/TODAY.txt` exists in the repo, pass its text with `--dream "..."` to the
  Pick 3 and Pick 4 predictions.
- Never re-run predict for a drawing that already has a full batch locked. Check picks.jsonl for game+date+draw first (Powerball/Mega Millions are often locked days ahead).
- If the push to GitHub fails, do NOT keep the run's new locks secret: report the failure and the lock codes in the summary.

## 3. Save and publish
- `python3 oracle_lab.py verify` again.
- `python3 oracle_lab.py report > reports/latest.txt` and `python3 oracle_lab.py audit pick3 > reports/audit_pick3.txt` and `python3 oracle_lab.py audit pick4 > reports/audit_pick4.txt`.
- `python3 oracle_lab.py export dashboard` (writes dashboard/methods.json and draws.json).
- Commit everything with message `Daily run TODAY: scored N drawings, locked M batches` and push.
  The commit timestamp on GitHub is the outside proof the picks existed before the drawings.
- Update the dashboard "Oracle Lab Scoreboard" (artifact slug
  3acacb06-2fd8-4c65-a983-dd0d4e75ceb7): upload dashboard/methods.json and draws.json with
  upload_asset, then db_write `update` datasets/methods and datasets/draws (read each first for
  ifVersion) setting `source.url` to the new /_blob/ url, `updated: {at: <UTC now>, by: "Oracle Lab daily run"}`
  and `edit: {via: "claude", at: <UTC now>}`. Change nothing else on the dashboard.

## 4. Report
Send a short summary (push notification):
- results entered (with numbers), any drawing left unscored and why
- any win, by method, and the Random Control's wins for comparison
- today's lock codes
Keep it plain. No predictions, no claims that a method "is working" unless it beats
the Random Control over 30+ drawings.
