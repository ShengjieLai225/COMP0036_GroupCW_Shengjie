"""T5: is the higher January draw rate real information beyond Elo?  Ordered logit with a
draw-band width that may differ in January / over Christmas, evaluated walk-forward (5-season fits).
usage: python3 -I time_structure/t_jan_draw.py cleaning/out/matches_clean.csv time_structure/out
"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
src, out = Path(sys.argv[1]), Path(sys.argv[2])
d = pd.read_csv(src, parse_dates=['Date']).sort_values(['Date', 'match_id']).reset_index(drop=True)
y = d.FTR.map({'H': 0, 'D': 1, 'A': 2}).to_numpy()
H, K, LAM = 65.0, 15.0, 0.9          # best Elo setting from t_elo.py
rating, pts, last, rel = {}, {}, None, []
D = np.empty(len(d))
for i, r in enumerate(d.itertuples(index=False)):
    if r.season != last:
        if last is not None:
            mu = np.mean([rating[t] for t in pts])
            for t in pts:
                rating[t] = LAM * rating[t] + (1 - LAM) * mu
            if len(pts) == 20:
                rel = [rating[t] for t in sorted(pts, key=pts.get)[:3]]
        pts, last = {}, r.season
    for t in (r.HomeTeam, r.AwayTeam):
        rating.setdefault(t, np.mean(rel) if rel else 1500.0)
    D[i] = rating[r.HomeTeam] + H - rating[r.AwayTeam]
    e = 1 / (1 + 10 ** (-D[i] / 400)); n = abs(r.FTHG - r.FTAG)
    g = 1.0 if n <= 1 else 1.5 if n == 2 else (11 + n) / 8
    dl = K * g * ((2 - y[i]) / 2 - e); rating[r.HomeTeam] += dl; rating[r.AwayTeam] -= dl
    pts[r.HomeTeam] = pts.get(r.HomeTeam, 0) + (3, 1, 0)[y[i]]; pts[r.AwayTeam] = pts.get(r.AwayTeam, 0) + (0, 1, 3)[y[i]]

m = d.Date.dt.month.to_numpy(); dd = d.Date.dt.day.to_numpy()
FEAT = {'jan': (m == 1).astype(float),
        'xmas': (((m == 12) & (dd >= 20)) | ((m == 1) & (dd <= 5))).astype(float),
        'march': (m == 3).astype(float)}
def pr(p, x, z):
    b, t1, g, gz = p; t2 = t1 - np.exp(g + gz * z)    # z widens/narrows the draw band
    a1, a2 = expit(b * x - t1), expit(b * x - t2)
    return np.c_[a1, a2 - a1, 1 - a2].clip(1e-12)
def fit(x, yy, z, use):
    f = lambda p: -np.log(pr(np.r_[p[:3], p[3] if use else 0.0], x, z)[np.arange(len(yy)), yy]).sum()
    return np.r_[minimize(f, [0.005, 0.0, -0.5, 0.0], method='L-BFGS-B').x[:3], 0.0] if not use else \
        minimize(f, [0.005, 0.0, -0.5, 0.0], method='L-BFGS-B').x
def score(P, yy):
    O = np.eye(3)[yy]; c = np.cumsum(P, 1) - np.cumsum(O, 1)
    return (c[:, :2] ** 2).sum(1) / 2, -np.log(P[np.arange(len(yy)), yy])
R = {}
for name, z in FEAT.items():
    res = {k: (np.full(len(d), np.nan), np.full(len(d), np.nan)) for k in ['base', 'with']}
    coefs = []
    for s in range(2005, 2027):
        tr = ((d.season >= s - 5) & (d.season < s)).to_numpy(); te = (d.season == s).to_numpy()
        for k, use in [('base', False), ('with', True)]:
            p = fit(D[tr], y[tr], z[tr], use)
            if use: coefs.append(p[3])
            a, b = score(pr(p, D[te], z[te]), y[te]); res[k][0][te] = a; res[k][1][te] = b
    sel = z == 1
    diff = res['with'][0] - res['base'][0]
    days = d.Date.to_numpy()
    df = pd.DataFrame(dict(day=days, x=diff)).dropna().groupby('day').x.agg(['sum', 'size'])
    rng = np.random.default_rng(0); S, N = df['sum'].to_numpy(), df['size'].to_numpy()
    bs = [(lambda i: S[i].sum() / N[i].sum())(rng.integers(0, len(S), len(S))) for _ in range(2000)]
    R[name] = dict(n_feature_matches=int(np.isfinite(diff[sel]).sum()), mean_gz=round(float(np.mean(coefs)), 3),
                   rps_base=round(float(np.nanmean(res['base'][0])), 5), rps_with=round(float(np.nanmean(res['with'][0])), 5),
                   rps_diff_all=[round(float(np.nanmean(diff)), 6), round(float(np.percentile(bs, 2.5)), 6), round(float(np.percentile(bs, 97.5)), 6)],
                   rps_diff_on_feature_matches=round(float(np.nanmean(diff[sel])), 5),
                   logloss_diff_all=round(float(np.nanmean(res['with'][1] - res['base'][1])), 5),
                   pred_draw_base_on_feature=round(float(np.nanmean(pr(fit(D, y, z, False), D, z)[sel, 1])), 4),
                   actual_draw_on_feature=round(float((y[sel & (d.season <= 2026).to_numpy()] == 1).mean()), 4))
json.dump(R, open(out / 't_jan_draw_results.json', 'w'), indent=1); print(json.dumps(R, indent=1))
