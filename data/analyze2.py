import sys, calendar, random, itertools, collections, datetime as dt
sys.path.insert(0,'.'); from p3_365 import EVE, DAY; from p3_y2 import EVE2, DAY2
R=random.Random(7)
def expand(d):
    rows=[]
    for k,v in d.items():
        toks=v.split(); p=k.split('-')
        if len(p)==3: start=dt.date(*map(int,p)); n=15
        else:
            y,m=map(int,p); start=dt.date(y,m,1); n=calendar.monthrange(y,m)[1]
            if (y,m) in ((2026,11),(2025,11)): n=15
        assert len(toks)==n,(k,len(toks),n)
        for i,t in enumerate(toks):
            num,w=(t.split('/') if '/' in t else (t[:3],t[3]))
            assert len(num)==3 and len(w)==1 and num.isdigit() and w.isdigit(),t
            rows.append((start+dt.timedelta(i),num,int(w)))
    return sorted(rows)
D=expand(DAY2)+expand(DAY); E=expand(EVE2)+expand(EVE)
dates=[r[0] for r in D]; assert dates==[r[0] for r in E]; assert all((b-a).days==1 for a,b in zip(dates,dates[1:])),"gap"
print("days",len(D),dates[0],"to",dates[-1])
seq=[]
for (d,n1,w1),(_,n2,w2) in zip(D,E): seq+=[(d,'Day',n1,w1),(d,'Evening',n2,w2)]
draws=[[int(c) for c in s[2]] for s in seq]; N=len(draws)
def fair(n): return [[R.randrange(10) for _ in range(3)] for _ in range(n)]
def stats(Ds):
    n=len(Ds); o={}
    f=collections.Counter(x for d in Ds for x in d); e=3*n/10
    o['digit_balance']=sum((f[u]-e)**2/e for u in range(10))
    o['position_balance']=sum(sum((collections.Counter(d[i] for d in Ds)[u]-n/10)**2/(n/10) for u in range(10)) for i in range(3))
    o['doubles']=sum(len(set(d))==2 for d in Ds); o['triples']=sum(len(set(d))==1 for d in Ds)
    pc=collections.Counter(p for d in Ds for p in itertools.combinations(sorted(set(d)),2)); o['top_pair']=max(pc.values())
    o['top_exact_number']=max(collections.Counter(tuple(d) for d in Ds).values())
    o['mean_sum']=sum(map(sum,Ds))/n
    o['share_with_prev']=sum(len(set(a)&set(b))>0 for a,b in zip(Ds,Ds[1:]))
    # predictive tests
    h=c=0; od=0; last={u:-1 for u in range(10)}
    for i,d in enumerate(Ds):
        if i>=30:
            cc=collections.Counter(x for q in Ds[i-30:i] for x in q)
            hot=set(sorted(range(10),key=lambda u:(-cc[u],u))[:3]); ov=set(sorted(range(10),key=lambda u:(last[u],u))[:3])
            h+=sum(x in hot for x in d); od+=sum(x in ov for x in d); c+=3
        for x in d: last[x]=i
    o['hot30_next']=h/c; o['overdue_next']=od/c
    return o
def report(name,Ds,S=600):
    obs=stats(Ds); sims=[stats(fair(len(Ds))) for _ in range(S)]
    print(f"\n{name}: {len(Ds)} drawings")
    for k,v in obs.items():
        vals=[s[k] for s in sims]; avg=sum(vals)/S; p=min(1,2*min(sum(x>=v for x in vals),sum(x<=v for x in vals))/S)
        print(f"  {k:18}{v:9.3f}{avg:9.3f}  p={p:.3f}")
report("TWO YEARS combined",draws)
half=N//2; Y1,Y2=draws[:half],draws[half:]
# out-of-sample: year-1 patterns -> year 2
f1=collections.Counter(x for d in Y1 for x in d); hot=[u for u,_ in f1.most_common(3)]; cold=[u for u,_ in f1.most_common()[-3:]]
print("\nYEAR 1 -> YEAR 2 (out of sample)")
print("  year-1 hottest digits",hot,"share in year 2:",round(sum(x in hot for d in Y2 for x in d)/(3*len(Y2)),3),"(chance 0.300)")
print("  year-1 coldest digits",cold,"share in year 2:",round(sum(x in cold for d in Y2 for x in d)/(3*len(Y2)),3))
pc1=collections.Counter(p for d in Y1 for p in itertools.combinations(sorted(set(d)),2)); tp=[p for p,_ in pc1.most_common(5)]
pc2=collections.Counter(p for d in Y2 for p in itertools.combinations(sorted(set(d)),2))
print("  year-1 top 5 pairs",tp,"-> year-2 counts",[pc2[p] for p in tp],"avg pair",round(sum(pc2.values())/45,1))
for i in range(3):
    t=collections.Counter(d[i] for d in Y1).most_common(1)[0][0]; print(f"  position {i+1}: year-1 top digit {t} -> year-2 rate {sum(d[i]==t for d in Y2)/len(Y2):.3f} (chance 0.100)")
n1=collections.Counter(tuple(d) for d in Y1); tn=[k for k,_ in n1.most_common(5)]; n2=collections.Counter(tuple(d) for d in Y2)
print("  year-1 most repeated numbers",["".join(map(str,k))+f"({n1[k]})" for k in tn],"-> year-2 counts",[n2[k] for k in tn],"(chance ~0.73)")
# correlation between year1 and year2 digit freqs
import statistics as st
a=[f1[u] for u in range(10)]; f2=collections.Counter(x for d in Y2 for x in d); b=[f2[u] for u in range(10)]
print("  digit counts y1",a); print("  digit counts y2",b)
ma,mb=st.mean(a),st.mean(b); r=sum((x-ma)*(y-mb) for x,y in zip(a,b))/((sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))**.5); print("  correlation y1 vs y2 digit frequency:",round(r,2))
# monthly carryover over 24 months
months=collections.defaultdict(list)
for s,d in zip(seq,draws): months[(s[0].year,s[0].month)].append(d)
ks=sorted(months); hh=tt=0
for a_,b_ in zip(ks,ks[1:]):
    c=collections.Counter(x for d in months[a_] for x in d); top=[u for u,_ in c.most_common(3)]
    hh+=sum(x in top for d in months[b_] for x in d); tt+=3*len(months[b_])
print(f"\nMONTH -> NEXT MONTH over {len(ks)-1} months: hot-3 share {hh/tt:.3f} (chance 0.300)")
wb=collections.Counter(s[3] for s in seq); print("wild ball counts",[wb[u] for u in range(10)],"expected",N/10)
