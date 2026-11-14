"""E6: manager changes vs EPL results (2000/01-2026/27 to 8 Nov 2026).
usage: python3 -I e6_manager.py mgr.txt epl-training.csv E0_2627.csv outdir

mgr.txt = text of the Wikipedia PDF "List of Premier League managers" (version 'up to date as of
8 November 2026', printed 2026-11-10), extracted with pypdf 7.0:
    '\n\n=====PAGE=====\n'.join(p.extract_text() for p in pypdf.PdfReader(pdf).pages)
E0_2627.csv = https://www.football-data.co.uk/mmz4281/2627/E0.csv (downloaded 2026-11-10, 100 matches).
Elo: published elofootball/eloratings method, K=20, H=100, goal-difference multiplier, no season regression.
"""
import re, sys, unicodedata, json
import numpy as np, pandas as pd

mtxt, ftrain, f2627, out = sys.argv[1:5]
rng = np.random.default_rng(0)

# ---------- 1. parse Wikipedia manager table ----------
lines = [unicodedata.normalize('NFKC', l) for l in open(mtxt).read().splitlines()]
D = r'(\d{1,2} [A-Z][a-z]+ \d{4})'
pat = re.compile(r'^\s*(.+?) ' + D + r'(?:\[\w+\])?\s+(?:' + D + r'|(Present\*?))(?:\[\w+\])?\s+(\d+)')
rows = []
for i, l in enumerate(lines):
    if i > 1450:  # later tables are summary stats
        break
    m = pat.match(l)
    if not m:
        continue
    club, name = m.group(1).strip(), lines[i - 1].strip()
    if club == 'Wanderers' and lines[i - 1].strip() == 'Wolverhampton':
        club, name = 'Wolverhampton Wanderers', lines[i - 2].strip()
    rows.append(dict(name=re.sub(r'[‡†§]', '', name).strip(), club=club,
                     caretaker=int('‡' in name), incumbent=int('†' in name),
                     start=pd.to_datetime(m.group(2), format='%d %B %Y'),
                     end=pd.to_datetime(m.group(3) or '8 November 2026', format='%d %B %Y')))
M = pd.DataFrame(rows)
MAP = {'Birmingham City': 'Birmingham', 'Blackburn Rovers': 'Blackburn', 'Bolton Wanderers': 'Bolton',
       'Bradford City': 'Bradford', 'Brighton & Hove Albion': 'Brighton', 'Cardiff City': 'Cardiff',
       'Charlton Athletic': 'Charlton', 'Coventry City': 'Coventry', 'Derby County': 'Derby',
       'Huddersfield Town': 'Huddersfield', 'Hull City': 'Hull', 'Ipswich Town': 'Ipswich',
       'Leeds United': 'Leeds', 'Leicester City': 'Leicester', 'Luton Town': 'Luton',
       'Manchester City': 'Man City', 'Manchester United': 'Man United', 'Newcastle United': 'Newcastle',
       'Norwich City': 'Norwich', 'Nottingham Forest': "Nott'm Forest", 'Queens Park Rangers': 'QPR',
       'Stoke City': 'Stoke', 'Swansea City': 'Swansea', 'Tottenham Hotspur': 'Tottenham',
       'West Bromwich Albion': 'West Brom', 'West Ham United': 'West Ham', 'Wigan Athletic': 'Wigan',
       'Wolverhampton Wanderers': 'Wolves'}
M['team'] = M.club.map(lambda c: MAP.get(c, c))
M.to_csv(f'{out}/managers_parsed.csv', index=False)

# ---------- 2. matches + Elo (published method, K=20, H=100) ----------
a = pd.read_csv(ftrain).dropna(subset=['HomeTeam'])
a['Date'] = pd.to_datetime(a.Date, dayfirst=True)
b = pd.read_csv(f2627)[['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']]
b['Date'] = pd.to_datetime(b.Date, dayfirst=True)
G = pd.concat([a[b.columns], b]).sort_values('Date', kind='stable').reset_index(drop=True)
G['season'] = G.Date.dt.year - (G.Date.dt.month < 7)
teams_pl = set(G.HomeTeam) | set(G.AwayTeam)
unmatched_wiki = sorted(t for t in teams_pl if t not in set(M.team))
print('PL teams with no manager rows:', unmatched_wiki)

K, H = 20.0, 100.0
def gmul(n):
    return 1.0 if n <= 1 else 1.5 if n == 2 else (11 + n) / 8
R, prev_rel = {}, []
recs = []
for s, gs in G.groupby('season', sort=True):
    tm = set(gs.HomeTeam) | set(gs.AwayTeam)
    init = np.mean(prev_rel) if prev_rel else 1500.0
    for t in tm - set(R):
        R[t] = init
    for _, r in gs.iterrows():
        h, w = r.HomeTeam, r.AwayTeam
        e = 1 / (1 + 10 ** (-(R[h] + H - R[w]) / 400))
        sh = {'H': 1.0, 'D': 0.5, 'A': 0.0}[r.FTR]
        recs.append((r.Date, s, h, w, 1, sh - e, e, sh, {'H': 3, 'D': 1, 'A': 0}[r.FTR], R[h]))
        recs.append((r.Date, s, w, h, 0, e - sh, 1 - e, 1 - sh, {'H': 0, 'D': 1, 'A': 3}[r.FTR], R[w]))
        dlt = K * gmul(abs(r.FTHG - r.FTAG)) * (sh - e)
        R[h] += dlt; R[w] -= dlt
    # relegated = bottom 3 by points this season (complete seasons only)
    pts = {}
    for _, r in gs.iterrows():
        pts[r.HomeTeam] = pts.get(r.HomeTeam, 0) + {'H': 3, 'D': 1, 'A': 0}[r.FTR]
        pts[r.AwayTeam] = pts.get(r.AwayTeam, 0) + {'H': 0, 'D': 1, 'A': 3}[r.FTR]
    if len(gs) == 380:
        prev_rel = [R[t] for t in sorted(pts, key=pts.get)[:3]]
T = pd.DataFrame(recs, columns=['date', 'season', 'team', 'opp', 'home', 'resid', 'exp', 'score', 'pts', 'rating'])
T = T.sort_values(['team', 'date']).reset_index(drop=True)
T['k'] = T.groupby(['team', 'season']).cumcount()          # match index within season
T['n'] = T.groupby(['team', 'season']).date.transform('size')

# ---------- 3. mid-season departures of permanent managers ----------
span = T.groupby(['team', 'season']).date.agg(['min', 'max']).reset_index()
ev = []
for _, m in M[(M.caretaker == 0)].iterrows():
    d = m.end
    if m.incumbent:
        continue
    sp = span[(span.team == m.team) & (span['min'] < d) & (span['max'] > d)]
    if len(sp) == 0:
        continue
    s = int(sp.season.iloc[0])
    tt = T[(T.team == m.team) & (T.season == s)]
    nb, na = (tt.date <= d).sum(), (tt.date > d).sum()
    if nb >= 3 and na >= 3:
        ev.append(dict(team=m.team, season=s, date=d, manager=m['name'], before=nb, after=na))
E = pd.DataFrame(ev).drop_duplicates(['team', 'date'])
E.to_csv(f'{out}/midseason_departures.csv', index=False)
print('mid-season departures 2000/01-2026/27:', len(E))
print(E.groupby('season').size().to_string())

# per-event windows (within same season, league matches only)
W = 10
win = []
for j, e in E.iterrows():
    tt = T[(T.team == e.team) & (T.season == e.season)].reset_index(drop=True)
    pos = (tt.date <= e.date).sum()  # first post-change match index
    for i in range(len(tt)):
        rel = i - pos + (1 if i >= pos else 0)  # ...,-2,-1 | 1,2,...
        if -W <= rel <= W and rel != 0:
            win.append(dict(ev=j, rel=rel, **tt.loc[i, ['resid', 'pts', 'exp', 'score']].to_dict()))
Wd = pd.DataFrame(win)
prof = Wd.groupby('rel').agg(n=('resid', 'size'), resid=('resid', 'mean'), ppg=('pts', 'mean'), exp=('exp', 'mean'))
prof.to_csv(f'{out}/event_profile.csv')

def blk(lo, hi):
    x = Wd[(Wd.rel >= lo) & (Wd.rel <= hi)].groupby('ev')[['resid', 'pts', 'exp']].mean()
    return x
pre, post = blk(-6, -1), blk(1, 6)
post10 = blk(1, 10)

# ---------- 4. matched control: same slump, no change ----------
# rolling 6-match residual sum (within season) BEFORE match i; exclude team-seasons within +-10 matches of any change
T['pre6'] = T.groupby(['team', 'season']).resid.transform(lambda x: x.shift(1).rolling(6).mean())
T['post6'] = T.groupby(['team', 'season']).resid.transform(lambda x: x[::-1].rolling(6).mean()[::-1])
T['post10'] = T.groupby(['team', 'season']).resid.transform(lambda x: x[::-1].rolling(10).mean()[::-1])
T['ppg_post6'] = T.groupby(['team', 'season']).pts.transform(lambda x: x[::-1].rolling(6).mean()[::-1])
T['ppg_pre6'] = T.groupby(['team', 'season']).pts.transform(lambda x: x.shift(1).rolling(6).mean())
T['rank'] = 0
excl = set()
for _, e in E.iterrows():
    for i in T.index[(T.team == e.team) & (T.season == e.season) & ((T.date - e.date).abs() < pd.Timedelta(days=120))]:
        excl.add(i)
C = T[~T.index.isin(excl) & T.pre6.notna() & T.post6.notna() & (T.season <= 2025)]
# treated rows: first post-change match
tr = []
for _, e in E.iterrows():
    tt = T[(T.team == e.team) & (T.season == e.season) & (T.date > e.date)]
    tr.append(tt.index[0])
Tr = T.loc[tr]
Tr = Tr[Tr.pre6.notna() & Tr.post6.notna()]
# nearest-neighbour on (pre6 residual, pre6 ppg, k) with 5 controls each
ctrl_post, ctrl_ppg = [], []
Z = C[['pre6', 'ppg_pre6', 'k']].to_numpy(float)
sc = Z.std(0)
for _, r in Tr.iterrows():
    dist = (((Z - r[['pre6', 'ppg_pre6', 'k']].to_numpy(float)) / sc) ** 2).sum(1)
    idx = np.argsort(dist)[:5]
    ctrl_post.append(C.post6.to_numpy()[idx].mean()); ctrl_ppg.append(C.ppg_post6.to_numpy()[idx].mean())
Tr = Tr.assign(ctrl_post6=ctrl_post, ctrl_ppg_post6=ctrl_ppg)
diff = Tr.post6 - Tr.ctrl_post6
boot = [rng.choice(diff.to_numpy(), len(diff)).mean() for _ in range(5000)]

res = dict(
    n_events=int(len(E)), n_events_matched=int(len(Tr)),
    pre6_resid=float(pre.resid.mean()), post6_resid=float(post.resid.mean()), post10_resid=float(post10.resid.mean()),
    pre6_ppg=float(pre.pts.mean()), post6_ppg=float(post.pts.mean()),
    pre6_exp=float(pre.exp.mean()), post6_exp=float(post.exp.mean()),
    treated_post6_resid=float(Tr.post6.mean()), control_post6_resid=float(Tr.ctrl_post6.mean()),
    did=float(diff.mean()), did_ci=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
    treated_post6_ppg=float(Tr.ppg_post6.mean()), control_post6_ppg=float(Tr.ctrl_ppg_post6.mean()),
    treated_pre6_resid=float(Tr.pre6.mean()), all_matches_resid_sd=float(T.resid.std()),
)

# ---------- 5. summer changes: new manager at season start ----------
def mgr_at(team, d):
    x = M[(M.team == team) & (M.start <= d) & (M.end >= d)]
    if len(x) == 0:
        return None
    x = x.sort_values(['caretaker', 'start'], ascending=[False, False])
    return x['name'].iloc[0]
S = T.groupby(['team', 'season']).agg(first=('date', 'min'), last=('date', 'max'), r0=('rating', 'first')).reset_index()
S['mgr_first'] = [mgr_at(t, d) for t, d in zip(S.team, S['first'])]
S = S.sort_values(['team', 'season'])
S['prev_season'] = S.groupby('team').season.shift(1)
S['prev_last'] = S.groupby('team')['last'].shift(1)
S['mgr_prev_last'] = [mgr_at(t, d) if pd.notna(d) else None for t, d in zip(S.team, S.prev_last)]
S = S[(S.prev_season == S.season - 1) & S.mgr_first.notna() & S.mgr_prev_last.notna()].copy()
S['new_mgr'] = (S.mgr_first != S.mgr_prev_last).astype(int)
# early-season residual (first 10 matches) and rating drift over the season
first10 = T[T.k < 10].groupby(['team', 'season']).resid.mean().rename('res10')
absres10 = T[T.k < 10].groupby(['team', 'season']).resid.apply(lambda x: abs(x.mean())).rename('absres10')
S = S.join(first10, on=['team', 'season']).join(absres10, on=['team', 'season'])
endR = T.groupby(['team', 'season']).rating.last()
S['dR'] = [endR.get((t, s), np.nan) - r for t, s, r in zip(S.team, S.season, S.r0)]
S = S[S.season <= 2025]
S.to_csv(f'{out}/summer_changes.csv', index=False)
g = S.groupby('new_mgr').agg(n=('team', 'size'), res10=('res10', 'mean'), absres10=('absres10', 'mean'),
                             sd_dR=('dR', 'std'), mean_absdR=('dR', lambda x: x.abs().mean()))
print(g)
# permutation test for |dR| difference
x1, x0 = S[S.new_mgr == 1].dR.abs().to_numpy(), S[S.new_mgr == 0].dR.abs().to_numpy()
obs = x1.mean() - x0.mean(); allv = np.r_[x1, x0]
perm = [(lambda p: p[:len(x1)].mean() - p[len(x1):].mean())(rng.permutation(allv)) for _ in range(5000)]
res['summer'] = g.reset_index().to_dict('records')
res['summer_absdR_diff'] = float(obs); res['summer_absdR_p'] = float(np.mean(np.abs(perm) >= abs(obs)))
y1, y0 = S[S.new_mgr == 1].absres10.to_numpy(), S[S.new_mgr == 0].absres10.to_numpy()
obs2 = y1.mean() - y0.mean(); allv = np.r_[y1, y0]
perm = [(lambda p: p[:len(y1)].mean() - p[len(y1):].mean())(rng.permutation(allv)) for _ in range(5000)]
res['summer_absres10_diff'] = float(obs2); res['summer_absres10_p'] = float(np.mean(np.abs(perm) >= abs(obs2)))

# ---------- 6. timing: how many mid-season departures fall 8 Nov - 30 Jan; per season ----------
E['md'] = E.date.dt.strftime('%m-%d')
inwin = E[(E.md >= '11-09') | (E.md <= '01-30')]
inwin = inwin[(inwin.date.dt.month >= 11) | (inwin.date.dt.month == 1)]
res['per_season_mean'] = float(E[E.season <= 2025].groupby('season').size().reindex(range(2000, 2026), fill_value=0).mean())
seasons_w = inwin[inwin.season <= 2025].groupby('season').size().reindex(range(2000, 2026), fill_value=0)
res['window_nov9_jan30_mean'] = float(seasons_w.mean()); res['window_share_ge1'] = float((seasons_w >= 1).mean())
win2 = E[(E.date.dt.month == 12) & (E.date.dt.day >= 21) | (E.date.dt.month == 1) & (E.date.dt.day <= 30)]
sw2 = win2[win2.season <= 2025].groupby('season').size().reindex(range(2000, 2026), fill_value=0)
res['window_dec21_jan30_mean'] = float(sw2.mean()); res['window_dec21_jan30_share_ge1'] = float((sw2 >= 1).mean())

# ---------- 7. 2026/27 status ----------
cur = M[M.incumbent == 1][['team', 'name', 'start']].copy()
cur['tenure_days_30jan27'] = (pd.Timestamp('2027-01-30') - cur.start).dt.days
cur['new_since_summer_2026'] = (cur.start >= '2026-05-01').astype(int)
r27 = T[T.season == 2026].groupby('team').agg(n=('resid', 'size'), resid=('resid', 'mean'), ppg=('pts', 'mean'))
cur = cur.join(r27, on='team').sort_values('start')
cur.to_csv(f'{out}/current_2026_27.csv', index=False)
res['r27_new'] = float(T[(T.season == 2026) & T.team.isin(cur[cur.new_since_summer_2026 == 1].team)].resid.mean())
res['r27_old'] = float(T[(T.season == 2026) & T.team.isin(cur[cur.new_since_summer_2026 == 0].team)].resid.mean())
json.dump(res, open(f'{out}/e6_results.json', 'w'), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
print(prof.round(3).to_string())
print(cur.to_string())
