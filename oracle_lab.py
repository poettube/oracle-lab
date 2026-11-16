#!/usr/bin/env python3
"""
ORACLE LAB v2 — a fair, locked, reproducible test of symbolic and statistical
lottery methods for PA Pick 3 and Pick 4 (with Wild Ball), Powerball, and Mega Millions.

Every method below is a FIXED rule written once and never changed mid-test.
Every random step uses the operating system's cryptographic RNG (secrets),
and the actual coins / cards / casts / dots are saved with each pick.
Each locked batch is chained with SHA-256 so later edits are detectable.

USAGE
  python oracle_lab.py predict pick3 2026-11-16 Day [--dream "I dreamed of a snake by a river"]
  python oracle_lab.py predict powerball 2026-11-16
  python oracle_lab.py predict megamillions 2026-11-17
  python oracle_lab.py result  pick3 2026-11-16 Day 482 --wild 7
  python oracle_lab.py result  powerball 2026-11-16 "4 5 15 19 55" --bonus 19
  python oracle_lab.py report  [pick3|powerball|megamillions]
  python oracle_lab.py verify            # checks the hash chain
  python oracle_lab.py audit pick3 [Day|Evening]   # randomness tests on history
  python oracle_lab.py selftest

FILES (created next to this script)
  picks.jsonl     locked predictions (append-only, hash-chained)
  results.csv     official results you enter: game,date,draw,numbers,bonus
"""
import sys, os, json, csv, hashlib, secrets, argparse, re, itertools
from collections import Counter
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
PICKS = os.path.join(HERE, "picks.jsonl")
RESULTS = os.path.join(HERE, "results.csv")
ET = ZoneInfo("America/New_York")
PICKS_PER_METHOD = 3
rng = secrets.SystemRandom()

# --------------------------------------------------------------------------
# GAMES
# --------------------------------------------------------------------------
GAMES = {
    "pick3":        dict(kind="digits", n=3, draws=["Day", "Evening"]),
    "pick4":        dict(kind="digits", n=4, draws=["Day", "Evening"]),
    "powerball":    dict(kind="lotto", n=5, main=69, bonus=26, bonus_name="Powerball", draws=["Main"]),
    "megamillions": dict(kind="lotto", n=5, main=70, bonus=24, bonus_name="Mega Ball", draws=["Main"]),
}

# --------------------------------------------------------------------------
# SYMBOLIC SYSTEMS — each casting returns (value >= 1, record of what happened)
# --------------------------------------------------------------------------

# I CHING: three-coin method. heads=3, tails=2. Line sum 6=old yin, 7=young yang,
# 8=young yin, 9=old yang. Lines built bottom to top. King Wen number from trigrams.
TRIGRAMS = {  # bottom->top, 1=yang
    (1,1,1): "Qian", (1,0,0): "Zhen", (0,1,0): "Kan", (0,0,1): "Gen",
    (0,0,0): "Kun", (0,1,1): "Xun", (1,0,1): "Li", (1,1,0): "Dui"}
TRI_ORDER = ["Qian", "Zhen", "Kan", "Gen", "Kun", "Xun", "Li", "Dui"]
KING_WEN = [  # rows = lower trigram, cols = upper trigram, in TRI_ORDER
    [1, 34, 5, 26, 11, 9, 14, 43],
    [25, 51, 3, 27, 24, 42, 21, 17],
    [6, 40, 29, 4, 7, 59, 64, 47],
    [33, 62, 39, 52, 15, 53, 56, 31],
    [12, 16, 8, 23, 2, 20, 35, 45],
    [44, 32, 48, 18, 46, 57, 50, 28],
    [13, 55, 63, 22, 36, 37, 30, 49],
    [10, 54, 60, 41, 19, 61, 38, 58]]

def king_wen(lines):
    lo, up = TRIGRAMS[tuple(lines[:3])], TRIGRAMS[tuple(lines[3:])]
    return KING_WEN[TRI_ORDER.index(lo)][TRI_ORDER.index(up)], lo, up

def cast_iching():
    tosses, lines, changing = [], [], []
    for i in range(6):
        coins = [rng.choice(["H", "T"]) for _ in range(3)]
        total = sum(3 if c == "H" else 2 for c in coins)
        tosses.append("".join(coins))
        lines.append(1 if total in (7, 9) else 0)
        if total in (6, 9): changing.append(i + 1)
    num, lo, up = king_wen(lines)
    return num, {"coins": tosses, "hexagram": num, "lower": lo, "upper": up, "changing_lines": changing}

# TAROT: full 78-card deck, cryptographically shuffled once per drawing.
# Value = position 1-78: Majors 0-21 -> 1-22, then Wands, Cups, Swords, Pentacles Ace..King.
MAJORS = ["The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
          "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
          "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance", "The Devil",
          "The Tower", "The Star", "The Moon", "The Sun", "Judgement", "The World"]
RANKS = ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
         "Page", "Knight", "Queen", "King"]
DECK = MAJORS + [f"{r} of {s}" for s in ["Wands", "Cups", "Swords", "Pentacles"] for r in RANKS]

class TarotDeck:
    def __init__(self):
        self.order = list(range(78)); rng.shuffle(self.order); self.pos = 0
    def draw(self):
        if self.pos >= 78: self.__init__()
        i = self.order[self.pos]; self.pos += 1
        rev = rng.random() < 0.5
        return i + 1, {"card": DECK[i], "reversed": rev, "value": i + 1}

# IFA: opele chain of 8 halves; each falls open (I, single mark) or closed (II, double).
# Right leg = first 4, left leg = last 4. Each leg is one of the 16 principal Odu
# in the traditional order Ogbe..Ofun. Combined Odu number = right*16 + left + 1 (1-256).
ODU = [("Ogbe", "IIII"), ("Oyeku", "XXXX"), ("Iwori", "XIIX"), ("Odi", "IXXI"),
       ("Irosun", "IIXX"), ("Owonrin", "XXII"), ("Obara", "IXXX"), ("Okanran", "XXXI"),
       ("Ogunda", "IIIX"), ("Osa", "XIII"), ("Ika", "XIXX"), ("Oturupon", "XXIX"),
       ("Otura", "IXII"), ("Irete", "IIXI"), ("Ose", "IXIX"), ("Ofun", "XIXI")]
# I = single mark (open), X = double mark (closed), read top to bottom
ODU_BY_PAT = {p: (k, n) for k, (n, p) in enumerate(ODU)}

def cast_ifa():
    halves = "".join(rng.choice("IX") for _ in range(8))
    ri, rn = ODU_BY_PAT[halves[:4]]; li, ln = ODU_BY_PAT[halves[4:]]
    name = f"{rn} Meji" if ri == li else f"{rn} {ln}"
    return ri * 16 + li + 1, {"halves": halves, "odu": name, "value": ri * 16 + li + 1}

# NAPOLEON'S ORACULUM: mark 4 rows of dots without counting (simulated as 12-30
# dots per row). Odd row = one star, even row = two stars. The four rows form one
# of the 16 figures. Figure number = binary position (odd=1) + 1, giving 1-16.
def cast_oraculum():
    rows = [rng.randint(12, 30) for _ in range(4)]
    bits = [r % 2 for r in rows]
    fig = bits[0] * 8 + bits[1] * 4 + bits[2] * 2 + bits[3] + 1
    pattern = "".join("*" if b else "**" for b in bits)
    return fig, {"dot_rows": rows, "figure": fig, "pattern": "/".join("*" if b else "**" for b in bits)}

# DREAM-SYMBOLIC: fixed lookup table, symbol -> number (1-99). Symbols are read in
# the order they appear in the dream text. No interpretation, no improvising.
# This table is OUR fixed rule for this experiment (not a traditional dream book).
DREAM_TABLE = {
 "water":1,"river":2,"ocean":3,"sea":3,"rain":4,"fire":5,"snake":6,"dog":7,"cat":8,"bird":9,
 "fish":10,"horse":11,"house":12,"door":13,"key":14,"car":15,"road":16,"bridge":17,"money":18,
 "gold":19,"baby":20,"child":21,"mother":22,"father":23,"wedding":24,"death":25,"funeral":26,
 "church":27,"tree":28,"flower":29,"moon":30,"sun":31,"star":32,"falling":33,"flying":34,
 "running":35,"teeth":36,"blood":37,"knife":38,"gun":39,"police":40,"school":41,"work":42,
 "store":43,"taxi":44,"train":45,"plane":46,"boat":47,"ship":47,"phone":48,"music":49,"song":49,
 "guitar":50,"book":51,"letter":52,"food":53,"bread":54,"wine":55,"mirror":56,"window":57,
 "stairs":58,"elevator":59,"hospital":60,"doctor":61,"friend":62,"stranger":63,"lover":64,
 "kiss":65,"fight":66,"crying":67,"laughing":68,"naked":69,"lost":70,"chase":71,"chased":71,
 "storm":72,"snow":73,"mountain":74,"cave":75,"spider":76,"rat":77,"lion":78,"bear":79,
 "wolf":80,"angel":81,"devil":82,"ghost":83,"grandmother":84,"grandfather":85,"son":86,
 "daughter":87,"brother":88,"sister":89,"ring":90,"clock":91,"shoes":92,"hair":93,"eyes":94,
 "hands":95,"egg":96,"milk":97,"crown":98,"light":99,"dark":99}

def dream_values(text):
    words = re.findall(r"[a-z]+", (text or "").lower())
    out = []
    for w in words:
        w2 = w if w in DREAM_TABLE else (w[:-1] if w.endswith("s") and w[:-1] in DREAM_TABLE else None)
        if w2: out.append((DREAM_TABLE[w2], w2))
    return out

# --------------------------------------------------------------------------
# NUMBER-BUILDING RULE (same for every symbolic method)
#   Pick 3:  digit = value mod 10 (one casting per digit).
#   Lotto:   ball = ((value - 1) mod range) + 1; if already on the ticket,
#            cast again. Bonus ball uses the same rule on its own range.
# --------------------------------------------------------------------------
def build_ticket(game, cast, record):
    g = GAMES[game]
    if g["kind"] == "digits":
        digs = []
        for _ in range(g["n"]):
            v, rec = cast(); record.append(rec); digs.append(v % 10)
        return "".join(map(str, digs)), None
    main = []
    while len(main) < g["n"]:
        v, rec = cast(); record.append(rec)
        b = (v - 1) % g["main"] + 1
        if b not in main: main.append(b)
    v, rec = cast(); record.append(dict(rec, for_bonus=True))
    return sorted(main), (v - 1) % g["bonus"] + 1

# --------------------------------------------------------------------------
# STATISTICAL METHODS — exact math on results.csv history (same game & draw).
# Ties are broken by a logged random draw.
# --------------------------------------------------------------------------
def history(game, draw=None):
    rows = [r for r in load_results() if r["game"] == game and (draw is None or r["draw"] == draw)]
    rows.sort(key=lambda r: (r["date"], GAMES[game]["draws"].index(r["draw"]) if r["draw"] in GAMES[game]["draws"] else 0))
    return rows

def ranked(counter, universe, reverse=True):
    tie = {u: rng.random() for u in universe}
    return sorted(universe, key=lambda u: ((-counter.get(u, 0)) if reverse else counter.get(u, 0), tie[u]))

def gaps(hist_items, universe):
    g = {u: len(hist_items) + 1 for u in universe}  # never seen = longest
    for age, items in enumerate(reversed(hist_items)):
        for u in set(items) & set(universe):
            if g[u] > age: g[u] = age
    return g

def stat_tickets(game, draw, method):
    g = GAMES[game]
    h = history(game, draw if g["kind"] == "digits" else None)
    if len(h) < 10:
        return None, {"skipped": f"only {len(h)} results on file; need 10+"}
    if g["kind"] == "digits":
        N = g["n"]
        res = [r["numbers"] for r in h]
        U = list("0123456789")
        win = res[-30:]
        freq = Counter("".join(win))
        if method == "Hot-Cold":
            hot = ranked(freq, U); cold = ranked(freq, U, reverse=False)
            pos = [ranked(Counter(r[i] for r in win), U)[0] for i in range(N)]
            t = ["".join(hot[:N]), "".join(pos), "".join(hot[:N-1]) + cold[0]]
            return t, {"window": len(win), "hot": hot[:N], "cold": cold[:N]}
        if method == "Historic Hot-Cold":
            af = Counter("".join(res)); hot = ranked(af, U); cold = ranked(af, U, reverse=False)
            t = ["".join(hot[:N]), "".join(cold[:N]), hot[0] + cold[0] + "".join(hot[1:N-1])]
            return t, {"window": "all %d draws" % len(res), "hot": hot[:N], "cold": cold[:N]}
        if method == "Prime":
            P = list("2357"); af = Counter("".join(res)); gp = gaps([list(r) for r in res], P)
            recent = ranked(freq, P); alltime = ranked(af, P)
            od = sorted(P, key=lambda u: (-gp[u], rng.random()))
            t = ["".join(recent[:N]), "".join(alltime[:N]), "".join(od[:N])]
            return t, {"primes": P, "recent_rank": recent, "alltime_rank": alltime, "overdue_rank": od}
        if method == "Overdue":
            gp = gaps([list(r) for r in res], U)
            od = sorted(U, key=lambda u: (-gp[u], rng.random()))
            posg = [gaps([[r[i]] for r in res], U) for i in range(N)]
            p1 = "".join(sorted(U, key=lambda u: (-posg[i][u], rng.random()))[0] for i in range(N))
            p2 = "".join(sorted(U, key=lambda u: (-posg[i][u], rng.random()))[1] for i in range(N))
            return ["".join(od[:N]), p1, p2], {"most_overdue": od[:N]}
        if method == "Recurring Pairs":
            pc = Counter()
            for r in res[-90:]:
                for a, b in itertools.combinations(sorted(set(r)), 2): pc[a + b] += 1
            pairs = ranked(pc, [a + b for a, b in itertools.combinations(U, 2)])[:3]
            hot = ranked(freq, U); t = []
            for p in pairs:
                rest = [d for d in hot if d not in p][:N-2]; t.append(p + "".join(rest))
            return t, {"top_pairs": pairs}
    else:
        mains = [r["numbers"] for r in h]; bon = [r["bonus"] for r in h]
        U = list(range(1, g["main"] + 1)); B = list(range(1, g["bonus"] + 1))
        win = mains[-50:]; freq = Counter(x for m in win for x in m); bf = Counter(bon[-50:])
        if method == "Hot-Cold":
            hot = ranked(freq, U); cold = ranked(freq, U, reverse=False); hb = ranked(bf, B)
            t = [(sorted(hot[0:5]), hb[0]), (sorted(hot[5:10]), hb[1]), (sorted(hot[:3] + cold[:2]), ranked(bf, B, False)[0])]
            return t, {"window": len(win), "hot": hot[:10]}
        if method == "Historic Hot-Cold":
            af = Counter(x for m in mains for x in m); abf = Counter(bon)
            hot = ranked(af, U); cold = ranked(af, U, reverse=False)
            t = [(sorted(hot[:5]), ranked(abf, B)[0]), (sorted(cold[:5]), ranked(abf, B, False)[0]),
                 (sorted(hot[:3] + cold[:2]), ranked(abf, B)[1])]
            return t, {"window": "all %d draws" % len(mains), "hot": hot[:10], "cold": cold[:10]}
        if method == "Prime":
            isp = lambda n: n > 1 and all(n % k for k in range(2, int(n ** .5) + 1))
            P = [u for u in U if isp(u)]; PB = [b for b in B if isp(b)]
            af = Counter(x for m in mains for x in m)
            gp = gaps(mains, P); gb = gaps([[b] for b in bon], PB)
            recent = ranked(freq, P); alltime = ranked(af, P)
            od = sorted(P, key=lambda u: (-gp[u], rng.random())); ob = sorted(PB, key=lambda u: (-gb[u], rng.random()))
            t = [(sorted(recent[:5]), ranked(bf, PB)[0]), (sorted(alltime[:5]), ranked(Counter(bon), PB)[0]),
                 (sorted(od[:5]), ob[0])]
            return t, {"primes": P}
        if method == "Overdue":
            gp = gaps(mains, U); od = sorted(U, key=lambda u: (-gp[u], rng.random()))
            gb = gaps([[b] for b in bon], B); ob = sorted(B, key=lambda u: (-gb[u], rng.random()))
            t = [(sorted(od[i*5:(i+1)*5]), ob[i]) for i in range(3)]
            return t, {"most_overdue": od[:15]}
        if method == "Recurring Pairs":
            pc = Counter()
            for m in mains[-100:]:
                for a, b in itertools.combinations(sorted(m), 2): pc[(a, b)] += 1
            top = sorted(pc, key=lambda k: (-pc[k], rng.random()))[:6]
            hot = ranked(freq, U); hb = ranked(bf, B); t = []
            for i in range(3):
                s = set(top[2*i]) | set(top[2*i+1])
                for x in hot:
                    if len(s) >= 5: break
                    s.add(x)
                t.append((sorted(list(s)[:5]), hb[i]))
            return t, {"top_pairs": [list(p) for p in top]}
    return None, {}

# --------------------------------------------------------------------------
# PREDICT
# --------------------------------------------------------------------------
SYMBOLIC = ["I Ching", "Tarot", "Ifa", "Napoleon's Oraculum"]
STATISTICAL = ["Hot-Cold", "Historic Hot-Cold", "Prime", "Overdue", "Recurring Pairs"]

def fmt(game, t):
    if GAMES[game]["kind"] == "digits": return t
    m, b = t; return " ".join(f"{x:02d}" for x in m) + f" + {b:02d}"

def predict(game, date, draw, dream=None, only=None):
    g = GAMES[game]
    draw = draw or g["draws"][0]
    now = datetime.now(timezone.utc)
    entries = []
    deck = TarotDeck()
    casters = {"I Ching": cast_iching, "Tarot": deck.draw, "Ifa": cast_ifa, "Napoleon's Oraculum": cast_oraculum}
    use = lambda m: not only or m in only
    for m in SYMBOLIC:
        if not use(m): continue
        for k in range(PICKS_PER_METHOD):
            rec = []; t = build_ticket(game, casters[m], rec)
            entries.append(dict(method=m, ticket=t[0] if g["kind"] == "digits" else [t[0], t[1]], casting=rec))
    # Dream-Symbolic
    vals = dream_values(dream)
    if not use("Dream-Symbolic"): pass
    elif dream and vals:
        it = iter(vals * 50)  # reuse symbols in order if the dream is short
        for k in range(PICKS_PER_METHOD):
            rec = []
            def cast():
                v, w = next(it); return v, {"symbol": w, "value": v}
            t = build_ticket(game, cast, rec)
            entries.append(dict(method="Dream-Symbolic", ticket=t[0] if g["kind"] == "digits" else [t[0], t[1]], casting=rec))
    else:
        entries.append(dict(method="Dream-Symbolic", ticket=None, casting={"skipped": "no dream given" if not dream else "no table symbols in dream"}))
    for m in STATISTICAL:
        if not use(m): continue
        ts, info = stat_tickets(game, draw, m)
        if ts is None: entries.append(dict(method=m, ticket=None, casting=info)); continue
        if g["kind"] == "digits":  # fixed rule: a repeated ticket is rotated one place
            seen = []
            for i, t in enumerate(ts):
                for _ in range(g["n"]):
                    if t not in seen: break
                    t = t[1:] + t[0]
                seen.append(t); ts[i] = t
        for t in ts:
            entries.append(dict(method=m, ticket=t if g["kind"] == "digits" else [t[0], t[1]], casting=info))
    if g["kind"] == "lotto" and use("Unpopular Numbers"):
        # fixed rule: white balls drawn at random from 32..max (avoids birthday range 1-31);
        # bonus drawn at random from its upper half. Changes payout-sharing, not odds.
        for k in range(PICKS_PER_METHOD):
            t = [sorted(rng.sample(range(32, g["main"] + 1), 5)), rng.randint(g["bonus"] // 2 + 1, g["bonus"])]
            entries.append(dict(method="Unpopular Numbers", ticket=t, casting={"rule": "whites 32-max, bonus upper half"}))
    for k in range(PICKS_PER_METHOD if use("Random Control") else 0):
        if g["kind"] == "digits": t = "".join(str(secrets.randbelow(10)) for _ in range(g["n"]))
        else: t = [sorted(rng.sample(range(1, g["main"] + 1), 5)), secrets.randbelow(g["bonus"]) + 1]
        entries.append(dict(method="Random Control", ticket=t, casting={"rng": "secrets"}))
    batch = dict(game=game, date=date, draw=draw, methods_filter=only, locked_utc=now.isoformat(timespec="seconds"),
                 locked_et=now.astimezone(ET).strftime("%Y-%m-%d %I:%M:%S %p ET"),
                 dream=dream, entries=entries, prev_hash=last_hash())
    body = json.dumps(batch, sort_keys=True)
    batch["hash"] = hashlib.sha256(body.encode()).hexdigest()
    with open(PICKS, "a") as f: f.write(json.dumps(batch, sort_keys=True) + "\n")
    print(f"LOCKED {game.upper()} {date} {draw} at {batch['locked_et']}")
    print(f"Lock code: {batch['hash'][:16]}   (text this to yourself as outside proof)\n")
    cur = None
    for e in entries:
        if e["method"] != cur: cur = e["method"]; print(f"{cur}:")
        if e["ticket"] is None: print(f"   (skipped: {list(e['casting'].values())[0]})"); continue
        line = fmt(game, e["ticket"] if g["kind"] == "digits" else tuple(e["ticket"]))
        c = e["casting"]; note = ""
        if isinstance(c, list) and c:
            if "hexagram" in c[0]: note = ", ".join(f"Hex {x['hexagram']}" + (f" (lines {x['changing_lines']})" if x['changing_lines'] else "") for x in c[:3])
            elif "card" in c[0]: note = ", ".join(x["card"] + (" (R)" if x["reversed"] else "") for x in c[:3])
            elif "odu" in c[0]: note = ", ".join(x["odu"] for x in c[:3])
            elif "figure" in c[0]: note = ", ".join(f"Fig {x['figure']} {x['pattern']}" for x in c[:3])
            elif "symbol" in c[0]: note = ", ".join(x["symbol"] for x in c[:3])
            if len(c) > 3: note += ", ..."
        print(f"   {line}" + (f"   [{note}]" if note else ""))
    return batch

def last_hash():
    h = "GENESIS"
    if os.path.exists(PICKS):
        for line in open(PICKS):
            if line.strip(): h = json.loads(line)["hash"]
    return h

def verify():
    prev, n = "GENESIS", 0
    for line in open(PICKS):
        b = json.loads(line); h = b.pop("hash")
        ok = hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest() == h and b["prev_hash"] == prev
        if not ok: print(f"BROKEN at batch {n+1} ({b['game']} {b['date']} {b['draw']})"); return False
        prev, n = h, n + 1
    print(f"Chain OK: {n} locked batches, untouched."); return True

# --------------------------------------------------------------------------
# RESULTS & SCORING
# --------------------------------------------------------------------------
def load_results():
    if not os.path.exists(RESULTS): return []
    out = []
    for r in csv.DictReader(open(RESULTS)):
        g = GAMES[r["game"]]
        if g["kind"] == "digits": r["numbers"] = r["numbers"].zfill(g["n"])
        else: r["numbers"] = sorted(int(x) for x in r["numbers"].split())
        r["bonus"] = int(r["bonus"]) if r.get("bonus") not in (None, "") else None
        out.append(r)
    return out

def add_result(game, date, draw, numbers, bonus):
    g = GAMES[game]; draw = draw or g["draws"][0]
    new = not os.path.exists(RESULTS)
    with open(RESULTS, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(["game", "date", "draw", "numbers", "bonus"])
        w.writerow([game, date, draw, numbers, "" if bonus is None else bonus])
    print(f"Saved {game} {date} {draw}: {numbers}" + (f" bonus {bonus}" if bonus is not None else ""))

def score_pick3(p, r, wild):
    cnt = lambda s: Counter(s)
    pos = sum(a == b for a, b in zip(p, r)); com = sum((cnt(p) & cnt(r)).values())
    ws = wb = False
    if wild is not None:
        for i in range(len(r)):
            r2 = r[:i] + str(wild) + r[i+1:]
            ws |= p == r2; wb |= sorted(p) == sorted(r2)
    s = dict(straight=p == r, box=sorted(p) == sorted(r) and p != r,
             wild_straight=ws and p != r, wild_box=wb and not ws and sorted(p) != sorted(r),
             front_pair=p[:2] == r[:2], back_pair=p[-2:] == r[-2:], digits=com, positions=pos)
    s["any_win"] = s["straight"] or s["box"] or s["wild_straight"] or s["wild_box"] or (len(r) == 3 and (s["front_pair"] or s["back_pair"]))
    return s

def score_lotto(t, r_main, r_bonus):
    m = len(set(t[0]) & set(r_main)); b = t[1] == r_bonus
    prize = (m, b) in {(5,1),(5,0),(4,1),(4,0),(3,1),(3,0),(2,1),(1,1),(0,1)} or (b and m <= 2)
    return dict(white=m, bonus=b, any_win=bool(prize), tier=f"{m}" + ("+B" if b else ""))

def report(only=None):
    res = {(r["game"], r["date"], r["draw"]): r for r in load_results()}
    stats = {}
    if not os.path.exists(PICKS): print("No picks locked yet."); return
    for line in open(PICKS):
        b = json.loads(line)
        if only and b["game"] != only: continue
        r = res.get((b["game"], b["date"], b["draw"]))
        if not r: continue
        g = GAMES[b["game"]]
        for e in b["entries"]:
            if e["ticket"] is None: continue
            key = (b["game"], e["method"]); s = stats.setdefault(key, Counter()); s["tickets"] += 1
            if g["kind"] == "digits":
                sc = score_pick3(e["ticket"], r["numbers"], r["bonus"])
                for k, v in sc.items(): s[k] += int(v)
                s["two_plus_digits"] += sc["digits"] >= 2
            else:
                sc = score_lotto(e["ticket"], r["numbers"], r["bonus"])
                s["white_total"] += sc["white"]; s["bonus_hits"] += sc["bonus"]; s["any_win"] += sc["any_win"]
                s[f"tier_{sc['tier']}"] += 1
    if not stats: print("Nothing scored yet — add results with the 'result' command."); return
    for game in GAMES:
        rows = [(m, s) for (gm, m), s in stats.items() if gm == game]
        if not rows: continue
        print(f"\n=== {game.upper()} ===")
        if GAMES[game]["kind"] == "digits":
            print(f"{'Method':22}{'tix':>5}{'str':>5}{'box':>5}{'wildS':>6}{'wildB':>6}{'pair':>5}{'any':>5}{'2+dig':>6}{'avgDig':>7}")
            for m, s in sorted(rows):
                print(f"{m:22}{s['tickets']:>5}{s['straight']:>5}{s['box']:>5}{s['wild_straight']:>6}{s['wild_box']:>6}"
                      f"{s['front_pair']+s['back_pair']:>5}{s['any_win']:>5}{s['two_plus_digits']:>6}{s['digits']/s['tickets']:>7.2f}")
            if game == "pick4": print("Chance per ticket: avg digits shared 1.21; straight 0.01%. Pair columns are shown for interest only (not counted as Pick 4 wins).")
            else: print("Chance per ticket: any digit-match avg 0.73; 2+ digits ~13%; straight 0.1%; front/back pair 1% each.")
        else:
            print(f"{'Method':22}{'tix':>5}{'avgWhite':>9}{'bonus':>6}{'anyWin':>7}")
            for m, s in sorted(rows):
                print(f"{m:22}{s['tickets']:>5}{s['white_total']/s['tickets']:>9.3f}{s['bonus_hits']:>6}{s['any_win']:>7}")
            g = GAMES[game]
            print(f"Chance per ticket: avg white matches {5*5/g['main']:.3f}; bonus 1 in {g['bonus']}; any prize ~1 in 24.")
        print("Compare every method to 'Random Control'. Small samples swing a lot — judge after 30+ drawings.")

# --------------------------------------------------------------------------
# EXPORT — rows for the dashboard
# --------------------------------------------------------------------------
def export(outdir):
    res = {(r["game"], r["date"], r["draw"]): r for r in load_results()}
    stats, draws = {}, []
    if os.path.exists(PICKS):
        for line in open(PICKS):
            b = json.loads(line); g = GAMES[b["game"]]
            r = res.get((b["game"], b["date"], b["draw"]))
            if r: rs = r["numbers"] if g["kind"] == "digits" else " ".join(f"{x:02d}" for x in r["numbers"]) + f" + {r['bonus']:02d}"
            draws.append(dict(game=b["game"], date=b["date"], draw=b["draw"], locked_et=b["locked_et"],
                              lock_code=b["hash"][:16], methods=len({e["method"] for e in b["entries"] if e["ticket"] is not None}),
                              result=(rs + (f" WB {r['bonus']}" if g["kind"] == "digits" and r["bonus"] is not None else "")) if r else "",
                              status="scored" if r else "pending"))
            for e in b["entries"]:
                if e["ticket"] is None: continue
                k = (b["game"], e["method"]); s_ = stats.setdefault(k, Counter())
                if not r: s_["pending"] += 1; continue
                s_["tickets"] += 1; s_["draws_seen"] += 0
                if g["kind"] == "digits":
                    sc = score_pick3(e["ticket"], r["numbers"], r["bonus"])
                    s_["wins"] += sc["any_win"]; s_["match"] += sc["digits"]; s_["near"] += sc["digits"] >= 2
                else:
                    sc = score_lotto(e["ticket"], r["numbers"], r["bonus"])
                    s_["wins"] += sc["any_win"]; s_["match"] += sc["white"]; s_["near"] += sc["bonus"]
    rows = []
    for (game, m), c in sorted(stats.items()):
        t = c["tickets"]
        rows.append(dict(game=game, method=m, tickets=t, pending=c["pending"], wins=c["wins"],
                         avg_match=round(c["match"] / t, 3) if t else None, near=c["near"]))
    # expected per ticket under chance
    for r in rows:
        r["expected_avg_match"] = {"pick3": 0.73, "pick4": 1.21}.get(r["game"]) or round(25 / GAMES[r["game"]]["main"], 3)
    os.makedirs(outdir, exist_ok=True)
    json.dump(rows, open(os.path.join(outdir, "methods.json"), "w"), indent=1)
    draws.sort(key=lambda d: (d["date"], d["game"], d["draw"]), reverse=True)
    json.dump(draws, open(os.path.join(outdir, "draws.json"), "w"), indent=1)
    print(f"Exported {len(rows)} method rows and {len(draws)} batches to {outdir}")

# --------------------------------------------------------------------------
# RANDOMNESS AUDIT — the same kinds of tests used in published lottery studies.
# p-values come from simulating fair histories of the same length (no extra libraries).
# --------------------------------------------------------------------------
def audit(game, draw=None, sims=2000):
    g = GAMES[game]; h = history(game, draw)
    if len(h) < 20: print(f"Only {len(h)} results on file for {game}; load more history first."); return
    if g["kind"] == "digits":
        U = list(range(10)); N = g["n"]; draws = [[int(c) for c in r["numbers"]] for r in h]
        fair = lambda: [[secrets.randbelow(10) for _ in range(N)] for _ in draws]
        def stats(D):
            n = len(D); flat = [x for d in D for x in d]
            fc = Counter(flat); e = N * n / 10
            freq = sum((fc[u] - e) ** 2 / e for u in U)
            pos = sum(sum((Counter(d[i] for d in D)[u] - n / 10) ** 2 / (n / 10) for u in U) for i in range(N))
            pc = Counter(tuple(sorted(p)) for d in D for p in itertools.combinations(set(d), 2))
            pairmax = max(pc.values()) if pc else 0
            rep = sum(len(set(a) & set(b)) > 0 for a, b in zip(D, D[1:]))
            return dict(frequency=freq, positions=pos, top_pair=pairmax, repeats_from_last_draw=rep)
    else:
        U = list(range(1, g["main"] + 1)); draws = [r["numbers"] for r in h]
        fair = lambda: [sorted(rng.sample(U, 5)) for _ in draws]
        def stats(D):
            n = len(D); fc = Counter(x for d in D for x in d); e = 5 * n / g["main"]
            freq = sum((fc[u] - e) ** 2 / e for u in U)
            pc = Counter(p for d in D for p in itertools.combinations(sorted(d), 2))
            pairmax = max(pc.values()) if pc else 0
            rep = sum(len(set(a) & set(b)) > 0 for a, b in zip(D, D[1:]))
            consec = sum(any(b - a == 1 for a, b in zip(d, d[1:])) for d in D)
            return dict(frequency=freq, top_pair=pairmax, repeats_from_last_draw=rep, has_consecutive=consec)
    obs = stats(draws); sim = [stats(fair()) for _ in range(sims)]
    print(f"RANDOMNESS AUDIT — {game} {draw or ''} — {len(draws)} drawings, {sims} simulated fair histories\n")
    print(f"{'Test':26}{'Observed':>10}{'Fair avg':>10}{'p-value':>9}  Verdict")
    for k, v in obs.items():
        vals = [x[k] for x in sim]; avg = sum(vals) / len(vals)
        hi = sum(x >= v for x in vals) / sims; lo = sum(x <= v for x in vals) / sims
        p = min(1.0, 2 * min(hi, lo))
        verdict = "consistent with random" if p >= 0.05 else "UNUSUAL — check with more data"
        print(f"{k:26}{v:>10.1f}{avg:>10.1f}{p:>9.3f}  {verdict}")
    print("\nWith several tests, one p-value under 0.05 now and then is expected by luck alone.")

# --------------------------------------------------------------------------
def selftest():
    nums = sorted(v for row in KING_WEN for v in row); assert nums == list(range(1, 65)), "King Wen table"
    assert len(ODU_BY_PAT) == 16, "Odu patterns"
    assert king_wen([1]*6)[0] == 1 and king_wen([0]*6)[0] == 2 and king_wen([1,0,0,0,1,0])[0] == 3
    assert king_wen([0,1,0,0,0,1])[0] == 4 and king_wen([1,0,1,0,1,0])[0] == 63 and king_wen([0,1,0,1,0,1])[0] == 64
    assert score_pick3("314", "314", 9)["straight"]
    assert score_pick3("1234", "4321", 0)["box"] and score_pick3("1239", "1234", 9)["wild_straight"]
    assert score_pick3("279", "799", 2)["wild_box"]
    assert len(DECK) == 78
    print("Self-test passed.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Oracle Lab v2")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("predict"); p.add_argument("game", choices=GAMES); p.add_argument("date"); p.add_argument("draw", nargs="?"); p.add_argument("--dream"); p.add_argument("--methods", help="comma list, e.g. \"Prime,Historic Hot-Cold\"")
    r = sp.add_parser("result"); r.add_argument("game", choices=GAMES); r.add_argument("date"); r.add_argument("draw_or_numbers"); r.add_argument("numbers", nargs="?"); r.add_argument("--wild", type=int); r.add_argument("--bonus", type=int)
    q = sp.add_parser("report"); q.add_argument("game", nargs="?", choices=GAMES)
    sp.add_parser("verify"); sp.add_parser("selftest")
    ex = sp.add_parser("export"); ex.add_argument("outdir", nargs="?", default=os.path.join(HERE, "dashboard"))
    au = sp.add_parser("audit"); au.add_argument("game", choices=GAMES); au.add_argument("draw", nargs="?")
    a = ap.parse_args()
    if a.cmd == "predict": predict(a.game, a.date, a.draw, a.dream, a.methods.split(",") if a.methods else None)
    elif a.cmd == "result":
        if GAMES[a.game]["kind"] == "digits": add_result(a.game, a.date, a.draw_or_numbers, a.numbers, a.wild)
        else: add_result(a.game, a.date, None, a.draw_or_numbers, a.bonus)
    elif a.cmd == "report": report(a.game)
    elif a.cmd == "verify": verify()
    elif a.cmd == "audit": audit(a.game, a.draw)
    elif a.cmd == "export": export(a.outdir)
    else: selftest()
