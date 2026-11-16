import sys, calendar, csv, random, itertools, collections, datetime as dt, secrets
sys.path.insert(0,'.'); from p3_365 import EVE, DAY
R=random.Random(12345)
def expand(d):
    rows=[]
    for k,v in d.items():
        toks=v.split()
        if k=="2025-11-16": start=dt.date(2025,11,16); n=15
        else:
            y,m=map(int,k.split('-')); start=dt.date(y,m,1); n=calendar.monthrange(y,m)[1] if k!="2026-11" else 15
        assert len(toks)==n,(k,len(toks),n)
        for i,t in enumerate(toks):
            num,w=t.split('/'); assert len(num)==3 and len(w)==1
            rows.append((start+dt.timedelta(i),num,int(w)))
    rows.sort(); return rows
E=expand(EVE); D=expand(DAY); print("rows",len(D),len(E))
# cross-check with lab results.csv (ChatGPT-ledger seed + confirmed)
lab={(r['date'],r['draw']):(r['numbers'].zfill(3),r['bonus']) for r in csv.DictReader(open('/home/claude/lab/results.csv')) if r['game']=='pick3'}
mm=0;tot=0;bad=[]
for name,rows in (('Day',D),('Evening',E)):
    for d,n,w in rows:
        k=(str(d),name)
        if k in lab:
            tot+=1
            if lab[k][0]!=n or (lab[k][1] not in (None,'') and int(lab[k][1])!=w): mm+=1; bad.append((k,lab[k],(n,w)))
print("crosscheck",tot,"mismatch",mm, bad[:12])
# combined sequence chronological: day then evening
seq=[]
for (d1,n1,w1),(d2,n2,w2) in zip(D,E): assert d1==d2; seq+= [(d1,'Day',n1,w1),(d2,'Evening',n2,w2)]
draws=[[int(c) for c in s[2]] for s in seq]; N=len(draws)
def fair(n): return [[R.randrange(10) for _ in range(3)] for _ in range(n)]
def stats(Ds, W=None):
    n=len(Ds); out={}
    flat=collections.Counter(x for d in Ds for x in d); e=3*n/10
    out['digit_chi2']=sum((flat[u]-e)**2/e for u in range(10))
    out['pos_chi2']=sum(sum((collections.Counter(d[i] for d in Ds)[u]-n/10)**2/(n/10) for u in range(10)) for i in range(3))
    out['doubles']=sum(len(set(d))==2 for d in Ds); out['triples']=sum(len(set(d))==1 for d in Ds)
    pc=collections.Counter(p for d in Ds for p in itertools.combinations(sorted(set(d)),2)); out['top_pair']=max(pc.values())
    oc=collections.Counter(tuple(d[:2]) for d in Ds); out['top_front_pair']=max(oc.values())
    sums=[sum(d) for d in Ds]; out['mean_sum']=sum(sums)/n
    out['repeat_prev']=sum(len(set(a)&set(b))>0 for a,b in zip(Ds,Ds[1:]))
    out['exact_repeat_any']=n-len(set(tuple(d) for d in Ds))
    # hot predictive: share of next draw digits in top3 of last 30
    hits=0;cnt=0
    for i in range(30,n):
        c=collections.Counter(x for d in Ds[i-30:i] for x in d); hot=set(sorted(range(10),key=lambda u:(-c[u],u))[:3])
        hits+=sum(x in hot for x in Ds[i]); cnt+=3
    out['hot30_hit_rate']=hits/cnt
    # overdue predictive: share of next digits among 3 longest-absent
    hits=0;cnt=0
    for i in range(30,n):
        last={u:-1 for u in range(10)}
        for j in range(i):
            for x in Ds[j]: last[x]=j
        od=set(sorted(range(10),key=lambda u:(last[u],u))[:3]); hits+=sum(x in od for x in Ds[i]); cnt+=3
    out['overdue_hit_rate']=hits/cnt
    return out
obs=stats(draws)
SIMS=1000
sims=[stats(fair(N)) for _ in range(SIMS)]
print(f"\nCOMBINED Day+Evening, {N} drawings")
for k,v in obs.items():
    vals=[s[k] for s in sims]; avg=sum(vals)/SIMS
    hi=sum(x>=v for x in vals)/SIMS; lo=sum(x<=v for x in vals)/SIMS; p=min(1,2*min(hi,lo))
    print(f"{k:18}{v:10.3f}{avg:10.3f}  p={p:.3f}")
flat=collections.Counter(x for d in draws for x in d); print("\ndigit counts",[flat[u] for u in range(10)], "expected",3*N/10)
for i in range(3): print("pos",i+1,[collections.Counter(d[i] for d in draws)[u] for u in range(10)])
pc=collections.Counter(p for d in draws for p in itertools.combinations(sorted(set(d)),2)); print("top pairs",pc.most_common(6), "expected per pair ~",round(sum(pc.values())/45,1))
wb=collections.Counter(s[3] for s in seq); print("wild ball counts",[wb[u] for u in range(10)])
# day of week
dow=collections.defaultdict(collections.Counter)
for s in seq:
    for c in s[2]: dow[s[0].weekday()][int(c)]+=1
# day vs evening separately
for name,rows in (('Day',D),('Evening',E)):
    o=stats([[int(c) for c in r[1]] for r in rows]); print(name, {k:round(v,3) for k,v in o.items() if k in('digit_chi2','pos_chi2','doubles','triples','mean_sum')})
# Day->same-day Evening carry
carry=sum(len(set(a[1])&set(b[1]))>0 for a,b in zip(D,E)); print("day->evening shares a digit",carry,"of",len(D))
# repeats of exact numbers
nums=collections.Counter(s[2] for s in seq); print("most repeated numbers",nums.most_common(8))
# runs: same digit three times (triples)
print("triples",[ (str(s[0]),s[1],s[2]) for s in seq if len(set(s[2]))==1])
