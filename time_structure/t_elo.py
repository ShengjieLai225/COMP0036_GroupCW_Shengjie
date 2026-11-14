"""Time structure (T1, T2, T4, T5, T6): descriptive statistics + Elo experiments.

usage: python3 -I time_structure/t_elo.py cleaning/out/matches_clean.csv time_structure/out
Elo = published elofootball/eloratings method (K, H, goal-difference multiplier G), extended with
season shrinkage lambda; probabilities from an ordered logit on d = R_h + H - R_a fitted on the
5 seasons before each evaluation season (walk-forward, no look-ahead).
"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

src, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
d = pd.read_csv(src, parse_dates=['Date']).sort_values(['Date', 'match_id']).reset_index(drop=True)
d['y'] = d.FTR.map({'H': 0, 'D': 1, 'A': 2})
R = {}

# closed doors: Project Restart 17 Jun 2020 -> 16 May 2021 (2,000 fans in some grounds 2-30 Dec 2020 ignored;
# up to 10,000 from 17 May 2021, i.e. the last two rounds, counted as crowds)
d['closed'] = d.Date.between('2020-06-17', '2021-05-16').astype(int)

# ------------------------------------------------------------------ T1 / T2 descriptive
full = d[d.season <= 2026]
per = full.groupby('season_label').agg(n=('y', 'size'), H=('y', lambda x: (x == 0).mean()), D=('y', lambda x: (x == 1).mean()),
                                       A=('y', lambda x: (x == 2).mean()), hg=('FTHG', 'mean'), ag=('FTAG', 'mean'))
per['gd'] = per.hg - per.ag
per['log_goal_ratio'] = np.log(per.hg / per.ag)
per['home_pts_share'] = (3 * per.H + per.D) / (3 * per.H + 3 * per.A + 2 * per.D)
per.to_csv(out / 'T1_home_adv_by_season.csv')
R['T1_per_season'] = per.round(4).reset_index().to_dict('records')
s = d[(d.season <= 2025)].copy()
for flag, g in s.groupby('closed'):
    R[f'T2_closed{flag}'] = dict(n=len(g), H=round((g.y == 0).mean(), 4), D=round((g.y == 1).mean(), 4),
                                 A=round((g.y == 2).mean(), 4), gd=round((g.FTHG - g.FTAG).mean(), 3),
                                 log_goal_ratio=round(np.log(g.FTHG.mean() / g.FTAG.mean()), 3),
                                 shots_diff=round((g.HS - g.AS).mean(), 2), yellow_diff=round((g.HY - g.AY).mean(), 3),
                                 fouls_diff=round((g.HF - g.AF).mean(), 2))
# trend in home advantage (seasons with crowds only), OLS with season index
sea = per.reset_index(); sea['yr'] = sea.season_label.str[:4].astype(int)
fit = sea[(sea.yr <= 2025) & (sea.yr != 2020)]
for col in ['H', 'gd', 'log_goal_ratio']:
    X = np.c_[np.ones(len(fit)), fit.yr - 2000]; b, *_ = np.linalg.lstsq(X, fit[col], rcond=None)
    resid = fit[col] - X @ b; se = np.sqrt(resid.var(ddof=2) * np.linalg.inv(X.T @ X)[1, 1])
    R[f'T1_trend_{col}_per_decade'] = [round(10 * b[1], 4), round(10 * se, 4)]
# how well do simple rules predict next season's home-win rate / goal ratio (seasons with crowds)?
rules = {}
for col in ['H', 'log_goal_ratio']:
    err = {k: [] for k in ['all_history', 'last3', 'last5', 'ewm_hl3', 'trend']}
    for i, row in fit.iterrows():
        past = fit[fit.yr < row.yr]
        if len(past) < 5:
            continue
        v = past[col].to_numpy(); t = past.yr.to_numpy()
        w = 0.5 ** ((t.max() - t) / 3)
        X = np.c_[np.ones(len(t)), t]; b, *_ = np.linalg.lstsq(X, v, rcond=None)
        pred = dict(all_history=v.mean(), last3=v[-3:].mean(), last5=v[-5:].mean(), ewm_hl3=(w * v).sum() / w.sum(),
                    trend=b[0] + b[1] * row.yr)
        for k, p in pred.items():
            err[k].append(abs(p - row[col]))
    rules[col] = {k: round(float(np.mean(e)), 4) for k, e in err.items()}
R['T1_next_season_MAE'] = rules
# team-specific home advantage: is it more than noise? (per team: home ppg - away ppg, seasons 2016-2025)
rec = d[(d.season.between(2016, 2025)) & (d.closed == 0)]
hp = rec.assign(p=rec.y.map({0: 3, 1: 1, 2: 0})).groupby('HomeTeam').p.agg(['mean', 'size', 'var'])
ap = rec.assign(p=rec.y.map({0: 0, 1: 1, 2: 3})).groupby('AwayTeam').p.agg(['mean', 'size', 'var'])
t = hp.add_suffix('_h').join(ap.add_suffix('_a')); t = t[(t.size_h >= 57)]
t['ha'] = t.mean_h - t.mean_a; t['se2'] = t.var_h / t.size_h + t.var_a / t.size_a
R['T1_team_HA'] = dict(n_teams=len(t), var_observed=round(t.ha.var(), 4), mean_sampling_var=round(t.se2.mean(), 4),
                       share_true_var=round(max(0, 1 - t.se2.mean() / t.ha.var()), 3))

# ------------------------------------------------------------------ T5 / T6 descriptive
s = d[(d.season <= 2025) & (d.closed == 0)].copy()
s['month'] = s.Date.dt.month
s['rnd'] = s.groupby('season').cumcount() // 10 + 1         # approx round number
s['phase'] = pd.cut(s.rnd, [0, 5, 18, 33, 38], labels=['R1-5', 'R6-18', 'R19-33', 'R34-38'])
s['xmas'] = ((s.Date.dt.month == 12) & (s.Date.dt.day >= 20) | (s.Date.dt.month == 1) & (s.Date.dt.day <= 5)).astype(int)
s['dow'] = s.Date.dt.day_name().str[:3]
def summ(g):
    return pd.Series(dict(n=len(g), H=(g.y == 0).mean(), D=(g.y == 1).mean(), A=(g.y == 2).mean(),
                          goals=(g.FTHG + g.FTAG).mean()))
for key in ['month', 'phase', 'xmas', 'dow']:
    tab = s.groupby(key, observed=True).apply(summ, include_groups=False)
    tab.to_csv(out / f'T56_by_{key}.csv'); R[f'T56_by_{key}'] = tab.round(4).reset_index().to_dict('records')

# ------------------------------------------------------------------ Elo engine
def gmul(n):
    return np.where(n <= 1, 1.0, np.where(n == 2, 1.5, (11 + n) / 8))

def run_elo(K=20.0, H=100.0, lam=1.0, covid='normal', H_closed=0.0):
    """returns pre-match d (with H) and per-team rating history for horizon look-ups"""
    rating, hist = {}, {}
    last_season, rel_prev = None, []
    D = np.empty(len(d)); Dn = np.empty(len(d))
    pts = {}
    for i, r in enumerate(d.itertuples(index=False)):
        if r.season != last_season:
            if last_season is not None:   # end of season: relegated teams' average for newcomers
                mean = np.mean([rating[t] for t in pts])
                for t in pts:            # season shrinkage toward the league mean of last season
                    rating[t] = lam * rating[t] + (1 - lam) * mean
                if len(pts) == 20:
                    rel_prev = [rating[t] for t in sorted(pts, key=pts.get)[:3]]
            pts, last_season = {}, r.season
        for t in (r.HomeTeam, r.AwayTeam):
            if t not in rating:
                rating[t] = np.mean(rel_prev) if rel_prev else 1500.0
                hist[t] = ([], [])
        h = H_closed if (covid == 'adjust' and r.closed) else H
        dd = rating[r.HomeTeam] + h - rating[r.AwayTeam]
        D[i] = dd; Dn[i] = rating[r.HomeTeam] - rating[r.AwayTeam]
        if not (covid == 'skip' and r.closed):
            e = 1 / (1 + 10 ** (-dd / 400)); sh = (2 - r.y) / 2
            delta = K * gmul(abs(r.FTHG - r.FTAG)) * (sh - e)
            rating[r.HomeTeam] += delta; rating[r.AwayTeam] -= delta
        for t in (r.HomeTeam, r.AwayTeam):
            hist[t][0].append(r.Date.value); hist[t][1].append(rating[t])
        pts[r.HomeTeam] = pts.get(r.HomeTeam, 0) + (3, 1, 0)[r.y]
        pts[r.AwayTeam] = pts.get(r.AwayTeam, 0) + (0, 1, 3)[r.y]
    return D, Dn, {t: (np.array(a), np.array(b)) for t, (a, b) in hist.items()}

def d_at_horizon(hist, H, days):
    """d using ratings as they stood `days` before kick-off (V7 forecast horizon)"""
    out_ = np.full(len(d), np.nan)
    for i, r in enumerate(d.itertuples(index=False)):
        cut = (r.Date - pd.Timedelta(days=days)).value
        v = []
        for t in (r.HomeTeam, r.AwayTeam):
            ts, rs = hist[t]; j = np.searchsorted(ts, cut, side='right') - 1
            v.append(rs[j] if j >= 0 else np.nan)
        out_[i] = v[0] + H - v[1]
    return out_

def ologit_fit(x, y, z=None):
    """P(H)=s(b x + c z - t1), P(H or D)=s(b x + c z - t2); z = optional closed-doors indicator"""
    z = np.zeros_like(x) if z is None else z
    def nll(p):
        b, c, t1, g = p; t2 = t1 - np.exp(g)
        a1, a2 = expit(b * x + c * z - t1), expit(b * x + c * z - t2)
        pr = np.c_[a1, a2 - a1, 1 - a2].clip(1e-12)
        return -np.log(pr[np.arange(len(y)), y]).sum()
    return minimize(nll, [0.004, 0.0, 0.0, -0.5], method='L-BFGS-B').x

def ologit_pred(p, x, z=None):
    z = np.zeros_like(x) if z is None else z
    b, c, t1, g = p; t2 = t1 - np.exp(g)
    a1, a2 = expit(b * x + c * z - t1), expit(b * x + c * z - t2)
    return np.c_[a1, a2 - a1, 1 - a2]

def rps(P, y):
    O = np.eye(3)[y]; c = np.cumsum(P, 1) - np.cumsum(O, 1)
    return (c[:, :2] ** 2).sum(1) / 2

EVAL = list(range(2005, 2027))        # 2026 = 2026/27 so far
def walk_forward(D, z=None, horizon_mask=None, train_D=None):
    """per-match RPS for evaluation seasons; ordered logit refit on the 5 previous seasons"""
    train_D = D if train_D is None else train_D
    out_ = np.full(len(d), np.nan)
    for s_ in EVAL:
        tr = (d.season >= s_ - 5) & (d.season < s_) & np.isfinite(train_D)
        te = (d.season == s_) & np.isfinite(D)
        if horizon_mask is not None:
            te &= horizon_mask
        zz = None if z is None else z[tr]
        p = ologit_fit(train_D[tr], d.y[tr].to_numpy(), zz)
        out_[te] = rps(ologit_pred(p, D[te], None if z is None else z[te]), d.y[te].to_numpy())
    return out_

def boot_diff(a, b, n=2000, seed=0):
    """paired bootstrap over match-days (dates), mean(a-b) and 95% CI"""
    m = np.isfinite(a) & np.isfinite(b)
    df = pd.DataFrame(dict(day=d.Date[m].to_numpy(), x=(a - b)[m])).groupby('day').x.agg(['sum', 'size'])
    rng = np.random.default_rng(seed); S, N = df['sum'].to_numpy(), df['size'].to_numpy()
    bs = [(lambda i: S[i].sum() / N[i].sum())(rng.integers(0, len(S), len(S))) for _ in range(n)]
    return [round(float((a - b)[m].mean()), 5), round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)]

# baseline: frequency model (last 5 seasons' H/D/A shares)
base = np.full(len(d), np.nan)
for s_ in EVAL:
    tr, te = (d.season >= s_ - 5) & (d.season < s_), d.season == s_
    f = np.bincount(d.y[tr], minlength=3) / tr.sum()
    base[te] = rps(np.tile(f, (te.sum(), 1)), d.y[te].to_numpy())
R['baseline_freq_rps'] = round(float(np.nanmean(base)), 5)

# ------------------------------------------------------------------ T4: K x lambda grid
grid = []
cache = {}
early = d.groupby('season').cumcount().to_numpy() < 100   # first 10 rounds
for H in [65.0, 100.0]:
  for K in [15, 20, 25]:
    for lam in [1.0, 0.9, 0.8, 0.7, 0.6]:
        D, Dn, hist = run_elo(K=K, H=H, lam=lam)
        r_ = walk_forward(D)
        grid.append(dict(H=H, K=K, lam=lam, rps=float(np.nanmean(r_)), rps_first10=float(np.nanmean(r_[early])),
                         rps_rest=float(np.nanmean(r_[~early]))))
        cache[(H, K, lam)] = (r_, D, hist)
G = pd.DataFrame(grid); G.to_csv(out / 'T4_K_lambda_grid.csv', index=False)
R['T4_grid'] = G.round(5).to_dict('records')
best = G.loc[G.rps.idxmin()]; R['T4_best'] = best.to_dict()
r_best = cache[(best.H, best.K, best.lam)][0]; r_l1 = cache[(best.H, best.K, 1.0)][0]
R['T4_best_vs_lam1_same_K'] = boot_diff(r_best, r_l1)
# selection inside walk-forward (nested): choose (K,lam) on seasons < s, evaluate on s
nested = np.full(len(d), np.nan); chosen = {}
for s_ in EVAL[3:]:
    past = d.season.between(EVAL[0], s_ - 1).to_numpy()
    sc = {k: np.nanmean(v[0][past]) for k, v in cache.items()}
    kbest = min(sc, key=sc.get); chosen[s_] = kbest
    nested[d.season == s_] = cache[kbest][0][d.season == s_]
R['T4_nested_choice'] = {str(k): list(v) for k, v in chosen.items()}
R['T4_nested_rps'] = round(float(np.nanmean(nested)), 5)
R['T4_nested_vs_published_H100K20lam1'] = boot_diff(nested, cache[(100.0, 20, 1.0)][0])
R['T4_best_vs_published'] = boot_diff(r_best, cache[(100.0, 20, 1.0)][0])

# ------------------------------------------------------------------ T2: covid treatments (best K, lambda)
Hb, Kb, lb = float(best.H), float(best.K), float(best.lam)
cov = {}
for name, kw in [('normal', {}), ('adjust_H0', dict(covid='adjust', H_closed=0.0)), ('skip', dict(covid='skip'))]:
    D, Dn, hist = run_elo(K=Kb, H=Hb, lam=lb, **kw)
    cov[name] = walk_forward(D)
z = d.closed.to_numpy().astype(float)
D, Dn, hist = run_elo(K=Kb, H=Hb, lam=lb, covid='adjust', H_closed=0.0)
cov['adjust_H0+indicator_in_ologit'] = walk_forward(D, z=z)
after = (d.season >= 2021).to_numpy(); during = d.closed.to_numpy() == 1
R['T2_rps'] = {k: dict(all=round(float(np.nanmean(v)), 5), during_closed=round(float(np.nanmean(v[during])), 5),
                       after_2021=round(float(np.nanmean(v[after])), 5)) for k, v in cov.items()}
R['T2_adjust_vs_normal_after2021'] = boot_diff(np.where(after, cov['adjust_H0'], np.nan), np.where(after, cov['normal'], np.nan))
R['T2_adjust_vs_normal_during'] = boot_diff(np.where(during, cov['adjust_H0'], np.nan), np.where(during, cov['normal'], np.nan))
# estimated home advantage in Elo points: fit H by max likelihood of the ologit using Dn and closed indicator
tr = d.season.between(2015, 2025).to_numpy()
p = ologit_fit(Dn[tr], d.y[tr].to_numpy(), z[tr])
R['T2_ologit_closed_coef'] = dict(b=float(p[0]), c=float(p[1]), closed_effect_in_elo_points=float(p[1] / p[0]))
# home advantage in Elo points by season: ologit on Dn per season (threshold midpoint / b)
hpts = {}
for s_ in range(2000, 2027):
    m = (d.season == s_).to_numpy()
    if s_ < 2026 and m.sum() < 300:
        continue
    q = ologit_fit(Dn[m], d.y[m].to_numpy())
    hpts[s_] = round(float(-(q[2] + (q[2] - np.exp(q[3]))) / 2 / q[0]), 1)
R['T1_home_adv_elo_points_by_season'] = hpts

# ------------------------------------------------------------------ V7 x T5: forecast horizon 42 days, by month
r0, Db, hist = cache[(best.H, best.K, best.lam)]
D42 = d_at_horizon(hist, Hb, 42)
same_season_mask = np.isfinite(D42) & (d.Date - pd.Timedelta(days=42) >= d.groupby('season').Date.transform('min')).to_numpy()
r42 = walk_forward(D42, horizon_mask=same_season_mask, train_D=D42)
both = same_season_mask & np.isfinite(r0) & np.isfinite(r42)
R['V7_rps_h0_vs_h42'] = dict(h0=round(float(r0[both].mean()), 5), h42=round(float(r42[both].mean()), 5),
                             diff=boot_diff(np.where(both, r42, np.nan), np.where(both, r0, np.nan)))
mon = pd.DataFrame(dict(month=d.Date.dt.month, r0=r0, r42=np.where(both, r42, np.nan), base=base))
R['T5_rps_by_month'] = mon.groupby('month').agg(n=('r0', lambda x: int(np.isfinite(x).sum())), elo_h0=('r0', 'mean'),
                                                elo_h42=('r42', 'mean'), freq=('base', 'mean')).round(4).reset_index().to_dict('records')
mon.groupby('month').mean().to_csv(out / 'T5_rps_by_month.csv')
# residual of Elo expected score by weekday / phase (does the calendar carry information beyond ratings?)
D100, _, _ = run_elo(K=20.0, H=100.0, lam=1.0)
E = 1 / (1 + 10 ** (-D100 / 400))   # residuals w.r.t. the published method (H=100)
S = (2 - d.y.to_numpy()) / 2
d['resid'] = S - E
x = d[(d.season <= 2025) & (d.closed == 0)].copy()
x['dow'] = x.Date.dt.day_name().str[:3]
x['rnd'] = x.groupby('season').cumcount() // 10 + 1
x['phase'] = pd.cut(x.rnd, [0, 5, 18, 33, 38], labels=['R1-5', 'R6-18', 'R19-33', 'R34-38'])
for key in ['dow', 'phase']:
    g = x.groupby(key, observed=True).resid.agg(['size', 'mean', 'std'])
    g['se'] = g['std'] / np.sqrt(g['size'])
    R[f'T56_resid_by_{key}'] = g.round(4).reset_index().to_dict('records')
json.dump(R, open(out / 't_elo_results.json', 'w'), indent=1, default=str)
print(json.dumps({k: v for k, v in R.items() if not k.startswith('T1_per') and not k.startswith('T56_by')}, indent=1, default=str))
