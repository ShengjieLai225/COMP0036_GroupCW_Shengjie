"""Data cleaning for BEAT THE BOOKIE (problems D1-D10).

usage:
    python3 -I cleaning/clean_data.py Data_Files cleaning/out [path/to/E0_2627.csv]

inputs : Data_Files/epl-training.csv, Data_Files/epl-test.csv,
         optional football-data 2026/27 file (https://www.football-data.co.uk/mmz4281/2627/E0.csv)
outputs: out/matches_clean.csv   one row per match, canonical team names, season id, flags
         out/test_clean.csv      test fixtures with canonical names + original names kept
         out/cleaning_log.json   every count / check printed below
Needs cleaning/team_names.csv and cleaning/referee_map.csv next to this script.
"""
import json, re, sys, hashlib, unicodedata
from pathlib import Path
import numpy as np
import pandas as pd

DATA, OUT = Path(sys.argv[1]), Path(sys.argv[2])
NEW = Path(sys.argv[3]) if len(sys.argv) > 3 else None
HERE = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)
log = {}
KEY = ['Date', 'HomeTeam', 'AwayTeam']
NUM = ['FTHG', 'FTAG', 'HTHG', 'HTAG', 'HS', 'AS', 'HST', 'AST', 'HC', 'AC', 'HF', 'AF', 'HY', 'AY', 'HR', 'AR']
CORE = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'HTHG', 'HTAG', 'HTR', 'Referee'] + NUM[4:]

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

# ---------------- step 0: read raw as strings, record provenance ----------------
f_train, f_test = DATA / 'epl-training.csv', DATA / 'epl-test.csv'
log['sha256'] = {f_train.name: sha(f_train), f_test.name: sha(f_test)}
raw = pd.read_csv(f_train, dtype=str, keep_default_na=False)
assert list(raw.columns) == CORE[:10] + NUM[4:], 'unexpected columns'
raw['src_row'] = np.arange(len(raw)) + 2          # line number in the csv (header = line 1)
log['raw_rows'] = len(raw)

# ---------------- D1: empty rows ----------------
blank = (raw[CORE] == '').all(axis=1)
partial = (raw[CORE] == '').any(axis=1) & ~blank
log['D1_blank_rows_src_line'] = raw.loc[blank, 'src_row'].tolist()
assert partial.sum() == 0, 'partially empty rows: inspect by hand'
d = raw[~blank].copy()

# ---------------- D3: dates (explicit formats, never inferred) ----------------
assert d.Date.str.fullmatch(r'\d{2}/\d{2}/\d{4}').all()
d['Date'] = pd.to_datetime(d.Date, format='%d/%m/%Y')
for c in NUM:
    d[c] = pd.to_numeric(d[c], errors='raise').astype(int)
for c in ['HomeTeam', 'AwayTeam', 'FTR', 'HTR']:
    assert (d[c] == d[c].str.strip()).all()

# ---------------- D2: duplicated 2023/24 block + swapped corner/foul columns ----------------
dupmask = d.duplicated(KEY, keep='first')
log['D2_duplicate_rows'] = int(dupmask.sum())
first_dup_line = int(d.loc[dupmask, 'src_row'].min())
log['D2_first_duplicate_src_line'] = first_dup_line
# the first copy (earlier lines) agrees with football-data.co.uk; from the first duplicated line to the
# end of the file the columns HC<->HF and AC<->AF are swapped (verified against the official files,
# 1138 of 1140 rows; the other 2 have HC==HF and AC==AF).
swap = d.src_row >= first_dup_line
copies = d[d.duplicated(KEY, keep=False)].copy()
copies.loc[copies.src_row >= first_dup_line, ['HC', 'HF', 'AC', 'AF']] = \
    copies.loc[copies.src_row >= first_dup_line, ['HF', 'HC', 'AF', 'AC']].to_numpy()
cmp_cols = [c for c in CORE if c not in KEY]
diff = copies.groupby(KEY)[cmp_cols].nunique().gt(1).sum()
log['D2_columns_still_differing_between_copies_after_unswap'] = {k: int(v) for k, v in diff.items() if v}
d = d[~dupmask].copy()
swap = d.src_row >= first_dup_line
d.loc[swap, ['HC', 'HF', 'AC', 'AF']] = d.loc[swap, ['HF', 'HC', 'AF', 'AC']].to_numpy()
log['D2_rows_unswapped'] = int(swap.sum())

# ---------------- D4: season id ----------------
d['season'] = np.where(d.Date.dt.month >= 8, d.Date.dt.year, d.Date.dt.year - 1)   # 2019/20 ends 26 Jul 2020
d['season_label'] = d.season.astype(str) + '/' + ((d.season + 1) % 100).astype(str).str.zfill(2)
sz = d.groupby('season').size()
assert (sz == 380).all(), sz[sz != 380]
assert (d.groupby('season').HomeTeam.nunique() == 20).all()

# ---------------- patches verified against football-data.co.uk (downloaded 2026-11-11) ----------------
PATCH = [  # (date, home, away, column, old, new, evidence)
    ('2022-03-10', 'Wolves', 'Watford', 'HTHG', 2, 3, 'football-data 2122/E0.csv'),
    ('2023-10-29', 'Liverpool', "Nott'm Forest", 'Referee', 'C Salisbury', 'C Kavanagh',
     'second (duplicate) copy in training file + football-data 2324/E0.csv'),
]
applied = []
for dt, h, a, col, old, new, ev in PATCH:
    m = (d.Date == dt) & (d.HomeTeam == h) & (d.AwayTeam == a)
    assert m.sum() == 1 and d.loc[m, col].iloc[0] == old, (dt, h, a, col)
    d.loc[m, col] = new
    applied.append(f'{dt} {h} v {a}: {col} {old} -> {new} ({ev})')
log['patches'] = applied

# ---------------- D5: logical consistency (hard asserts) ----------------
res = lambda h, a: np.select([h > a, h < a], ['H', 'A'], 'D')
checks = {
    'FTR_matches_score': (res(d.FTHG, d.FTAG) == d.FTR).all(),
    'HTR_matches_score': (res(d.HTHG, d.HTAG) == d.HTR).all(),
    'HT_goals_le_FT': ((d.HTHG <= d.FTHG) & (d.HTAG <= d.FTAG)).all(),
    'no_negative': (d[NUM] >= 0).all().all(),
    'home_ne_away': (d.HomeTeam != d.AwayTeam).all(),
    'each_pair_once_per_season': (~d.duplicated(['season', 'HomeTeam', 'AwayTeam'])).all(),
    'no_team_twice_same_day': not pd.concat([d[['Date', 'HomeTeam']].set_axis(['Date', 'T'], axis=1),
                                             d[['Date', 'AwayTeam']].set_axis(['Date', 'T'], axis=1)]).duplicated().any(),
    '38_matches_per_team_season': (pd.concat([d.groupby(['season', 'HomeTeam']).size(),
                                              d.groupby(['season', 'AwayTeam']).size()], axis=1).sum(axis=1) == 38).all(),
}
log['D5_checks'] = {k: bool(v) for k, v in checks.items()}
assert all(checks.values()), checks

# ---------------- D6: shots on target > shots ----------------
d['flag_shots'] = ''
for side, s, st, g in [('home', 'HS', 'HST', 'FTHG'), ('away', 'AS', 'AST', 'FTAG')]:
    bad = d[st] > d[s]
    d.loc[bad, 'flag_shots'] += f'{side}:SOT>S;'
    d[s] = d[s].astype('Int64'); d[st] = d[st].astype('Int64')
    d.loc[bad, [s, st]] = pd.NA
    log[f'D6_{side}_set_missing'] = d.loc[bad, KEY].astype(str).agg(' '.join, axis=1).tolist()
# goals > shots on target is legitimate (own goals are not shots); only flagged
d['flag_goals_gt_sot'] = ((d.FTHG > d.HST) | (d.FTAG > d.AST)).fillna(False).astype(int)
log['D6_goals_gt_sot_rows (kept, own goals)'] = int(d.flag_goals_gt_sot.sum())

# ---------------- D7: referee names ----------------
def ref_key(s):
    s = unicodedata.normalize('NFKC', s).replace('\xa0', ' ').replace('†', '').strip()
    s = re.sub(r'\s+', ' ', s)
    if ',' in s:                                   # "Wiley, A. G." -> "A. G. Wiley"
        a, b = [x.strip() for x in s.split(',', 1)]
        s = f'{b} {a}'
    parts = s.replace('.', ' ').split()
    return f'{parts[0][0].upper()} {parts[-1]}' if len(parts) > 1 else parts[-1]
rmap = pd.read_csv(HERE / 'referee_map.csv', comment='#')
manual = dict(zip(rmap.raw_key, rmap.canonical))
d['Referee_raw'] = d.Referee
d['Referee'] = d.Referee.map(ref_key).map(lambda k: manual.get(k, k))
log['D7_referee_unique_raw'] = int(d.Referee_raw.nunique())
log['D7_referee_unique_clean'] = int(d.Referee.nunique())

# ---------------- D8: distribution checks (report only; values are not deleted) ----------------
by = d.groupby('season')
log['D8_season_means'] = by[['HS', 'HST', 'HC', 'HF', 'HY', 'HR']].mean().round(2).to_dict()
sot_ratio = (by.HST.sum() + by.AST.sum()) / (by.HS.sum() + by.AS.sum())
log['D8_sot_per_shot_by_season'] = sot_ratio.round(3).to_dict()
d['era_sot'] = np.where(d.season >= 2013, 'post2013', 'pre2013')   # structural break in HST/AST

# ---------------- D9: team names ----------------
tn = pd.read_csv(HERE / 'team_names.csv')
alias = {}
for _, r in tn.iterrows():
    for a in [r.canonical] + [x for x in str(r.aliases).split('|') if x and x != 'nan']:
        assert alias.get(a, r.canonical) == r.canonical, f'alias clash {a}'
        alias[a] = r.canonical
canon = lambda s: s.map(lambda x: alias[x])         # KeyError = unmapped name -> fix the table
for c in ['HomeTeam', 'AwayTeam']:
    d[c] = canon(d[c])
test = pd.read_csv(f_test, dtype=str)
assert test.Date.str.fullmatch(r'\d{1,2} [A-Z][a-z]{2} \d{2}').all()
test['Date_parsed'] = pd.to_datetime(test.Date, format='%d %b %y')
test['HomeTeam_orig'], test['AwayTeam_orig'] = test.HomeTeam, test.AwayTeam
test['HomeTeam'], test['AwayTeam'] = canon(test.HomeTeam), canon(test.AwayTeam)
log['D9_test_renamed'] = {o: c for o, c in zip(pd.concat([test.HomeTeam_orig, test.AwayTeam_orig]),
                                               pd.concat([test.HomeTeam, test.AwayTeam])) if o != c}
d['source'] = 'epl-training.csv'

# ---------------- D10: append 2026/27 from football-data (same provider, same columns) ----------------
if NEW is not None:
    log['sha256'][NEW.name] = sha(NEW)
    n = pd.read_csv(NEW, dtype=str, keep_default_na=False)
    n = n[n.HomeTeam.str.strip() != '']
    n['src_row'] = np.arange(len(n)) + 2
    n['Date'] = pd.to_datetime(n.Date, format='%d/%m/%Y')
    extra = {c: n[c] for c in ['Time', 'HxG', 'AxG'] if c in n}   # odds columns are dropped here (rule R3)
    n = n[CORE + ['src_row']].assign(**extra)
    for c in NUM:
        n[c] = pd.to_numeric(n[c]).astype(int)
    for c in ['HxG', 'AxG']:
        if c in n:
            n[c] = pd.to_numeric(n[c].replace('', np.nan))
    n['season'] = np.where(n.Date.dt.month >= 8, n.Date.dt.year, n.Date.dt.year - 1)
    n['season_label'] = n.season.astype(str) + '/' + ((n.season + 1) % 100).astype(str).str.zfill(2)
    n['Referee_raw'] = n.Referee
    n['Referee'] = n.Referee.map(ref_key).map(lambda k: manual.get(k, k))
    for c in ['HomeTeam', 'AwayTeam']:
        n[c] = canon(n[c])
    assert n.Date.min() > d.Date.max(), 'overlap with training data'
    assert not n.duplicated(KEY).any()
    assert (res(n.FTHG, n.FTAG) == n.FTR).all() and (res(n.HTHG, n.HTAG) == n.HTR).all()
    assert ((n.HST <= n.HS) & (n.AST <= n.AS)).all()
    # corners must look like corners (guards against the D2 swap reappearing)
    assert n.HC.mean() < n.HF.mean()
    n['flag_shots'] = ''
    n['flag_goals_gt_sot'] = ((n.FTHG > n.HST) | (n.FTAG > n.AST)).astype(int)
    n['era_sot'] = 'post2013'
    n['source'] = NEW.name
    log['D10_appended_rows'] = len(n)
    log['D10_appended_range'] = [str(n.Date.min().date()), str(n.Date.max().date())]
    d = pd.concat([d, n], ignore_index=True)

d = d.sort_values(['Date', 'src_row'], kind='stable').reset_index(drop=True)
# closed doors (T2): Project Restart 17 Jun 2020 to 16 May 2021; verify dates against official sources
d['closed'] = d.Date.between('2020-06-17', '2021-05-16').astype(int)
log['closed_doors_matches'] = int(d.closed.sum())
d['match_id'] = np.arange(len(d))
test_teams = set(test.HomeTeam) | set(test.AwayTeam)
log['D10_test_teams_without_2026_27_data'] = sorted(test_teams - set(d.loc[d.season == 2026, 'HomeTeam']))
log['final_rows'] = len(d)
log['rows_per_season'] = d.groupby('season_label').size().to_dict()

cols = ['match_id', 'season', 'season_label', 'Date'] + [c for c in ['Time'] if c in d] + \
       ['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'HTHG', 'HTAG', 'HTR', 'Referee', 'Referee_raw'] + NUM[4:] + \
       [c for c in ['HxG', 'AxG'] if c in d] + ['era_sot', 'closed', 'flag_shots', 'flag_goals_gt_sot', 'source', 'src_row']
d[cols].to_csv(OUT / 'matches_clean.csv', index=False, date_format='%Y-%m-%d')
test.to_csv(OUT / 'test_clean.csv', index=False, date_format='%Y-%m-%d')
json.dump(log, open(OUT / 'cleaning_log.json', 'w'), indent=1, default=str)
for k, v in log.items():
    if not k.startswith('D8') and k != 'rows_per_season':
        print(k, ':', v)
