"""Figures for the report (static PDF/PNG). usage: python3 -I time_structure/t_figures.py time_structure/out"""
import sys, json
from pathlib import Path
import pandas as pd, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
out = Path(sys.argv[1])
BLUE, ORANGE, INK, INK2, GRID, SURF = '#2a78d6', '#eb6834', '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': INK2, 'axes.labelcolor': INK2, 'xtick.color': INK2,
                     'ytick.color': INK2, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': SURF, 'axes.facecolor': SURF, 'savefig.facecolor': SURF})

# Figure 1: home advantage by season (two panels, one measure each)
s = pd.read_csv(out / 'T1_home_adv_by_season.csv'); s['yr'] = s.season_label.str[:4].astype(int)
s = s[s.yr <= 2025]
fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
for ax, col, ttl, fmt in [(axes[0], 'H', 'Home-win rate', '{:.0%}'), (axes[1], 'log_goal_ratio', 'log(home goals / away goals)', '{:.2f}')]:
    ok = s[s.yr != 2020]
    ax.plot(s.yr, s[col], color=BLUE, lw=2, marker='o', ms=4, zorder=3, markeredgecolor=SURF, markeredgewidth=1)
    b = np.polyfit(ok.yr, ok[col], 1)
    ax.plot(ok.yr, np.polyval(b, ok.yr), color=INK2, lw=1, ls='--', zorder=2)
    c = s[s.yr == 2020].iloc[0]
    ax.annotate('2020/21\nno crowds', (2020, c[col]), xytext=(2011.5, c[col] + (0.012 if col == 'H' else 0.04)), color=INK, fontsize=8,
                va='center', arrowprops=dict(arrowstyle='-', color=INK2, lw=0.8))
    ax.set_title(ttl, color=INK, fontsize=9, loc='left')
    ax.grid(axis='y', color=GRID, lw=0.6); ax.set_axisbelow(True)
    ax.set_xticks([2000, 2005, 2010, 2015, 2020, 2025]); ax.set_xticklabels(['00/01', '05/06', '10/11', '15/16', '20/21', '25/26'])
    ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.04 if col == 'H' else 0.1))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _, f=fmt: f.format(v)))
axes[0].text(0.02, 0.03, 'dashed: linear trend, 2020/21 excluded', color=INK2, fontsize=7, transform=axes[0].transAxes)
fig.tight_layout(); fig.savefig(out / 'fig_T1_home_advantage.png', dpi=200); fig.savefig(out / 'fig_T1_home_advantage.pdf')

# Figure 2: RPS vs half-life, horizon 0 vs 42 days
g = pd.read_csv(out / 'T3_half_life_grid.csv'); g = g[g.delta == 1.0]
fig, ax = plt.subplots(figsize=(4.8, 3.0))
xs = {str(h): i for i, h in enumerate(['60', '90', '120', '180', '270', '365', '540', '730', 'inf'])}
for hz, colr, lab in [(0, BLUE, 'data up to the day before'), (42, ORANGE, 'data 42 days old (as in the test)')]:
    t = g[g.horizon == hz].copy()
    t['x'] = t.half_life.map(lambda v: 'inf' if str(v) == 'inf' else str(int(float(v)))).map(xs)
    ax.plot(t.x, t.rps, color=colr, lw=2, marker='o', ms=5, markeredgecolor=SURF, markeredgewidth=1, zorder=3)
    ax.plot([], [], color=colr, lw=2, marker='o', ms=5, label=lab)
ax.set_xticks(range(9)); ax.set_xticklabels(['60', '90', '120', '180', '270', '365', '540', '730', 'no\ndecay'])
ax.set_xlabel('half-life of time-decay weights (days)'); ax.set_ylabel('mean RPS (lower is better)')
ax.set_title('Poisson model, walk-forward 2010/11-2026/27\nboth curves lowest at 270 days', color=INK, fontsize=8.5, loc='left')
ax.grid(axis='y', color=GRID, lw=0.6); ax.set_axisbelow(True); ax.set_xlim(-0.4, 8.4)
ax.legend(frameon=False, fontsize=7.5, loc='upper center', labelcolor=INK)
fig.tight_layout(); fig.savefig(out / 'fig_T3_half_life.png', dpi=200); fig.savefig(out / 'fig_T3_half_life.pdf')
print('ok')
