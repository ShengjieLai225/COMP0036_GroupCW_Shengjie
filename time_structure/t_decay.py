"""T3 (time-decay half-life) and T4 (extra down-weighting across season boundaries) for a Poisson
attack/defence model (Maher 1982 / Dixon-Coles 1997 weighting, independent Poisson, no rho),
evaluated walk-forward with weekly refits at forecast horizons of 0 and 42 days (V7).

usage: python3 -I time_structure/t_decay.py cleaning/out/matches_clean.csv time_structure/out
"""
import sys, json, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import poisson

src, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
d = pd.read_csv(src, parse_dates=['Date']).sort_values(['Date', 'match_id']).reset_index(drop=True)
d['y'] = d.FTR.map({'H': 0, 'D': 1, 'A': 2}).to_numpy()
day = ((d.Date - pd.Timestamp('2000-01-01')).dt.days).to_numpy()
season = d.season.to_numpy()
WINDOW = 4 * 365            # training window (days before the data cut-off)
RIDGE = 1.0                 # L2 penalty on attack/defence (identifiability + teams with few matches)
EVAL = list(range(2010, 2027))
G = np.arange(11)
PMF = None

def fit(idx, w, teams):
    """weighted Poisson: log mu_h = c + h + a_i - b_j ; log mu_a = c + a_j - b_i"""
    k = {t: i for i, t in enumerate(teams)}; n = len(teams)
    hi = np.array([k[t] for t in d.HomeTeam.to_numpy()[idx]]); ai = np.array([k[t] for t in d.AwayTeam.to_numpy()[idx]])
    m = len(idx); p = 2 + 2 * n
    X = np.zeros((2 * m, p)); r = np.arange(m)
    X[:, 0] = 1; X[:m, 1] = 1
    X[r, 2 + hi] = 1; X[r, 2 + n + ai] = -1
    X[m + r, 2 + ai] = 1; X[m + r, 2 + n + hi] = -1
    y = np.r_[d.FTHG.to_numpy()[idx], d.FTAG.to_numpy()[idx]].astype(float)
    ww = np.r_[w, w]
    P = np.ones(p); P[:2] = 0
    beta = np.zeros(p); beta[0] = np.log(max(y.mean(), 0.1))
    for _ in range(25):
        mu = np.exp(X @ beta)
        g = X.T @ (ww * (y - mu)) - RIDGE * P * beta
        Hm = (X * (ww * mu)[:, None]).T @ X + np.diag(RIDGE * P)
        step = np.linalg.solve(Hm, g); beta += step
        if np.abs(step).max() < 1e-6:
            break
    return beta, k, n

def probs(beta, k, n, home, away):
    c, h = beta[0], beta[1]; att, de = beta[2:2 + n], beta[2 + n:]
    # teams with no data in the window (promoted after a long absence): weakest third of the league
    strength = att + de          # higher = better (de enters as -de for the opponent)
    weak = np.argsort(strength)[: max(3, n // 3)]
    fa, fd = att[weak].mean(), de[weak].mean()
    A = lambda t: att[k[t]] if t in k else fa
    Dd = lambda t: de[k[t]] if t in k else fd
    lh = np.exp(c + h + np.array([A(t) for t in home]) - np.array([Dd(t) for t in away]))
    la = np.exp(c + np.array([A(t) for t in away]) - np.array([Dd(t) for t in home]))
    ph, pa = poisson.pmf(G[None, :], lh[:, None]), poisson.pmf(G[None, :], la[:, None])
    M = ph[:, :, None] * pa[:, None, :]
    pH = np.tril(np.ones((11, 11)), -1)[None] * M; pD = np.eye(11)[None] * M
    PH, PD = pH.sum((1, 2)), pD.sum((1, 2))
    tot = M.sum((1, 2))
    return np.c_[PH, PD, tot - PH - PD] / tot[:, None]

def rps(P, y):
    O = np.eye(3)[y]; c = np.cumsum(P, 1) - np.cumsum(O, 1)
    return (c[:, :2] ** 2).sum(1) / 2

def run(hl, horizon, delta=1.0):
    """per-match RPS for EVAL seasons; refit every 7 days on data older than (refit day - horizon)"""
    res = np.full(len(d), np.nan)
    for s in EVAL:
        ms = np.where(season == s)[0]
        start, end = day[ms].min(), day[ms].max()
        for t0 in range(start, end + 1, 7):
            te = ms[(day[ms] >= t0) & (day[ms] < t0 + 7)]
            if len(te) == 0:
                continue
            cut = t0 - horizon
            tr = np.where((day < cut) & (day >= cut - WINDOW))[0]
            age = cut - day[tr]
            w = np.ones(len(tr)) if hl is None else 0.5 ** (age / hl)
            if delta != 1.0:
                cut_season = season[np.searchsorted(day, cut, side='right') - 1]
                w = w * delta ** (cut_season - season[tr])
            teams = sorted(set(d.HomeTeam.to_numpy()[tr]) | set(d.AwayTeam.to_numpy()[tr]))
            beta, k, n = fit(tr, w, teams)
            P = probs(beta, k, n, d.HomeTeam.to_numpy()[te], d.AwayTeam.to_numpy()[te])
            res[te] = rps(P, d.y[te])
    return res

def boot_diff(a, b, n=2000, seed=0):
    m = np.isfinite(a) & np.isfinite(b)
    df = pd.DataFrame(dict(day=day[m], x=(a - b)[m])).groupby('day').x.agg(['sum', 'size'])
    rng = np.random.default_rng(seed); S, N = df['sum'].to_numpy(), df['size'].to_numpy()
    bs = [(lambda i: S[i].sum() / N[i].sum())(rng.integers(0, len(S), len(S))) for _ in range(n)]
    return [round(float((a - b)[m].mean()), 5), round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)]

if __name__ == '__main__':
    R = {}
    HL = [60, 90, 120, 180, 270, 365, 540, 730, None]
    cache = {}
    t1 = time.time()
    for hz in [0, 42]:
        for hl in HL:
            cache[(hz, hl, 1.0)] = run(hl, hz)
        print('horizon', hz, 'done', round(time.time() - t1), 's', flush=True)
    for hz in [0, 42]:
        for hl in [180, 365, None]:
            for delta in [0.8, 0.6, 0.4]:
                cache[(hz, hl, delta)] = run(hl, hz, delta)
    print('delta done', round(time.time() - t1), 's', flush=True)

    jan = (d.Date.dt.month == 1).to_numpy()
    rows = []
    for (hz, hl, dl), r in cache.items():
        rows.append(dict(horizon=hz, half_life=('inf' if hl is None else hl), delta=dl, rps=np.nanmean(r),
                         rps_jan=np.nanmean(r[jan]), n=int(np.isfinite(r).sum())))
    T = pd.DataFrame(rows); T.to_csv(out / 'T3_half_life_grid.csv', index=False)
    R['grid'] = T.round(5).to_dict('records')
    for hz in [0, 42]:
        sub = {k: v for k, v in cache.items() if k[0] == hz and k[2] == 1.0}
        best = min(sub, key=lambda k: np.nanmean(sub[k]))
        R[f'h{hz}_best'] = str(best)
        R[f'h{hz}_best_vs_inf'] = boot_diff(sub[best], sub[(hz, None, 1.0)])
        R[f'h{hz}_best_vs_180'] = boot_diff(sub[best], sub[(hz, 180, 1.0)])
        R[f'h{hz}_best_vs_60'] = boot_diff(sub[best], sub[(hz, 60, 1.0)])
        # per-season optimum
        per = {}
        for s in EVAL:
            m = season == s
            sc = {('inf' if k[1] is None else k[1]): float(np.nanmean(v[m])) for k, v in sub.items()}
            per[s] = min(sc, key=sc.get)
        R[f'h{hz}_best_per_season'] = per
        # nested: choose half-life on previous evaluation seasons only
        nested = np.full(len(d), np.nan); ch = {}
        for s in EVAL[2:]:
            past = (season >= EVAL[0]) & (season < s)
            kbest = min(sub, key=lambda k: np.nanmean(sub[k][past])); ch[s] = 'inf' if kbest[1] is None else kbest[1]
            nested[season == s] = sub[kbest][season == s]
        R[f'h{hz}_nested_choice'] = ch
        R[f'h{hz}_nested_vs_inf'] = boot_diff(nested, sub[(hz, None, 1.0)])
        R[f'h{hz}_nested_vs_180'] = boot_diff(nested, sub[(hz, 180, 1.0)])
        for hl in [180, 365, None]:
            for dl in [0.8, 0.6, 0.4]:
                R[f'h{hz}_hl{hl}_delta{dl}_vs_delta1'] = boot_diff(cache[(hz, hl, dl)], cache[(hz, hl, 1.0)])
    # cost of the forecast horizon at the best half-lives
    b0 = eval(R['h0_best']); b42 = eval(R['h42_best'])
    R['horizon_cost_best'] = boot_diff(cache[b42], cache[b0])
    json.dump(R, open(out / 't_decay_results.json', 'w'), indent=1, default=str)
    print(T.round(5).to_string())
    print(json.dumps({k: v for k, v in R.items() if k != 'grid'}, indent=1, default=str))
