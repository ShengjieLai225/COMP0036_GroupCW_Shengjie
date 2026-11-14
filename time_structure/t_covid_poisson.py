"""T2 for the Poisson model: how should the closed-doors matches (17 Jun 2020 - 16 May 2021) be treated
when they fall inside the training window?  half-life 270 days, horizon 0, weekly refits.
usage: python3 -I time_structure/t_covid_poisson.py cleaning/out/matches_clean.csv time_structure/out
"""
import sys, json, importlib.util
from pathlib import Path
import numpy as np
spec = importlib.util.spec_from_file_location('t_decay', Path(__file__).with_name('t_decay.py'))
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)   # reads the same argv
d, day, season = T.d, T.day, T.season
closed = d.Date.between('2020-06-17', '2021-05-16').to_numpy()

def fit_z(idx, w, teams, z):
    k = {t: i for i, t in enumerate(teams)}; n = len(teams)
    hi = np.array([k[t] for t in d.HomeTeam.to_numpy()[idx]]); ai = np.array([k[t] for t in d.AwayTeam.to_numpy()[idx]])
    m = len(idx); p = 3 + 2 * n
    X = np.zeros((2 * m, p)); r = np.arange(m)
    X[:, 0] = 1; X[:m, 1] = 1; X[:m, 2] = z          # extra home effect for closed-doors matches
    X[r, 3 + hi] = 1; X[r, 3 + n + ai] = -1; X[m + r, 3 + ai] = 1; X[m + r, 3 + n + hi] = -1
    y = np.r_[d.FTHG.to_numpy()[idx], d.FTAG.to_numpy()[idx]].astype(float); ww = np.r_[w, w]
    P = np.ones(p); P[:3] = 0
    if z.sum() == 0:
        P[2] = 1e6                                       # not identified -> pinned at 0
    beta = np.zeros(p); beta[0] = np.log(y.mean())
    for _ in range(25):
        mu = np.exp(X @ beta)
        g = X.T @ (ww * (y - mu)) - T.RIDGE * P * beta
        Hm = (X * (ww * mu)[:, None]).T @ X + np.diag(T.RIDGE * P)
        st = np.linalg.solve(Hm, g); beta += st
        if np.abs(st).max() < 1e-6:
            break
    return beta, k, n

def run(mode, hl=270):
    res = np.full(len(d), np.nan); hz = []
    for s in range(2019, 2026):
        ms = np.where(season == s)[0]
        for t0 in range(day[ms].min(), day[ms].max() + 1, 7):
            te = ms[(day[ms] >= t0) & (day[ms] < t0 + 7)]
            if len(te) == 0:
                continue
            tr = np.where((day < t0) & (day >= t0 - T.WINDOW))[0]
            w = 0.5 ** ((t0 - day[tr]) / hl)
            z = closed[tr].astype(float)
            if mode == 'exclude':
                w = w * (1 - z)
            zz = z if mode == 'indicator' else np.zeros_like(z)
            beta, k, n = fit_z(tr, w, sorted(set(d.HomeTeam.to_numpy()[tr]) | set(d.AwayTeam.to_numpy()[tr])), zz)
            b = np.r_[beta[0], beta[1] + beta[2] * closed[te].mean(), beta[3:]]   # predict with closed status of test week
            P = T.probs(b, k, n, d.HomeTeam.to_numpy()[te], d.AwayTeam.to_numpy()[te])
            res[te] = T.rps(P, d.y[te]); hz.append((t0, beta[1], beta[2]))
    return res, hz

R = {}; cache = {}
for mode in ['normal', 'exclude', 'indicator']:
    cache[mode], hz = run(mode)
    R[f'{mode}_home_param_first_week_2021_22'] = [round(float(x), 4) for x in
        min((h for h in hz if h[0] >= day[season == 2021].min()), key=lambda h: h[0])[1:]]
during = closed; after = season >= 2021
for mode, r in cache.items():
    R[mode] = dict(during=round(float(np.nanmean(r[during])), 5), after_2021_22_to_2025_26=round(float(np.nanmean(r[after])), 5),
                   first_half_2021_22=round(float(np.nanmean(r[(season == 2021) & (d.Date.dt.month >= 8).to_numpy()])), 5))
for mode in ['exclude', 'indicator']:
    R[f'{mode}_vs_normal_after'] = T.boot_diff(np.where(after, cache[mode], np.nan), np.where(after, cache['normal'], np.nan))
    R[f'{mode}_vs_normal_during'] = T.boot_diff(np.where(during, cache[mode], np.nan), np.where(during, cache['normal'], np.nan))
json.dump(R, open(T.out / 't_covid_poisson_results.json', 'w'), indent=1)
print(json.dumps(R, indent=1))
