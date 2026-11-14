# External Data E1–E10: Screening and Analysis

English version of `external_data_analysis.md`. Sources were checked on 10 November 2026, and the manager analysis (E6) was completed the same day. Notes marked **Update** add results from the later foundation analysis (`foundation_report.md`, 11 November 2026) that change or sharpen a conclusion here.

**How each source was checked**

| Mark | Meaning |
|---|---|
| ✔ | Downloaded and read on 10–11 November 2026 |
| ◐ | Reachable, but not fully verified |
| ✘ | Could not be reached from our machine |
| 📄 | Based only on web pages or second-hand sources |

All downloaded files are cached in `data_cache/`. `data_cache/MANIFEST.csv` records the URL, download date, SHA-256, line count and licence note of each file.

## Overview

| ID | Data | Recommended source | Checked | Known before kick-off? | Value | Recommendation |
|---|---|---|---|---|---|---|
| E1 | First half of 2026/27 Premier League | Football-Data.co.uk `mmz4281/2627/E0.csv` | ✔ | Yes | **Very high** | **Must use** |
| E2 | Championship | Football-Data.co.uk `mmz4281/YYZZ/E1.csv` | ✔ | Yes | **High** (cold start) | **Must use** |
| E3 | Expected goals (xG) | Football-Data (2026/27 only); Understat (from 2014/15) | ✔ / ✘ | Lagged values are | Medium–high | Usable for 2026/27; historical xG needs another source |
| E4 | Squad market values | transfermarkt-datasets (a compilation of Transfermarkt) | ✔ | Needs point-in-time reconstruction | Medium | Optional; mind the terms and the timing |
| E5 | Club Elo | **elofootball.com** (✔); api.clubelo.com (✘ 502/403) | ✔ | Yes | Medium–high | **Replicate its published method ourselves**; site values only as a check and benchmark |
| E6 | Manager changes | Wikipedia list (PDF, up to 8 November 2026) + premierleague.com | ✔ | Yes | **Low (tested)** | New-manager effect ≈ 0 (regression to the mean); not in the main model; report as a negative result |
| E7 | European fixtures | openfootball/champions-league, UEFA.com | ✔ (to 2025/26) | Fixtures published in advance | **Low (tested for the UCL)** | Not a feature; report as a negative result |
| E8 | Travel distance | Wikidata SPARQL (stadium coordinates) | ✔ | Yes | Low | Easy; a small ablation |
| E9 | Injuries / weather | FPL official API (injuries, current only); Open-Meteo (weather) | ✔ | No injury history; no weather forecast at the deadline | Low | Discussion or a final qualitative check only |
| E10 | Player ratings | EA official ratings page; Kaggle FIFA/FC datasets | 📄 | Release dates are known | Low–medium | Heavy work; not recommended as a main line |

---

## E1. First half of the 2026/27 Premier League ✔

- **Source**: Football-Data.co.uk.
  - Overview page: https://www.football-data.co.uk/englandm.php
  - Direct file: https://www.football-data.co.uk/mmz4281/2627/E0.csv
  - Column notes: https://www.football-data.co.uk/notes.txt
- **This is the source of the training file.** We merged Football-Data's 2025/26 file with `epl-training.csv` on (date, home team, away team): **all 380 of 380 matches matched**. Column names and team spellings (e.g. `Nott'm Forest`, `Ipswich`) are identical, so the files can be concatenated directly.
- **Update (11 November).** The 10 November check compared only goals and shots on target, which agreed exactly. A full column-by-column comparison later showed that **the corner and foul columns are swapped in the training file from 2023/24 onwards**. See `data_cleaning_en.md`, D2; that document takes precedence.
- **Current content**: 100 matches from 21 August to 8 November 2026 (10 rounds), 114 columns. Downloaded 10 November 2026.
- **Extra columns**:
  - `Time` (kick-off time);
  - **`HxG` and `AxG`** (see E3);
  - many odds columns (`B365H`, `PSH`, `AvgH`, …). These **must be removed**: the coursework forbids odds as features.
- **What will be available at the deadline**: openfootball's fixture list puts round 16 on Saturday 19 December 2026. So **16 rounds, 160 matches**, will be available before the 21 December deadline.
- **The gap between the deadline and the test matches**: rounds 17–22 (26 and 29 December, 1, 5, 16 and 23 January), **6 rounds and 60 matches**, will not be known at submission. The test matches are round 23 (30 January 2027). Validation must simulate this forecast distance (problem list, V7).
- **Risks**:
  - The file is updated weekly, and older rows can be corrected. Fix the download date, write "data as of YYYY-MM-DD" in the notebook, and cache a copy.
  - notes.txt says dates are `dd/mm/yy`, but the actual file uses `dd/mm/yyyy`. Parse with an explicit format and check it.

## E2. Championship data ✔

- **Source**: the same site, `https://www.football-data.co.uk/mmz4281/YYZZ/E1.csv` (e.g. `2526/E1.csv`), in the same format as the Premier League files.
- **Verified**: 2025/26 Championship, 552 matches (24 teams × 46 rounds).
  - Points computed from the scores: **Coventry first with 95, Ipswich second with 84**, Hull 73. All three are in the 2026/27 Premier League.
  - How Hull were promoted (e.g. through the play-offs) has not been checked. Verify before mentioning it in the report.
- **2026/27 Championship**: 180 matches so far, including the newly relegated West Ham, Wolves and Burnley.
- **Uses**:
  1. **Cold start.** Fit a joint Premier League + Championship Dixon–Coles or Elo model, **using promoted and relegated clubs to estimate the strength gap between the two leagues**. Three clubs go up and three come down every year, giving about 25 × 6 = 150 cross-league links. This follows the cross-league pooling idea of the original Dixon–Coles (1997) paper.
  2. Coventry appear in the training file only in 2000/01. Championship data fill in their entire history from 2001 to 2026.
- **Risks**:
  - Championship team names must be added to the same mapping table.
  - Home advantage may differ between leagues; a league-specific parameter can be added.

## E3. Expected goals (xG)

| Source | Coverage | Checked | Problem |
|---|---|---|---|
| Football-Data `HxG`/`AxG` | **2026/27 only** (absent from 2025/26 and earlier files) | ✔ all 100 matches filled | No history, so we cannot train or test an xG feature historically. The provider does not say where the values come from (not in notes.txt); state "source not specified" |
| Understat (understat.com) | Premier League from 2014/15, per match and per shot | ✘ our requests returned an error page | Unofficial, no public API, data embedded in web pages; third-party packages (e.g. `understatapi`) break often |
| FBref | Previously Opta xG | 📄 | **Since 20 January 2026, FBref has removed its advanced data (including xG)** because Opta ended the licence. Old scraping tutorials no longer work |
| FotMob, Sofascore | Have xG | 📄 | Unofficial APIs, restrictive terms; not suitable as a reproducible source |

- **Numbers computed so far.** Over the 100 matches of 2026/27, the correlation between goal difference and xG difference per match is **0.475**. So xG is related to the score but carries different information.
- Some teams differ a lot between the two:
  - Bournemouth: goal difference +2, xG difference +6.6;
  - Nott'm Forest: goal difference −4, xG difference +4.7.

  On xG, both should rank higher than they do.
- **Recommendation**:
  - (a) For history, use **shots on target as a "poor man's xG"**; the training file has HST/AST from 2000.
  - (b) For 2026/27, use real xG to refine this season's strength estimates, and compare the predictive power of the shots-on-target proxy with real xG within the season.
  - If Understat works in a team member's browser, consider adding historical xG from 2014.

## E4. Squad market values ✔ (with two problems: terms and timing)

- **Source**: transfermarkt-datasets.
  - GitHub: https://github.com/dcaribou/transfermarkt-datasets
  - Kaggle: `davidcariboo/player-scores`
  - Direct CSV download: `https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/player_valuations.csv.gz` (7.2 MB) and others.
- **Verified**: `player_valuations` has 656,301 rows, dated 20 January 2000 to **12 June 2026**. The README states that **the data pipeline stopped updating in mid-July 2026**, so there are no 2026/27 squads.
- **Problem 1: timing.**
  - The `current_club_name` field is probably the club at the time of scraping, not at the time of the valuation. Records containing "Coventry" appear under several league codes (Scottish, Dutch, French top flights), so the meaning of this field needs checking.
  - Aggregating by it directly would count later transfers towards old clubs, which is leakage.
  - The correct approach is to rebuild each club's squad on each date from the `transfers` / `appearances` tables, then aggregate valuations.
- **Problem 2: terms.**
  - According to second-hand sources, Transfermarkt's terms forbid robotic scraping and require written permission to republish. We could not read the terms directly.
  - Using a third-party compilation still requires citing the original source and checking the licence on the Kaggle page; the README states none.
- **Value**: market value correlates strongly with long-term strength and would help as a **prior for promoted clubs**. But data after the summer 2026 window are missing, so promoted clubs' summer signings are not reflected.
- **Alternative**: reports from bodies such as the CIES Football Observatory are suitable for citation, not as data.

## E5. Club Elo: elofootball.com ✔ (updated 10 November)

**Note: elofootball.com and clubelo.com are two different sites** with different methods and numbers; the report must not use the names interchangeably. On 10 November 2026 the clubelo.com API still returned 502 and its home page 403 from our machine, so everything below concerns elofootball.com.

### Source and pages

- England 2026/27 season page: https://www.elofootball.com/country.php?countryiso=ENG&season=2026-2027 (any season from 1955/56 can be selected).
- Club pages, with match-by-match rating history and end-of-season ratings, e.g. Coventry: https://www.elofootball.com/club.php?clubid=685&season=2026-2027
- Method: https://www.elofootball.com/about.php
- Coverage: https://www.elofootball.com/data_coverage.php
- Terms of use: https://www.elofootball.com/impressum_legal_notice.php
- Maintainer: Erik Pfeiffer (Frankfurt, Germany), according to the site's legal notice.

### What the pages contain (parsed)

The England season page has five tables:
1. **Ratings table** (130 English clubs): current rating, season high, all-time high, change over 1 month / 1 year / this season, rating change over the last six matches, and this season's change split by league, cup and Europe.
2. **Results table**: overall record, plus league, cup and European records separately (matches, wins, draws, losses, goals).
3–4. Summaries by competition.
5. **Match table (1,013 rows)**: date, competition, home and away teams with pre-match ratings, score, and **pre-match three-way probabilities (home / draw / away %)**. Both played and **future** fixtures are listed (currently up to 15 December 2026).

Coverage: England is **complete from 1955 onwards**, including tiers 2–5, the FA Cup, the League Cup and European competition. Promoted clubs therefore have continuous ratings and never start from scratch.

### Method (from the about page)

- Expected win: $WE_h = 1/(10^{-d_r/400}+1)$, where $d_r$ is the pre-match rating difference including home advantage.
- Update: $R\Delta_h = k\cdot gdm\cdot(\text{outcome}-WE_h)$, with outcome 1 / 0.5 / 0 and $gdm$ the goal-difference multiplier.
- **Home advantage 100 points.**
- **$k$ values**: 20 for domestic league, cup, super-cup and play-off matches; 15 for the league cup; 30 for the Champions League; 25 for the Europa League; 20 for the Conference League. The author tried $k\in\{5,\dots,50\}$ by least squares on samples of 1,000–50,000 matches; with 10,000 or more matches the optimum was about 15.
- A club entering a league takes the average rating of the previous season's relegated clubs. A relegated club keeps its rating until it is promoted or meets a rated club in a cup.
- Seasons run from 1 July to 30 June. Our data use an August boundary, so take care when merging.
- **The method page does not explain how the draw probability in the three-way probabilities is calculated.** It gives only the two-way expected win $WE_h$. Say so whenever these probabilities are cited.

Full details of our replication are in `elo_method_for_report_en.md`.

### Current ratings of the 20 Premier League clubs (page of 10 November 2026, after 10 rounds)

| Club | Rating | European rank | 1-year change | Points | Europe this season |
|---|---|---|---|---|---|
| Arsenal | 2383 | 2 | +45 | 27 | Champions League |
| Man City | 2268 | 6 | −24 | 21 | Champions League |
| Brighton | 2190 | 8 | +70 | 22 | Conference League (incl. qualifiers) |
| Liverpool | 2185 | 9 | −58 | 18 | Champions League |
| Bournemouth | 2179 | 10 | +111 | 15 | Europa League |
| Aston Villa | 2176 | 12 | +12 | 13 | Champions League |
| Chelsea | 2101 | 20 | −97 | 16 | – |
| Brentford | 2091 | 24 | +18 | 14 | – |
| Man United | 2085 | 25 | −8 | 8 | Champions League |
| Newcastle | 2074 | 28 | −81 | 12 | – |
| Everton | 2064 | 33 | +42 | 16 | – |
| Leeds | 2063 | 34 | +135 | 14 | – |
| Nott'm Forest | 2053 | 37 | +72 | 9 | – |
| Tottenham | 2048 | 38 | −53 | 12 | – |
| Fulham | 2016 | 46 | +19 | 10 | – |
| Crystal Palace | 2005 | 51 | −160 | 7 | Europa League |
| Sunderland | 1927 | 81 | +86 | 8 | Europa League |
| Coventry | 1878 | 114 | +40 | 9 | – |
| Ipswich | 1875 | 117 | +59 | 11 | – |
| **Hull** | **1800** | 171 | +91 | 11 | – |

- The 20 clubs average 2073. The three promoted clubs are about **200–270 points** below average, two to three times the home advantage of 100 points. By the formula, an average club at home to Hull has an expected score of about $1/(10^{-(273+100)/400}+1)\approx0.89$.
- Coventry's rating path: 1869 at the end of 2025/26 (Championship winners) → 1884 at its 2026/27 peak (4-1 home win over Newcastle on 12 October) → 1878 now. Its all-time high is 2004 (1978).
- Coventry's Premier League record on the page (10 matches, 3 wins, 0 draws, 7 losses, 10 scored, 19 conceded) agrees with Football-Data, which is a useful cross-check.

### How well the site's probabilities perform (100 matches of 2026/27)

| Measure | elofootball pre-match probabilities | Historical frequency baseline |
|---|---|---|
| RPS | **0.2118** | 0.2295 |
| Log loss | 1.0275 | – |
| Accuracy | 49% | – |

- With 100 matches the RPS standard error is about 0.014. So we can only say the site **clearly beats the frequency baseline**; it cannot be compared precisely with other models.
- Assumption: the probabilities shown for played matches are the **pre-match** ones. Elo is a deterministic recursion, so this should be the case, but we found no explicit statement.
- **Update (11 November).** On the same 100 matches, our replicated Elo scores 0.2077 ± 0.0123, the site 0.2118 and the frequency baseline 0.2290 (computed slightly differently from the 0.2295 above). The two Elo systems are at the same level. The site was unreachable on 11 November, so no match-by-match paired comparison was possible. This replaces an earlier remark that a group-4 model score (0.1979, computed on different seasons) could not be compared.

### Terms and reproducibility

- **Terms of use (main points)**:
  - all content is free for **non-commercial use**, such as analysis in forums, blogs and articles, **provided elofootball.com is credited**;
  - the author may supply data for custom queries on request but **does not provide full data dumps**;
  - **mirroring the site or reproducing large parts of its content elsewhere is not allowed**.
- **robots.txt**:
  - ordinary access and retrieval on behalf of a user are allowed, with `Crawl-delay: 10` (10 seconds between requests);
  - crawling the head-to-head (h2h) pages is forbidden;
  - AI-training and large-scale crawlers are blocked.
- **What this means for us**:
  1. Small citations, such as the 20-club table above with the source credited, comply with the terms.
  2. **Scraping every season and club, then packaging the whole rating history into our submission zip, risks breaching the "large-scale copying" clause.** We should not do it.
  3. If a historical rating series is really needed, a team member can email info@elofootball.com explaining the purpose and ask for custom data.

### Recommendation

1. **Best use: replicate the method ourselves.** The formulas and parameters (home advantage 100, $k = 20$, goal-difference multiplier, the rule for new clubs) are all public.
   - Computing Elo ourselves from Football-Data Premier League and Championship data (E1, E2) is **fully reproducible and raises no terms-of-use issue**.
   - It also lets us tune $k$ and the home advantage in walk-forward validation, and add season shrinkage.
2. **Use the site's numbers only for checking and comparison**:
   - the correlation between our replicated ratings and the site's current ratings;
   - the site's pre-match probabilities as a "public Elo benchmark" when comparing RPS.

   They are not betting odds, so the rules do not forbid them. We still recommend using them only as a benchmark and never as a feature, so the model does not depend on an external value we cannot reproduce.
3. **It also helps with E7.** The European column shows that 9 Premier League clubs are playing in Europe this season, and they cover 7 of the 10 test matches (see E7).
4. For the 30 January test matches, the site's ratings at the deadline will include results up to round 16. Changes from rounds 17–22 remain unknown, consistent with problem-list item V7.

---

## E6. Manager changes ✔ (updated 10 November: parsed and tested)

**Conclusion first.** Results do improve after a manager change, but by the same amount as for clubs in a similar slump that kept their manager. **There is no measurable new-manager effect.** Summer changes do not make last season's ratings less reliable either. **Manager changes therefore stay out of the main model** and are reported as a tested negative result, with a short paragraph each in Evaluation and Discussion.

### 1. Data and parsing

- **Source**: the PDF print of Wikipedia's "List of Premier League managers".
  - The page states "up to date as of 8 November 2026"; it was printed on 10 November 2026 at 03:32.
  - 37 pages; first 16 characters of the SHA-256: `7e82c7ed39745006`.
  - For the reference, find the matching revision under "View history" and cite its oldid link.
- **Parsing**:
  - Text extracted with pypdf, then each managerial spell (manager, club, start and end date, caretaker or not) read with regular expressions.
  - Result: **519 spells**, 120 of them caretaker spells.
  - After mapping club names to training-file names, **all 46 clubs** in the training file and 2026/27 are matched.
  - The 20 managers marked as current (†) correspond exactly to the 20 clubs of 2026/27, a useful check that the parsing is correct.
- **Problems handled during parsing**:
  - "Wolverhampton Wanderers" is split over two lines in the PDF and is merged back.
  - Ligatures (ﬀ, ﬁ, ﬃ) are normalised with Unicode NFKC.
  - Caretaker and new-manager dates sometimes overlap (e.g. Danks and Emery at Aston Villa in 2022). The caretaker takes priority when deciding who was in charge of a match.
  - "Until" is the date the departure was announced, so matches on or before that day count as "before the change".
- **Files** (script and all outputs in [e6_manager/](e6_manager/)):
  - `managers_parsed.csv`: all parsed spells;
  - `midseason_departures.csv`: the 171 mid-season departures;
  - `event_profile.csv`: match-by-match averages before and after each change;
  - `summer_changes.csv`: whether each club started each season with a different manager;
  - `current_2026_27.csv`: this season's 20 managers;
  - `e6_results.json`: all summary numbers.

### 2. How often managers change

- **Mid-season departures.** Definition: a permanent manager's spell ends between the club's first and last league match of the season, with at least three league matches before and after.
  - 2000/01 to 2025/26 has **171** such departures, **6.6 per season** on average.
  - The most was 14 in 2022/23; 2025/26 had 11.
- **Summer changes.** Among the 430 club-seasons in which a club stayed in the Premier League for two consecutive seasons, 77 (**18%**) started the season with a different manager from the last match of the previous season.
- **Summer 2026 was exceptional.** **8 of the 17 (47%)** continuing clubs changed manager, 2.6 times the historical rate: Bournemouth, Liverpool, Crystal Palace, Man City, Chelsea, Nott'm Forest, Fulham and Newcastle. With promoted Ipswich, 9 of the 20 clubs have a new manager.
- **2026/27 up to 8 November**: **no mid-season change yet** among the 20 Premier League clubs. West Ham sacked Nuno on 3 November, but West Ham are in the Championship this season.

### 3. The effect of a change: event study with matched controls

**Method**

- Run the published elofootball Elo (K = 20, H = 100, goal-difference multiplier) through every Premier League match from 2000/01 to 2026/27 in date order.
- For each team in each match, record the **residual = actual score − Elo expected score** (win 1, draw 0.5, loss 0). A positive residual means the team did better than its rating predicted.
- Compare the six matches before and the six matches after the departure date.

| | 6 matches before departure | 6 matches after |
|---|---|---|
| Points per game | 0.72 | **1.18** |
| Elo expected score (reflects opponents and rating) | 0.426 | 0.408 |
| Residual (actual − expected) | **−0.145** | +0.028 |

- The residual in the last match before departure is −0.297 (0.28 points per game). Clubs almost always change manager **at the bottom of a run of bad results**.
- Looking only at points per game, a change appears to add 0.46 points. But the Elo expectation for the following six matches does not rise, so the recovery is not caused by an easier fixture list.

**Matched controls**

- For each of the 151 events with complete windows, we found 5 "same slump, no change" controls, matched on:
  - the residual over the previous six matches;
  - points per game over the previous six matches;
  - the match number within the season.

  Control matches with a manager change within 120 days either side were excluded.
- Residual over the following six matches: controls **+0.051** (1.32 points per game); clubs that changed manager +0.032 (1.19 points per game).
- **Difference-in-differences = −0.018**, bootstrap 95% CI [−0.046, +0.009], which includes 0.

**Robustness to K**

| Elo K | Changed clubs, residual over next 6 | Controls, residual over next 6 | Difference-in-differences [95% CI] |
|---|---|---|---|
| 10 | +0.007 | +0.035 | −0.028 [−0.058, +0.002] |
| 15 | +0.021 | +0.043 | −0.022 [−0.051, +0.007] |
| 20 | +0.032 | +0.051 | −0.018 [−0.046, +0.009] |
| 30 | +0.050 | +0.057 | −0.007 [−0.034, +0.020] |

**Interpretation**

- The improvement after a change is essentially **regression to the mean**: part of the slump was bad luck, and results would have recovered anyway. This agrees with the literature (Bruinshoofd & ter Weel 2003 and van Ours & van Tuijl 2016, both on Dutch football; check volume and pages before citing).
- The point estimate is even slightly negative, but not significantly, so we cannot say that changing manager hurts.
- The bootstrap resamples events only and ignores sampling error in the control means, so the true interval is somewhat wider.

**Side finding (useful for the Elo section)**

- Whatever K is, both groups have positive residuals after a slump. **Elo over-reacts to short losing runs**, mistaking part of the bad luck for a loss of strength.
- This supports two choices: a smaller K (the elofootball author's own tests also gave K ≈ 15), and adding less noisy information such as shots and xG to the ratings (see E3).

### 4. Do summer changes make last season's ratings unreliable?

This tests whether clubs that changed manager in summer need stronger season shrinkage (problem list, T4).

| | Club-seasons | Mean residual, first 10 matches | Mean \|residual\|, first 10 matches | Mean \|ΔR\| over the season |
|---|---|---|---|---|
| No change | 353 | −0.010 | 0.102 | 46.2 |
| Summer change | 77 | +0.006 | 0.098 | 46.7 |

- Permutation tests: p = 0.90 for the difference in \|ΔR\|, p = 0.72 for the first-10-match \|residual\|. The same holds for K = 10, 15 and 30 (p between 0.80 and 0.91).
- Conclusion: ratings of clubs with a new manager are **no less accurate** in the new season. This does not support a separate shrinkage factor λ for those clubs; **one league-wide λ is enough**. This can be cited in the Methodology as the justification for the λ design.
- In the first 10 rounds of 2026/27, the 9 clubs with a new manager have a mean residual of −0.040 and the other 11 have +0.032. The difference of 0.07 has a rough standard error of 0.055, not significant; it is descriptive only.

### 5. Relevance to the 30 January test matches

| Test match | Home manager (tenure at 30 Jan) | Away manager (tenure at 30 Jan) | Points per game, first 10 rounds (home / away) |
|---|---|---|---|
| Bournemouth v Fulham | Marco Rose (243 days, new) | Álvaro Arbeloa (207 days, new) | 1.5 / 1.0 |
| Aston Villa v Ipswich | Unai Emery (1,559 days) | Gary O'Neil (221 days, new) | 1.3 / 1.1 |
| Brentford v Man United | Keith Andrews (582 days) | Michael Carrick (382 days) | 1.4 / 0.8 |
| Chelsea v Nott'm Forest | Xabi Alonso (213 days, new) | Oliver Glasner (208 days, new) | 1.6 / 0.9 |
| Coventry v Leeds | Frank Lampard (793 days) | Daniel Farke (1,306 days) | 0.9 / 1.4 |
| Hull v Crystal Palace | Sergej Jakirović (598 days) | Pierre Sage (229 days, new) | 1.1 / 0.7 |
| Liverpool v Everton | Andoni Iraola (240 days, new) | David Moyes (749 days) | 1.8 / 1.6 |
| Man City v Arsenal | Enzo Maresca (215 days, new) | Mikel Arteta (2,596 days) | 2.1 / 2.7 |
| Newcastle v Brighton | Matthias Jaissle (178 days, new) | Fabian Hürzeler (942 days) | 1.2 / 2.2 |
| Tottenham v Sunderland | Roberto De Zerbi (305 days) | Régis Le Bris (943 days) | 1.2 / 0.8 |

"New" means appointed in summer 2026. Tenures are projected to 30 January, assuming no change in the meantime.

- **A manager may still change between the deadline and the match.**
  - Historically, there are on average **1.1** mid-season departures between 21 December and 30 January, and **69% of seasons** have at least one.
  - Between 9 November and 30 January the average is 2.6, and 96% of seasons have at least one.
  - We cannot predict these, but Section 3 shows that even a change has a near-zero effect on individual results. The impact on our predictions is therefore small; one sentence in the Limitations is enough (problem list, P4).
- The clubs in the worst form are Crystal Palace (0.7), Man United and Sunderland (0.8), and Nott'm Forest and Coventry (0.9). A change is most likely at one of these. This is description only: **do not** turn "likely to be sacked" into a feature.
- Palace are also the club in E7 with only two days' rest after a European match. If the report discusses this fixture, any effect should be attributed to the schedule, not the manager. (**Update:** for Champions League clubs, the schedule effect itself was later found to be absent; see E7.)

### 6. Recommendations

1. **Not in the main model.** The evidence is in Sections 3 and 4: the incremental effect of a mid-season change is around zero, and summer changes do not affect rating reliability.
2. **Write it up as a negative result**, which helps the Interest mark. First show the surface pattern (+0.46 points per game after a change), then use Elo residuals and matched controls to show it is regression to the mean. This demonstrates using a model rather than raw points to judge causation.
3. **Use the two side findings elsewhere**: a single league-wide λ for season shrinkage (T4); and since Elo over-reacts to short losing runs, a smaller K and shot information (part O, E3).
4. **If the group still wants to try a feature**, an ablation could add "matches since the new manager took over" (capped at 10). We expect no gain. The table would have to be included in the submission (problem list, X4).

**Reproduction**

```bash
python3 -I e6_manager/e6_manager.py e6_manager/mgr.txt Data_Files/epl-training.csv data_cache/football-data/E0_2627.csv e6_manager
```

- `mgr.txt` is extracted from the PDF with pypdf. The extraction command is in the docstring at the top of the script and in `README.md`, Section 4.
- To change K, edit `K, H = 20.0, 100.0` in the script.
- The random seed is fixed at 0, and the whole script runs in about 2 seconds.

---

## E7. European fixtures ✔ (to 2025/26)

- **Source**:
  - openfootball, a public data project on GitHub: https://github.com/openfootball/champions-league. It has Champions League fixtures and scores for 2011/12 to 2025/26; 2025/26 has 36 teams and 189 matches.
  - The repository was last updated on 2 July 2026 and **does not yet include 2026/27**; that season must be checked on UEFA.com (https://www.uefa.com).
  - Coverage of the Europa League and Conference League on openfootball still needs to be confirmed.
- **Use**: features such as "played a European match in the N days before this league match" and "days of rest since the European match". Fixtures are published in advance, so they are known before kick-off and there is no leakage.
- **2026/27 participants** (from the European records on elofootball's England season page, 10 November 2026; to be cross-checked on UEFA.com):
  - Champions League: Arsenal, Man City, Liverpool, Aston Villa, Man United;
  - Europa League: Bournemouth, Crystal Palace, Sunderland;
  - Conference League: Brighton (including qualifiers).

  That is nine clubs in total.
- **Relevance to the test matches.** In 7 of the 10 test matches at least one side plays in Europe. Verified on 10 November 2026:
  - **Champions League league-phase round 8 is on Wednesday 27 January 2027** (from a UEFA fixture screenshot supplied by a team member);
  - **Europa League round 8 is on Thursday 28 January 2027** (UEFA.com);
  - **the Conference League league phase ends on 17 December 2026**, with play-offs in February (UEFA.com), so Brighton have no European match in January.

| Test match (Sat 30 Jan) | Home side in Europe (late Jan) | Away side in Europe | Rest after Europe | Initial concern level |
|---|---|---|---|---|
| Bournemouth v Fulham | Europa League, Thu 28 Jan, home v Hapoel Beer-Sheva | – | 2 days v 7 | High |
| Aston Villa v Ipswich | Champions League, Wed 27 Jan, **away** v Slavia Praha | – | 3 days (+ Prague trip) v 7 | High |
| Brentford v Man United | – | Champions League, Wed 27 Jan, **away** v Villarreal | 7 v 3 days (+ trip to Spain) | High |
| Chelsea v Nott'm Forest | – | – | 7 v 7 | None |
| Coventry v Leeds | – | – | 7 v 7 | None |
| Hull v Crystal Palace | – | Europa League, Thu 28 Jan, **away** v Salzburg | 7 v **2 days (+ trip to Austria)** | **Highest** |
| Liverpool v Everton | Champions League, Wed 27 Jan, home v Lens | – | 3 days v 7 (city derby) | High |
| Man City v Arsenal | Champions League, Wed 27 Jan, home v Sporting CP | Champions League, Wed 27 Jan, home v Sabah | 3 v 3 (symmetric) | Medium |
| Newcastle v Brighton | – | – (Conference League ended 17 Dec) | 7 v 7 | None |
| Tottenham v Sunderland | – | Europa League, Thu 28 Jan, home v Levski Sofia | 7 v 2 days | High |

- Rest days assume all matches are played on 30 January. openfootball lists every round-23 match at Saturday 15:00, a placeholder before television selections. A club playing in the Europa League on Thursday may be moved to Sunday or Monday. The test file lists every match as 30 Jan 27, so we predict as given, but the report should mention this.
- Late-January load for Europa League clubs: Thursday 21 January (round 7, verified), Saturday 23 January (Premier League round 22), Thursday 28 January and Saturday 30 January, **four matches in ten days**. The date of Champions League round 7 has not been verified.
- Round 8 is the last league-phase round in both the Champions League and the Europa League. How much each club rotates will depend on its standing at that point (direct qualification for the last 16 or a play-off), which cannot be known now.
- **Direct effect on our earlier model.** The rest-day feature in the earlier group-4 script was computed from Premier League matches only. It would **give these clubs 7 days of rest when they actually have 2–3**. A correct computation needs European (and FA Cup and League Cup) fixtures merged in. Historical European fixtures are available from openfootball (Champions League from 2011/12) or from elofootball's club pages (all competitions).

**Update (11 November): the Champions League effect has been tested, and there is none.** Using openfootball's Champions League fixtures for 2011/12 to 2025/26 (CC0), we examined the 2,394 Premier League matches played by clubs in that season's Champions League (`foundation_report.md`, Section 4.4):

| Situation | Matches | Elo residual |
|---|---|---|
| ≤ 3 days' rest after a Champions League match | 163 | +0.024 ± 0.026 |
| No Champions League match in the previous 7 days | 1,801 | −0.014 ± 0.009 |
| Difference | – | **+0.038 ± 0.027** (no fatigue effect) |
| Only one side played midweek (asymmetric case) | 144 | +0.025 ± 0.026 |

- The "high concern" flags in the table above are therefore **not supported by historical data for Champions League clubs** (Arsenal, Man City, Liverpool, Aston Villa, Man United).
- Europa League clubs (Bournemouth, Crystal Palace, Sunderland) have thinner squads and play on Thursday before a Saturday match. But openfootball has no Europa League data, so **this cannot be tested**.
- Decision: no European-fixture feature. The untested Europa League case goes into the report's Limitations.

## E8. Travel distance ✔

- **Source**: the Wikidata SPARQL endpoint https://query.wikidata.org (data licence CC0). Query "home venue (P115) → coordinates (P625)" for each club's stadium. Verified to return coordinates (e.g. City Ground, −1.1328, 52.94).
- **Cautions**:
  - Each club's Wikidata identifier must be checked by hand; in testing, one wrong identifier returned a different club.
  - Clubs that moved ground need date-specific coordinates, e.g. Arsenal 2006, Tottenham at Wembley 2017–2019, West Ham 2016, Everton 2025.
- **Computation**: great-circle (haversine) distance between stadiums, plus optionally a "same-city derby" indicator.
- **Value**: distances within England are short, and the literature usually finds weak effects. But the feature is easy, fully reproducible, and ideal as a small ablation. It is also one of the examples given in the coursework brief.

## E9. Injuries and weather

**Injuries**

- **FPL official API** ✔: https://fantasy.premierleague.com/api/bootstrap-static/
  - On 10 November 2026 it returned 672 players with `status`, `news` and `chance_of_playing_next_round`.
  - 77 players were flagged as injured, doubtful or suspended (e.g. Saka, thigh injury, return date unknown).
- **Fatal problem**:
  - it has **only the current status, no history**, so it can be neither trained nor validated;
  - at submission there are still six weeks to 30 January, and the injury list will be completely different by then.
- **Other sources**: Transfermarkt injury pages (terms problem); premierinjuries.com (commercial, paid, not reproducible).
- **Recommendation**: keep out of the model. Discuss in the report's limitations, or use as a manual sanity check on the final predictions while stating that this is not reproducible.

**Weather**

- **Open-Meteo historical weather API** ✔: https://archive-api.open-meteo.com/v1/archive
  - Based on ERA5 reanalysis; no API key needed.
  - Licence CC BY 4.0 (credit "Weather data by Open-Meteo.com").
  - Verified to return daily mean temperature, precipitation and wind speed for Coventry's coordinates.
- **Fatal problem**: training could use observed weather, but **when predicting the 30 January matches, no forecast for that day exists at the 21 December deadline** (40 days earlier). Training on observations and predicting with climatological averages is inconsistent, another form of information mismatch at test time.
- **Recommendation**: exploratory analysis only (e.g. whether heavy rain or wind reduces goals or increases draws); not in the final model.

## E10. Player ratings 📄

- **Sources**:
  - EA's official ratings page: https://www.ea.com/games/ea-sports-fc/ratings
  - Kaggle datasets by `stefanoleone992` (FIFA 15 to FC 24, with player and team ratings per edition).
  - We found no version from the same author for FC 25 or later. Other versions are third-party scrapes of the EA site of unknown reliability.
  - sofifa.com has historical editions but the same terms problem.
- **Timing**: released each September and updated during the season; using "that season's edition" is known before kick-off.
- **Difficulties**:
  - aggregating player ratings into team strength needs starting line-ups or minutes-weighted averages;
  - squads change after transfer windows;
  - there are no data before 2015;
  - player names must be matched across datasets.
- **Value**: could help the prior for promoted clubs (EA rates Coventry's, Hull's and Ipswich's new signings), but the workload and reproducibility are poor. **Not recommended as a main line.**

---

## Recommended choices

1. **Core (must do)**: E1 + E2. Almost no cost, identical in structure to the training file, and they directly solve two top-priority problems: data ending in May, and cold start for promoted clubs.
2. **Main-line candidates (pick one and go deep)**:
   - E3 xG: real 2026/27 xG plus a historical shots-on-target proxy;
   - or an E2 joint cross-league model.

   Either can be written up as the "interest" element.
3. **Small ablations (easy, extra credit)**:
   - E8 travel distance.
   - E6 manager changes and E7 Champions League congestion have been tested (effects ≈ 0) and are reported as negative results.
4. **Discussion only, not in the model**: E9 injuries and weather (unavailable at test time); E10 player ratings (high cost).
5. **E5 Elo**: replicate elofootball's published method ourselves with E1 + E2 data (reproducible, no terms issues). Use the site's ratings and pre-match probabilities only for checking and as a public benchmark, in the same way that odds-implied probabilities would be used only for comparison.

## Reproducibility requirements (for the notebook and the report)

- For every source, record the URL, download date, licence or terms, number of rows and SHA-256 hash. This is implemented in `data_cache/MANIFEST.csv`.
- The notebook looks for the local cache first and downloads only if it is missing. Small supporting files (stadium coordinates, manager table, team-name mapping) are included as CSVs in the submission. Whether the zip may contain extra files must be confirmed with the lecturer (problem list, X4).
- Every external source goes through the same team-name mapping table, and the match rate is reported after merging.

## Sources

- **Football-Data.co.uk**: https://www.football-data.co.uk/englandm.php, https://www.football-data.co.uk/notes.txt
- **openfootball**: https://github.com/openfootball/england, https://github.com/openfootball/champions-league
- **transfermarkt-datasets**: https://github.com/dcaribou/transfermarkt-datasets
- **elofootball.com**:
  - https://www.elofootball.com/country.php?countryiso=ENG&season=2026-2027
  - method: https://www.elofootball.com/about.php
  - terms: https://www.elofootball.com/impressum_legal_notice.php
- **ClubElo** (a different site, unreachable from our machine): http://clubelo.com
- **FBref's removal of advanced data**:
  - report: https://amp.awfulannouncing.com/soccer/sports-reference-pulls-advanced-data-agreement-violation-dispute.html
  - Sports Reference blog: https://www.sports-reference.com/blog/category/fbref/
- **Understat third-party package**: https://pypi.org/project/understatapi/
- **Wikipedia**: https://en.wikipedia.org/wiki/List_of_Premier_League_managers. Version used: the page stating "up to date as of 8 November 2026", printed to PDF on 10 November 2026; add the oldid when citing.
- **Premier League website**: https://www.premierleague.com/en/managers
- **Manager-change literature** (volume and pages to be verified):
  - Bruinshoofd, A. & ter Weel, B. (2003), "Manager to go? Performance dips reconsidered with evidence from Dutch football", *European Journal of Operational Research* 148(2), 233–246.
  - van Ours, J. C. & van Tuijl, M. A. (2016), "In-season head-coach dismissals and the performance of professional football teams", *Economic Inquiry* 54(1), 591–604.
- **Wikidata SPARQL**: https://query.wikidata.org
- **Open-Meteo licence**: https://open-meteo.com/en/license
- **FPL API**: https://fantasy.premierleague.com/api/bootstrap-static/
- **EA FC ratings**: https://www.ea.com/games/ea-sports-fc/ratings
- **Kaggle FC 24 dataset mirror**: https://baselight.app/u/kaggle/dataset/stefanoleone992_ea_sports_fc_24_complete_player_dataset
- **Second-hand accounts of Transfermarkt's terms**: https://stat.ethz.ch/pipermail/r-package-devel/2018q1/002405.html; soccerdata FAQ: https://soccerdata.readthedocs.io/en/stable/_sources/faq.rst.txt
