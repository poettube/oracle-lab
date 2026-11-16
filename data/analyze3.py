import sys, calendar, random, itertools, collections, datetime as dt
sys.path.insert(0,'.'); from p3_365 import EVE, DAY; from p3_y2 import EVE2, DAY2; from p3_y3 import EVE3, DAY3
R=random.Random(7)
def expand(d):
    rows=[]
    for k,v in d.items():
        toks=v.split(); p=k.split('-')
        if len(p)==3: start=dt.date(*map(int,p)); n=15
        else:
            y,m=map(int,p); start=dt.date(y,m,1); n=calendar.monthrange(y,m)[1]
            if (y,m) in ((2026,11),(2025,11),(2024,11)): n=15
        assert len(toks)==n,(k,len(toks),n)
        for i,t in enumerate(toks):
            num,w=(t.split('/') if '/' in t else (t[:3],t[3]))
            assert len(num)==3 and len(w)==1 and num.isdigit() and w.isdigit(),t
            rows.append((start+dt.timedelta(i),num,int(w)))
    return sorted(rows)
D=expand(DAY3)+expand(DAY2)+expand(DAY); E=expand(EVE3)+expand(EVE2)+expand(EVE)
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
report("THREE YEARS combined",draws)

b1,b2=dt.date(2024,11,16),dt.date(2025,11,16)
Y=[[d for s_,d in zip(seq,draws) if s_[0]<b1],[d for s_,d in zip(seq,draws) if b1<=s_[0]<b2],[d for s_,d in zip(seq,draws) if s_[0]>=b2]]
print("year sizes",[len(y) for y in Y])
print("\nYEAR -> NEXT YEAR (out of sample)")
import statistics as st
for a,b,lab in ((Y[0],Y[1],"Y1->Y2"),(Y[1],Y[2],"Y2->Y3"),(Y[0]+Y[1],Y[2],"Y1+Y2->Y3")):
    f1=collections.Counter(x for d in a for x in d); hot=[u for u,_ in f1.most_common(3)]; cold=[u for u,_ in f1.most_common()[-3:]]
    pc1=collections.Counter(p for d in a for p in itertools.combinations(sorted(set(d)),2)); tp=[p for p,_ in pc1.most_common(5)]
    pc2=collections.Counter(p for d in b for p in itertools.combinations(sorted(set(d)),2))
    f2=collections.Counter(x for d in b for x in d); A=[f1[u] for u in range(10)]; B=[f2[u] for u in range(10)]
    ma,mb=st.mean(A),st.mean(B); r=sum((x-ma)*(y-mb) for x,y in zip(A,B))/((sum((x-ma)**2 for x in A)*sum((y-mb)**2 for y in B))**.5)
    pos=[sum(d[i]==collections.Counter(q[i] for q in a).most_common(1)[0][0] for d in b)/len(b) for i in range(3)]
    print(f"  {lab}: hot{hot} {sum(x in hot for d in b for x in d)/(3*len(b)):.3f} | cold{cold} {sum(x in cold for d in b for x in d)/(3*len(b)):.3f} | top5 pairs avg {sum(pc2[p] for p in tp)/5:.1f} vs {sum(pc2.values())/45:.1f} | pos-top {[round(x,3) for x in pos]} | digit corr {r:.2f}")
for i,y in enumerate(Y): 
    f=collections.Counter(x for d in y for x in d); print(f"  year {i+1} digit counts",[f[u] for u in range(10)])
months=collections.defaultdict(list)
for s_,d in zip(seq,draws): months[(s_[0].year,s_[0].month)].append(d)
ks=sorted(months); hh=tt=0
for a_,b_ in zip(ks,ks[1:]):
    c=collections.Counter(x for d in months[a_] for x in d); top=[u for u,_ in c.most_common(3)]
    hh+=sum(x in top for d in months[b_] for x in d); tt+=3*len(months[b_])
print(f"\nMONTH -> NEXT MONTH over {len(ks)-1} months: hot-3 share {hh/tt:.3f} (chance 0.300)")
for i,y in enumerate(Y):
    o=stats(y); print(f"  year {i+1}: overdue_next {o['overdue_next']:.3f}  hot30_next {o['hot30_next']:.3f}")
wb=collections.Counter(s_[3] for s_ in seq); print("wild ball counts",[wb[u] for u in range(10)],"expected",N/10)
