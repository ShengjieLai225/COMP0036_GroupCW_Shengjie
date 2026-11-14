# Beat the Bookie: Group Progress Report

COMP0036 group coursework, UCL, 2026/27. Status as of 14 November 2026.

This README is the single English entry point to the repository. It explains what we have done so far, why we made each decision, where the code and outputs live, and what is still to be done. Everything that follows (feature work, final models, the notebook and the report) should build on the data version, evaluation protocol and baselines defined here. If you need to change any of them, update this file first and say so in the commit message.

**Contents**

1. [The task](#1-the-task)
2. [Status at a glance](#2-status-at-a-glance)
3. [Repository layout](#3-repository-layout)
4. [How to reproduce everything](#4-how-to-reproduce-everything)
5. [Data cleaning](#5-data-cleaning)
6. [Club Elo ratings: replicating the published method](#6-club-elo-ratings-replicating-the-published-method)
7. [Time-decayed Poisson model](#7-time-decayed-poisson-model)
8. [Time structure of the data](#8-time-structure-of-the-data)
9. [External data](#9-external-data)
10. [Evaluation protocol and baseline results](#10-evaluation-protocol-and-baseline-results)
11. [Baseline specification v1.0 (rules for all further work)](#11-baseline-specification-v10-rules-for-all-further-work)
12. [The report](#12-the-report)
13. [Open decisions and next tasks](#13-open-decisions-and-next-tasks)
14. [Working with this repository](#14-working-with-this-repository)

---

## 1. The task

- **Goal**: predict the full-time result (H, D or A) of the 10 Premier League matches played on **30 January 2027** (`Data_Files/epl-test.csv`).
- **Deadline**: 21 December 2026, 16:00.
- **Deliverables**:
  - a report of at most 10 pages in the arXiv LaTeX template (`LaTeX_Files/`), references included;
  - a Jupyter notebook that reproduces every result;
  - the predictions file in the format of `Data_Files/sample-submission.csv`.
- **Rules that shape our design**:
  - betting odds must not be used as features;
  - generative AI use falls under UCL Category 2 (assistive), and the report needs a declaration.
- **Marking weights**: Methodology 15, Evaluation 15, Results 15, Interest 40, Format 15. "Interest" carries the most weight, which is why the analyses below put a lot of effort into insight and into honest negative results, not only into accuracy.

One consequence matters for almost every decision. **We submit on 21 December but the matches are played on 30 January.** Our predictions can only use data up to mid-December, about six match rounds (42 days) before the test matches. Section 10 explains how we build this gap into validation.

---

## 2. Status at a glance

| Area | Status | Main output |
|---|---|---|
| Data cleaning (D1–D10) | Done | `cleaning/out/matches_clean.csv` (9,980 matches) |
| Elo replication | Done | `time_structure/t_elo.py`, `foundation/f_second_pass.py` |
| Time-decayed Poisson model | Done (independent Poisson, no Dixon–Coles ρ yet) | `time_structure/t_decay.py` |
| Time structure (T1–T6) and forecast horizon (V7) | Done | `time_structure/out/`, two report figures |
| External data screening (E1–E10) | Done | Decisions in Section 9 |
| Manager changes (E6) | Done, negative result | `e6_manager/` |
| Champions League congestion (E7) | Done, negative result | `foundation/out/` |
| Baseline scoreboard | Done | Section 10 |
| LaTeX for data, methodology and validation sections | First draft, not yet compiled | `report/` |
| Championship data for promoted clubs (E2) | **To do** | – |
| Dixon–Coles ρ correction | **To do** | – |
| Shots / xG-based strength (E3) | **To do** | – |
| Final model, notebook, predictions | **To do** | – |

---

## 3. Repository layout

```
Group Coursework/
├── README.md                    <- this file
├── Data_Files/                  provided data (unchanged): epl-training.csv, epl-test.csv, sample-submission.csv
├── LaTeX_Files/                 provided arXiv template (unchanged)
├── cleaning/
│   ├── clean_data.py            the full cleaning pipeline (D1–D10)
│   ├── team_names.csv           canonical team names and aliases (52 clubs)
│   ├── referee_map.csv          manual referee-name mappings (10 rows, with confidence)
│   └── out/                     matches_clean.csv, test_clean.csv, cleaning_log.json
├── data_cache/                  every external file we downloaded, with MANIFEST.csv (URL, date, SHA-256)
│   ├── football-data/           E0 seasons 2000/01–2026/27, E1 2025/26, notes.txt
│   └── openfootball_ucl/        Champions League fixtures 2011/12–2025/26 (CC0)
├── time_structure/              Elo and Poisson experiments, figures (T1–T6, V7)
├── e6_manager/                  manager-change event study (E6)
├── foundation/                  second-pass analyses and the unified baseline scoreboard
├── report/                      LaTeX: main.tex, sec_foundation.tex, references.bib, figures/
├── *_en.md                      detailed notes in English:
│   data_cleaning_en.md, time_structure_en.md,
│   external_data_analysis_en.md, elo_method_for_report_en.md
└── *.md                         the original working notes in Chinese (same content), plus
    problem_list.md and foundation_report.md (Chinese only for now)
```

The detailed notes contain the full working, including intermediate checks. This README summarises them, and every number in it can be traced to a JSON or CSV file in one of the `out/` folders.

| Topic | English notes |
|---|---|
| Data cleaning, D1–D10 | [data_cleaning_en.md](data_cleaning_en.md) |
| Time structure, T1–T6 | [time_structure_en.md](time_structure_en.md) |
| External data, E1–E10 | [external_data_analysis_en.md](external_data_analysis_en.md) |
| Elo method and replication | [elo_method_for_report_en.md](elo_method_for_report_en.md) |

---

## 4. How to reproduce everything

**Environment.** Python 3.13 with pandas 3.1, numpy 2.5, scipy 1.18 and matplotlib 3.11. Older recent versions should also work. The manager analysis additionally needs `pypdf` to extract text from the Wikipedia PDF.

Run all commands from the `Group Coursework/` folder. Each script takes its input and output paths as arguments. The `-I` flag runs Python in isolated mode, so no stray local module can be imported by mistake.

1. Clean the data and append 2026/27:

```bash
python3 -I cleaning/clean_data.py Data_Files cleaning/out data_cache/football-data/E0_2627.csv
```

2. Elo experiments and time-structure statistics (T1, T2, T4, T5, T6, V7):

```bash
python3 -I time_structure/t_elo.py cleaning/out/matches_clean.csv time_structure/out
```

3. Time-decayed Poisson model (T3, T4, V7):

```bash
python3 -I time_structure/t_decay.py cleaning/out/matches_clean.csv time_structure/out
```

4. Closed-doors treatment for the Poisson model, and the January draw test:

```bash
python3 -I time_structure/t_covid_poisson.py cleaning/out/matches_clean.csv time_structure/out
```

```bash
python3 -I time_structure/t_jan_draw.py cleaning/out/matches_clean.csv time_structure/out
```

5. Second-pass analyses and the baseline scoreboard:

```bash
python3 -I foundation/f_second_pass.py cleaning/out/matches_clean.csv data_cache/openfootball_ucl foundation/out
```

6. Report figures:

```bash
python3 -I time_structure/t_figures.py time_structure/out
```

7. Manager changes (E6). First extract the PDF text, then run the analysis:

```bash
python3 -I -c "import pypdf; r=pypdf.PdfReader('e6_manager/List of Premier League managers - Wikipedia.pdf'); open('e6_manager/mgr.txt','w').write('\n\n=====PAGE=====\n'.join(p.extract_text() for p in r.pages))"
```

```bash
python3 -I e6_manager/e6_manager.py e6_manager/mgr.txt Data_Files/epl-training.csv data_cache/football-data/E0_2627.csv e6_manager
```

Steps 1–6 take under a minute in total. All random seeds are fixed at 0, so the numbers should match exactly. If they do not, first check the SHA-256 of `matches_clean.csv`. The current value is `c31538e41330868cdff74910351c5764802938b648fe765bebeebd4c45d3fcae`, generated on 11 November 2026. The hash changes every time 2026/27 data are re-downloaded, so record it in the notebook whenever you refresh the data.

---

## 5. Data cleaning

### 5.1 Approach

The provided training file comes from Football-Data.co.uk. We re-downloaded the 27 original season files (2000/01 to 2026/27, cached in `data_cache/football-data/`) and compared them with the training file match by match and column by column. This comparison is used only to **find and verify errors**. It adds no new variables.

The pipeline in `cleaning/clean_data.py`:

1. Read every column as text and record the original line number (`src_row`), so any row can be traced back to the raw file.
2. **D1**: remove the one blank row (line 5702, between 2014/15 and 2015/16).
3. **D3**: parse dates with explicit formats: `dd/mm/yyyy` for the training file, `30 Jan 27` style for the test file.
4. **D2**: remove the duplicated block and swap the corner and foul columns back (see 5.2).
5. **D4**: assign a season id. A new season starts in August, because 2019/20 finished on 26 July 2020. The script asserts 380 matches per completed season.
6. Apply two single-value patches taken from the official files. Each patch first asserts the old value:
   - 10 March 2022, Wolves v Watford: half-time home goals 2 → 3;
   - 29 October 2023, Liverpool v Nott'm Forest: referee C Salisbury → C Kavanagh.
7. **D5**: run eight logical-consistency assertions, for example half-time goals ≤ full-time goals and the result matching the score. All pass.
8. **D6**: three matches record more shots on target than shots (five values). The official files contain the same values, so we set them to missing and add a flag. The 51 matches with more goals than shots on target are kept, because own goals explain them.
9. **D7**: normalise referee names, merging 190 spellings into 84 referees.
10. **D8**: add a flag for the change in how shots on target are counted (see 5.2).
11. **D9**: map team names to canonical names with `team_names.csv`. The script raises an error on any unknown name. The test file uses `Ipswich Town` and `Nottingham Forest`, so the original names are kept for the submission.
12. **D10**: append the 2026/27 matches played so far from the same source. All betting-odds columns are dropped through a column whitelist.
13. Add a `closed` indicator for matches played behind closed doors (17 June 2020 to 16 May 2021, 452 matches).

### 5.2 Main findings

| Finding | Evidence | Action |
|---|---|---|
| **The first 100 matches of 2023/24 appear twice, and from the duplicate to the end of the file the corner and foul columns are swapped** (HC↔HF, AC↔AF), affecting 1,040 matches from 2023/24 to 2025/26 | Mean home "corners" jump from 5.6 to 10.8 per match. Against the official files, 1,138 of 1,140 rows are exactly swapped | Keep the first copy and swap the columns back. An assertion (mean corners < mean fouls) protects future appends |
| Shots-on-target definition changes in 2013/14 | The share of shots that are on target drops from 0.566 to 0.332, while total shots barely change. 2026/27 so far: 0.31 | Flag the era; standardise shot-based features within each season |
| Three matches with more shots on target than shots | The official files contain the same values | Set to missing, flag |
| 190 referee spellings | – | Merged into 84 referees. Referees are **not** in the test file, so they cannot be prediction features |
| Inconsistent team names | Test file uses full names | Central mapping table, 52 clubs |

**Anyone who has used corners or fouls from `epl-training.csv` needs to re-run that analysis on the cleaned file.**

### 5.3 Output

`cleaning/out/matches_clean.csv` has 9,980 matches: 9,880 from 2000/01 to 2025/26 plus 100 from 2026/27 (up to 8 November 2026). Besides the original 22 columns it contains:

- `match_id`, `season`, `season_label`;
- `Time`, `HxG`, `AxG` (2026/27 only);
- `Referee_raw`;
- `era_sot`, `flag_shots`, `flag_goals_gt_sot`, `closed`;
- `source` and `src_row`, which trace every row back to its raw file.

All counts quoted above are written to `cleaning_log.json`. Against the official files, all 9,980 matches match, and every numeric value is identical apart from the five values we deliberately set to missing.

---

## 6. Club Elo ratings: replicating the published method

### 6.1 Which "Club Elo"?

There are two different public club-rating sites with different formulas and numbers, and they should not be confused in the report:

- **elofootball.com** (maintained by Erik Pfeiffer). It publishes its full method and, for every match, the pre-match ratings and probabilities. **This is the method we replicate.**
- **clubelo.com**. Its API returned errors (502/403) every time we tried it in November 2026, so we do not use it.

We **rebuild the ratings ourselves** from the published formulas instead of downloading them, for three reasons:

1. elofootball's terms of use allow non-commercial citation but forbid copying its content in bulk, so we cannot ship its rating history in our submission.
2. Our own implementation is fully reproducible from the training data.
3. We can tune the parameters and extend the method inside our own validation.

The site's numbers serve only as a check and a benchmark. They are never used as features.

### 6.2 The published method

Matches are processed in date order. For a home team with rating $R_h$ and an away team with rating $R_a$:

$$E_h = \frac{1}{1 + 10^{-d/400}}, \qquad d = R_h + H - R_a$$

- $H$ is the home advantage in rating points (100 on the site).
- $E_h$ is the home team's **expected score**, where a draw counts as half a win: $E_h = P(\mathrm{H}) + \tfrac12 P(\mathrm{D})$. It is not a win probability, and the report must not call it one.

After the match, both ratings move by the same amount in opposite directions:

$$R_h \leftarrow R_h + K\,G(N)\,(S_h - E_h), \qquad R_a \leftarrow R_a - K\,G(N)\,(S_h - E_h)$$

- $S_h$ is 1, ½ or 0 for a home win, draw or loss.
- $K$ is the step size (20 for league matches on the site).
- $G(N)$ is the goal-difference multiplier:

$$G(N)=\begin{cases}1 & N\le1\\ 3/2 & N=2\\ (11+N)/8 & N\ge3\end{cases}$$

A club joining the league starts at the average rating of the previous season's relegated clubs.

This update is one stochastic-gradient step on the squared error of the expected score. $K$ therefore acts as a learning rate: a large $K$ reacts quickly to form but is noisy, a small $K$ is stable but slow. It is the same bias–variance trade-off as the half-life of the time-decayed Poisson model in Section 7.

### 6.3 Our extensions

1. **Draw probabilities.** The site does not say how it turns ratings into three outcome probabilities. We map the rating difference $d$ to H/D/A with an **ordered logistic model**:

$$P(\mathrm{H}) = \sigma(\beta d - \theta_1), \qquad P(\mathrm{H} \cup \mathrm{D}) = \sigma(\beta d - \theta_2), \qquad \theta_1 > \theta_2$$

   This model is fitted by maximum likelihood on the five seasons before each evaluation season (Hvattum & Arntzen, 2010).
2. **Season shrinkage.** At the start of every season, ratings are pulled towards the league mean: $R_i \leftarrow \lambda R_i + (1-\lambda)\bar R$. This reflects squad changes over the summer. The site does not do this.
3. **Tuned parameters.** $K$, $H$ and $\lambda$ are chosen by walk-forward validation (Section 10). The selected values are **K = 15, H = 65, λ = 0.9**, chosen in almost every season by nested selection. They differ from the published K = 20 and H = 100, but the differences in score are not significant.
   - The smaller K agrees with the site author's own least-squares experiments, which found K ≈ 15 for samples of 10,000+ matches.
   - The smaller H agrees with the decline in home advantage shown in Section 8.
4. **Forecast horizon.** For validation, ratings can be "frozen" a fixed number of days before kick-off (function `d_at_horizon` in `t_elo.py`), so that we score exactly the situation of the real submission.

The implementation is `run_elo()` in `time_structure/t_elo.py`, and a compact copy sits in `foundation/f_second_pass.py`.

### 6.4 Validation against the site

On the 100 Premier League matches of 2026/27 played so far:

| Model | RPS |
|---|---|
| Our replicated Elo | 0.2077 ± 0.0123 |
| elofootball's published pre-match probabilities (scored on 10 November) | 0.2118 |
| Frequency baseline | 0.2290 |

With 100 matches the standard error is about 0.012. So we can only say that our replication performs at the same level as the published system and clearly better than the baseline. The site page became unreachable on 11 November, so a match-by-match paired comparison was not possible.

---

## 7. Time-decayed Poisson model

The second baseline is a goals model in the tradition of Maher (1982) and Dixon & Coles (1997):

$$\log \lambda_h = \mu + \gamma + \alpha_h - \delta_a, \qquad \log \lambda_a = \mu + \alpha_a - \delta_h$$

- $\alpha$ and $\delta$ are attack and defence strengths, and $\gamma$ is home advantage.
- Home and away goals are independent Poisson variables. The Dixon–Coles low-score correction ρ is not included yet.
- Matches are weighted by $w = 0.5^{\text{age}/\tau}$ with half-life τ = 270 days, inside a four-year window.
- An L2 penalty of 1.0 keeps strengths of clubs with little data close to zero.
- The model is fitted by iteratively reweighted least squares and refitted every week.
- A club with no matches in the window gets the average strength of the weakest third of the league.
- Outcome probabilities are obtained by summing the joint score distribution.

The implementation is in `time_structure/t_decay.py`.

---

## 8. Time structure of the data

| Question | Finding | Default we adopt |
|---|---|---|
| T1 Home advantage | Declining: the log goal ratio falls by 0.063 ± 0.017 per decade. Over recent seasons it is worth about 67 Elo points. We find no evidence that some teams have a larger home advantage than others | One league-wide home parameter, estimated from recent data |
| T2 Closed doors (452 matches) | Home wins fell from 46.0% to 38.9%, and **the home–away yellow-card gap disappeared** (−0.34 → 0.00) | Keep these matches, add the `closed` indicator. How they are treated makes no difference to forecasts from 2021/22 on |
| T3 Time decay | Half-life 270 days is best, 0.0023 [0.0013, 0.0033] RPS better than no decay. Nested selection picks 270–365 days every season | Half-life 270 days, 4-year window |
| T4 Season boundaries | With time decay, extra down-weighting across seasons does not help. For Elo, λ = 0.9 and λ = 1 are equivalent, while λ ≤ 0.7 is worse | Elo K = 15, H = 65, λ = 0.9 |
| T5 Month and season phase | The January draw rate is 28%, but a January draw parameter gives no out-of-sample gain | No calendar features |
| T6 Day of the week | No information beyond Elo | Not used |
| V7 Forecast horizon | Using ratings from 42 days earlier costs Elo +0.00085 [0.00035, 0.00136] RPS and Poisson +0.00123 [0.0003, 0.0022] | **All final comparisons use the 42-day horizon** |

Two points are worth highlighting in the report:

- **Home advantage and referees.** The long-run fall in home advantage, its near disappearance without crowds, the simultaneous disappearance of the yellow-card gap, and the lower home advantage our tuning selects all point to the same mechanism. A large part of home advantage works through the crowd's influence on referees, consistent with Bryson et al. (2021). This is a strong "insight into the data" point.
- **The forecast horizon costs more than any tuning gains.** It is therefore essential that validation reproduces the 42-day gap.

Figures for the report are in `report/figures/`: `fig_T1_home_advantage.pdf` and `fig_T3_half_life.pdf`.

---

## 9. External data

Each candidate source was checked for three things: whether it is available, whether it would be known before kick-off, and whether its licence allows us to use it. Every file we downloaded is cached in `data_cache/` and listed in `MANIFEST.csv` with its URL, download date, SHA-256 and licence note. The notebook should read the cache first and download only if a file is missing.

| ID | Data | Decision | Reason |
|---|---|---|---|
| E1 | 2026/27 Premier League results (Football-Data.co.uk, same source as the training file) | **Use** | Essential: the current season. 100 matches appended; about 160 will be available by the deadline. Re-download in mid-December |
| E2 | Championship results (Football-Data.co.uk) | **Use (to do)** | Promoted clubs Coventry, Ipswich and Hull were in the Championship in 2025/26. Joint modelling gives them real ratings instead of a cold start |
| E3 | Expected goals (xG) | **Partly** | Only 2026/27 has xG in Football-Data. For history we will use season-standardised shots on target as a proxy |
| E4 | Squad market values (Transfermarkt-derived dataset) | Not now | Data stop in June 2026; point-in-time and terms-of-use problems |
| E5 | Club Elo (elofootball.com) | **Replicate the method; site values as benchmark only** | See Section 6 |
| E6 | Manager changes (Wikipedia list) | **Not a feature; report as a negative result** | See 9.1 |
| E7 | European fixture congestion | **Not a feature; report as a negative result** (Champions League); Europa League cannot be tested | See 9.2 |
| E8 | Travel distance (Wikidata stadium coordinates) | Optional small ablation | Easy to build, expected effect small |
| E9 | Injuries, weather | Not used | Not known at the submission date |
| E10 | Player ratings (EA FC) | Not used | High cost, poor reproducibility |

### 9.1 Manager changes (E6)

We parsed the Wikipedia "List of Premier League managers" (version current on 8 November 2026): 519 managerial spells, 120 of them caretakers. That gives 171 mid-season departures, about 6.6 per season.

- **Raw picture.** Around a sacking, points per game rise from 0.72 before to 1.18 after. The Elo residual (actual minus expected score) rises from −0.145 to +0.028.
- **Controls.** Each change is matched with 5 similar clubs that hit a similar slump but kept their manager; 151 changes could be matched. These controls also recover (+0.051).
- **Difference-in-differences.** The extra effect of the new manager is −0.018 [−0.046, +0.009], i.e. zero. The apparent "new-manager bounce" is regression to the mean, in line with Bruinshoofd & ter Weel (2003) and van Ours & van Tuijl (2016).
- **Summer changes.** 8 of the 17 continuing clubs changed manager in summer 2026 (47%, against 18% historically). Summer changes do not make Elo less reliable (p = 0.90).
- **Changes before the test matches.** Historically there are about 1.1 changes per season between 21 December and 30 January, and 69% of seasons have at least one. This is a risk we cannot model; it goes into the report's limitations.

### 9.2 Champions League congestion (E7)

Using openfootball's Champions League fixtures (2011/12 to 2025/26, CC0), we looked at the 2,394 Premier League matches played by clubs in that season's Champions League.

- Matches with **three days' rest or less** after a Champions League game have an Elo residual of +0.024 ± 0.026 (163 matches).
- Matches with no Champions League game in the previous 7 days have −0.014 ± 0.009 (1,801 matches).
- The difference is +0.038 ± 0.027: **no sign of fatigue**.
- The asymmetric case (only one side played midweek, 144 matches) gives the same answer.

Europa League fixtures are not available historically, so that effect cannot be tested. It goes into the limitations.

### 9.3 What the external analysis tells us

Once team strength is controlled for, every "calendar" factor we tested is close to zero: manager changes, midweek European games, month, day of the week and season phase. **Almost all predictive power comes from estimating team strength accurately and promptly.** Further effort should therefore go into better strength estimates (Championship data, shots/xG, time decay), not into more contextual variables.

Three independent results also point the same way: Elo under-rates clubs after a bad run (E6), a smaller K is preferred (T4), and very short half-lives are worse (T3). Single results are noisy, so strength estimates should update cautiously. **Less noisy signals such as shots and xG are the most promising route to an improvement.** This is our main candidate for the "interest" part of the report.

### 9.4 Promoted clubs

Under the current rule, a promoted club starts at the average rating of the relegated clubs. Over 78 first seasons this slightly under-rates promoted clubs: the mean residual over their first 19 matches is +0.019 ± 0.011, which is not significant.

Promoted clubs average 0.97 points per game against 1.45 for the others, and 44% go straight back down. By the deadline, this season's promoted clubs will each have about 16 matches of 2026/27, so the cold start matters mostly in early-season validation rather than for the test matches themselves. Adding Championship data (E2) should remove the remaining bias.

---

## 10. Evaluation protocol and baseline results

### 10.1 Protocol

- **Walk-forward validation.** For each evaluation season, models are fitted only on earlier data and refitted every 7 days. No information from the future is ever used.
- **42-day horizon.** The main scores use team strengths as they stood 42 days before kick-off, which mirrors the gap between submission and the test matches. Scores at horizon 0 are reported alongside.
- **Nested selection.** Hyperparameters such as K, H, λ and the half-life are chosen using only seasons before the one being evaluated.
- **Metrics.**
  - The main metric is the **Ranked Probability Score** (RPS; Epstein, 1969; Constantinou & Fenton, 2012). It respects the ordering H < D < A, and lower is better.
  - Log loss and accuracy are secondary.
- **Comparisons.** Two models are compared with a **paired bootstrap over match days** (2,000 resamples, seed 0). We report the mean difference with its 95% confidence interval.

### 10.2 Baseline scoreboard

Evaluated on 6,128 matches from 2010/11 to 2026/27:

| Model | RPS, horizon 0 | RPS, horizon 42 days | Accuracy, 42 days |
|---|---|---|---|
| Frequency baseline (H/D/A shares of the previous 5 seasons) | 0.2308 | 0.2308 | 44.7% (always "home") |
| Elo + ordered logit (K = 15, H = 65, λ = 0.9) | 0.2002 | **0.2011** | **53.1%** |
| Time-decayed Poisson (half-life 270 days) | 0.1999 | 0.2014 | – |

- Elo minus Poisson at 42 days: −0.0004 [−0.0015, +0.0007], not significant.
- Elo beats the frequency baseline by 0.0297 [0.0264, 0.0332].

**Any new model must beat 0.2011 under the same protocol, on the same matches, with a paired confidence interval.**

### 10.3 Hard labels

The submission needs H, D or A, not probabilities. A well-calibrated model **never makes a draw the most likely outcome**: over 7,980 matches from 2005 to 2025, the highest draw probability was 0.32. Taking the most likely outcome (argmax) gives 53.7% accuracy and maximises expected accuracy.

On only 10 matches, accuracy is mostly luck: the 90% range at our hit rate is 30% to 80%. The report should therefore lead with RPS and log loss and present accuracy as secondary.

---

## 11. Baseline specification v1.0 (rules for all further work)

1. **Data**: read only `cleaning/out/matches_clean.csv`, never `epl-training.csv` directly. Use canonical team names from `team_names.csv`.
2. **Seasons**: a season starts in August, and `season` is its starting year. 2026/27 is incomplete.
3. **Evaluation**: walk-forward, evaluation seasons 2010/11 to 2026/27 by default, weekly refits, **42-day horizon for headline results**, nested hyperparameter selection.
4. **Metrics**: RPS first, then log loss and accuracy. Compare models by paired bootstrap over match days (2,000 resamples, seed 0) and report the difference with its 95% CI.
5. **Baselines**: Elo + ordered logit (K = 15, H = 65, λ = 0.9) and time-decayed Poisson (half-life 270 days, 4-year window, L2 penalty 1.0). Their RPS at 42 days is 0.2011 and 0.2014.
6. **Features**:
   - only information known at kick-off, and for the test matches only what is known at the submission date;
   - no betting odds, referees, injuries or weather;
   - shot-based features standardised within season;
   - include the `closed` indicator.
7. **Admission rule for a new feature**: its paired RPS improvement over the baseline must have a 95% CI that excludes zero. Otherwise it is reported as an ablation, not added to the final model.
8. **External data**: put the file in `data_cache/`, add a row to `MANIFEST.csv`, map team names through `team_names.csv`, and report the match rate.

---

## 12. The report

`report/` contains a first draft that can be pasted into the final document:

- `main.tex`: the arXiv template with `amsmath`, `graphicx` and an IEEE-style bibliography (`\bibliographystyle{IEEEtran}`).
- `sec_foundation.tex`: about 1,900 words with three tables and two figures, roughly 3.5 pages. It covers:
  - Data Transformation and Exploration (sources, validation, non-stationarity);
  - Methodology Overview (Elo with ordered logit, Poisson, external data tested);
  - Model Training and Validation (protocol, RPS, time weighting, baseline table).
- `references.bib`: 22 entries, all cited.

The files have not been compiled yet because no LaTeX installation was available. A static check found no problems with braces, environments, citations, cross-references or figure paths. **Please compile on Overleaf and check every reference's volume and page numbers against the publisher's page**, especially Bryson 2021, Bruinshoofd 2003, van Ours 2016, Constantinou 2012 and Pollard 1986.

Suggested page budget (10 pages in total):

| Section | Pages |
|---|---|
| Introduction | 0.5 |
| Data | 2 |
| Methodology | 2 |
| Training and validation | 1.5 |
| Results | 2 |
| Final predictions | 0.5 |
| Conclusion | 0.5 |
| References | 1 |

A draft GenAI declaration (UCL Category 2) is in `foundation_report.md`, Section 8. Please adjust it to how each of us actually used AI tools.

---

## 13. Open decisions and next tasks

### Decisions for the group

| # | Question | Proposal |
|---|---|---|
| 1 | Submit the most likely outcome (argmax)? | Yes (Section 10.3) |
| 2 | What does the brief mean by analysing performance "on the test set" when the matches have not been played? | Treat it as a historical hold-out at the 42-day horizon. **Email the module lead to confirm** |
| 3 | Can we include cached external data files in the submission zip? | Ask the module lead together with question 2 |
| 4 | Final data refresh date | About one week before the deadline, around 14 December |

### Modelling tasks (volunteers welcome)

| Task | What "done" looks like |
|---|---|
| Championship data (E2) | Elo and Poisson run on Premier League and Championship matches together; paired comparison against the baseline in the first 10 rounds of each season |
| Dixon–Coles ρ | Low-score correction added to `t_decay.py`; paired comparison at 42 days |
| Shots/xG strength | Season-standardised shots on target used in the strength update; checked against real xG on 2026/27 |
| Ensemble | Weighted average of Elo and Poisson probabilities, weight chosen by nested validation |
| Travel distance (E8, optional) | Small ablation using Wikidata stadium coordinates |
| Notebook | One notebook that runs the whole pipeline from the cached files and writes the predictions CSV |

### Checks still needed

- The closed-doors dates (17 June 2020 to 16 May 2021) against an official source.
- The Wikipedia revision id (oldid) for the managers list.
- How Hull were promoted in 2025/26.
- The volume and page numbers of all journal references.

---

## 14. Working with this repository

- **Pull before you start, push when you finish.** In GitHub Desktop: Fetch origin / Pull → work → write a short summary → Commit to main → Push origin.
- **Avoid editing the same file at the same time.** Notebooks (`.ipynb`) are especially hard to merge. Develop in your own `.py` file or your own notebook, and let one person merge into the main notebook.
- **Never overwrite cleaned data by hand.** Change `clean_data.py`, re-run it, and note the new SHA-256.
- **New results go into an `out/` folder next to the script that produced them**, as JSON or CSV, so every number in the report can be traced.
- **The repository must stay private.** It contains our coursework, and a public repository could be copied by other groups.

---

### Key references

- A. E. Elo, *The Rating of Chessplayers, Past and Present*, 1978.
- M. J. Maher, "Modelling association football scores," *Statistica Neerlandica*, 1982.
- M. J. Dixon and S. G. Coles, "Modelling association football scores and inefficiencies in the football betting market," *JRSS C*, 1997.
- L. M. Hvattum and H. Arntzen, "Using ELO ratings for match result prediction in association football," *Int. J. Forecasting*, 2010.
- E. S. Epstein, "A scoring system for probability forecasts of ranked categories," *J. Applied Meteorology*, 1969.
- A. C. Constantinou and N. E. Fenton, "Solving the problem of inadequate scoring rules for assessing probabilistic football forecast models," *JQAS*, 2012.
- A. Bryson et al., "Causal effects of an absent crowd on performances and refereeing decisions during Covid-19," *Economics Letters*, 2021.
- A. Bruinshoofd and B. ter Weel, "Manager to go? Performance dips reconsidered with evidence from Dutch football," *EJOR*, 2003.
- J. C. van Ours and M. A. van Tuijl, "In-season head-coach dismissals and the performance of professional football teams," *Economic Inquiry*, 2016.
- Data: Football-Data.co.uk; elofootball.com (method page); openfootball/champions-league (CC0); Wikipedia, "List of Premier League managers".

The full IEEE-formatted list is in `report/references.bib`.
