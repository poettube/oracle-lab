# Oracle Lab — method specification (v2)

You are being briefed on a fixed, pre-registered experiment. Do not reinterpret, improvise, or "improve" any rule below. If you are asked to produce picks, you must not invent castings in text: every random step must come from a real random source (code, dice, coins, cards) and be logged. The tool `oracle_lab.py` in github.com/poettube/oracle-lab is the reference implementation; if this text and the code disagree, the code wins.

## Purpose
Test whether symbolic and statistical number-selection methods beat a Random Control on PA Pick 3 and Pick 4 (with Wild Ball), Powerball (5 of 1–69 + 1 of 1–26) and Mega Millions (5 of 1–70 + 1 of 1–24). The working hypothesis is that none will, because the draws are independent; the lab measures that honestly.

## Ground rules
- Every method makes exactly 3 tickets per drawing.
- All tickets for a drawing are locked before the drawing, timestamped, and SHA-256 hash-chained (each batch includes the previous batch's hash). Locked picks are never edited.
- Every random step uses a cryptographic RNG (Python `secrets`), and the raw outcome (coins, cards, halves, dots) is saved with the pick.
- Results are entered only from published results pages; never guessed.
- Ties in any statistical ranking are broken by a logged random draw.

## Number-building rule (all symbolic methods)
Each casting yields one integer value ≥ 1.
- Pick 3 / Pick 4: each digit = value mod 10, one casting per digit (3 or 4 castings per ticket).
- Powerball / Mega Millions: white ball = ((value − 1) mod range) + 1; if that ball is already on the ticket, cast again. The bonus ball uses the same rule on its own range (26 or 24).

## Symbolic methods
1. I Ching — three-coin method, six times, bottom line first. Heads = 3, tails = 2. Line sum 6 = old yin, 7 = young yang, 8 = young yin, 9 = old yang (6 and 9 are changing lines). Lower and upper trigrams give the King Wen hexagram number (1–64). Value = hexagram number. Changing lines are recorded but not used in the number.
2. Tarot — full 78-card deck, cryptographically shuffled once per drawing, cards drawn in order without replacement. Value = card position 1–78: Major Arcana 0–21 → 1–22, then Wands, Cups, Swords, Pentacles, each Ace…Ten, Page, Knight, Queen, King. Reversal (50%) is recorded but not used.
3. Ifá — opele chain of 8 halves, each open (single mark, I) or closed (double mark, II). First 4 halves = right leg, last 4 = left leg; each leg is one of the 16 principal Odù in the order Ogbe, Oyeku, Iwori, Odi, Irosun, Owonrin, Obara, Okanran, Ogunda, Osa, Ika, Oturupon, Otura, Irete, Ose, Ofun (index 0–15). Value = right×16 + left + 1 (1–256). Same leg twice = "Meji".
4. Napoleon's Oraculum — 4 rows of dots, 12–30 dots per row (random count, "marked without counting"). Odd row = one star (1), even row = two stars (0). Figure = row1×8 + row2×4 + row3×2 + row4 + 1 (1–16). Value = figure number. (Pick 3/4 digits therefore come from 1–16; big-game balls can only be 1–16.)
5. Dream-Symbolic — the user supplies a dream in writing. Words are matched, in order of appearance, against a fixed table of ~100 symbols, each mapped to a number 1–99 (e.g. water 1, river 2, snake 6, dog 7, house 12, money 18, moon 30, taxi 44, music 49, light 99; full table in the code). Values are used in order and reused from the start if the dream runs out. No dream or no table words → the method is skipped for that drawing. No interpretation is allowed.

## Statistical methods (computed from the results file; need ≥ 10 past results; for Pick 3/4 only the same draw time, Day or Evening)
Pick 3/4 (N = 3 or 4 digits):
6. Hot-Cold (last 30 drawings) — ticket 1: N most frequent digits; ticket 2: most frequent digit in each position; ticket 3: the N−1 hottest digits + the coldest.
7. Historic Hot-Cold (all recorded drawings) — ticket 1: N hottest; ticket 2: N coldest; ticket 3: hottest + coldest + the next N−2 hottest.
8. Prime (digits 2, 3, 5, 7 only) — ticket 1: primes ranked by last-30 frequency; ticket 2: by all-time frequency; ticket 3: by longest absence. First N of each ranking.
9. Overdue — ticket 1: the N digits absent longest from any position; tickets 2 and 3: the most and second-most overdue digit in each position.
10. Recurring Pairs — top 3 unordered digit pairs over the last 90 drawings; each ticket = a pair + the hottest (last-30) digits not in the pair to fill N.
- If two statistical tickets in one method are identical, the repeat is rotated one place.

Powerball / Mega Millions:
- Hot-Cold (last 50): hottest 5 + hottest bonus; next 5 hottest + 2nd bonus; 3 hottest + 2 coldest + coldest bonus.
- Historic Hot-Cold (all): hottest 5; coldest 5; 3 hot + 2 cold, with matching bonus picks.
- Prime: prime white balls only (19 primes ≤ 69/70) and prime bonus balls, ranked by recent frequency, all-time frequency, and longest absence.
- Overdue: the 15 longest-absent white balls split into three tickets; the 3 longest-absent bonus balls.
- Recurring Pairs: top 6 pairs over the last 100 drawings, two pairs per ticket, filled with hot balls.
11. Unpopular Numbers (big games only) — white balls drawn at random from 32 to max (avoiding the birthday range 1–31), bonus ball at random from the upper half of its range. This changes jackpot sharing, not odds.

## Control
12. Random Control — 3 uniformly random tickets per drawing from a cryptographic RNG. Every method is judged against it on the same drawings.

## Scoring
- Pick 3: straight, box, Wild Ball straight, Wild Ball box (the Wild Ball replaces any one drawn digit), front pair, back pair; plus digits shared (multiset) and digits in the right position. Chance: average 0.73 digits shared per ticket.
- Pick 4: straight, box, Wild Ball straight, Wild Ball box; pairs shown but not counted as wins. Chance: average 1.21 digits shared.
- Big games: white balls matched + bonus match; any official prize tier counts as a win. Chance: average 25/69 or 25/70 white matches per ticket.
- Randomness audit (on history): digit/ball frequency, per-position frequency, most common pair, repeats from the previous drawing, consecutive numbers; p-values from 2,000 simulated fair histories.
- A method is only called better than chance if it beats the Random Control over 30+ drawings and survives correction for testing many methods at once.

## Background
Over 2,202 earlier picks from an unverified ChatGPT-run ledger (Sept 25–Nov 15, 2026), all 27 method labels scored at chance (11 wins vs 11.5 expected). That ledger's symbolic picks were generated in text without real castings, which is why v2 exists.
