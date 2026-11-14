# Data Cleaning: Issues D1–D10

English version of `data_cleaning.md` (11 November 2026).

This document answers Part 1 of the problem list, issues D1 to D10. For each issue it gives what we **found**, exactly **what we did**, how we **verified** it, and what to **say in the report**. Every step has been implemented as a script and run.

**Files**

| Role | Path |
|---|---|
| Script | [cleaning/clean_data.py](cleaning/clean_data.py) |
| Mapping tables | [cleaning/team_names.csv](cleaning/team_names.csv), [cleaning/referee_map.csv](cleaning/referee_map.csv) |
| Cleaned matches | `cleaning/out/matches_clean.csv`: 9,980 matches (9,880 training + 100 from 2026/27) |
| Cleaned test file | `cleaning/out/test_clean.csv` |
| Log | `cleaning/out/cleaning_log.json`: every number in this document comes from here |

**How to run it** (from `Group Coursework/`):

```bash
python3 -I cleaning/clean_data.py Data_Files cleaning/out data_cache/football-data/E0_2627.csv
```

The third argument is the Football-Data.co.uk 2026/27 file. It is optional; without it, only the training file is cleaned.

**How we verified the result.** On 11 November 2026 we re-downloaded all 27 original E0 files for 2000/01 to 2026/27 from Football-Data.co.uk and compared them with the cleaned data match by match and column by column. All 9,980 matches were found, and every numeric value agrees except the five values deliberately set to missing in D6. The training file itself comes from Football-Data.co.uk, so this comparison is used only to **find and verify errors**; it adds no new variables.

---

## Summary

| ID | Issue | Finding | Action | Rows affected |
|---|---|---|---|---|
| D1 | Blank row | Line 5702 is empty (between 2014/15 and 2015/16) | Delete | 1 |
| **D2** | Duplicate rows | The first 100 matches of 2023/24 appear twice. **Worse**: from the second copy to the end of the file, **the corner and foul columns are swapped** (HC↔HF, AC↔AF) | Keep the first copy; swap the columns back in the 1,040 remaining rows | 100 deleted, 1,040 fixed |
| D3 | Date formats | Training file uses `dd/mm/yyyy`; test file uses `30 Jan 27` | Parse each with an explicit format | All |
| D4 | Season boundaries | 2019/20 finished on 26 July 2020 | A season starts in August; assert 380 matches per season | All |
| D5 | Logical consistency | All eight checks pass | Written as assertions, checked on every run | 0 |
| D6 | Shots on target > shots | 5 values in 3 matches; the official files contain the same values | Set to missing and flag; keep the 51 matches where goals exceed shots on target (own goals) | 3 |
| D7 | Referee names | 190 spellings | Rule-based normalisation plus 10 manual mappings: 84 referees | All |
| D8 | Outliers and definitions | Extreme values are all real matches. **The definition of shots on target changes in 2013/14** (on-target share drops from 0.57 to 0.33) | No deletion or trimming; add an `era_sot` flag; standardise shot features within season | 0 |
| D9 | Team names | Test file uses `Ipswich Town` and `Nottingham Forest` | Central mapping table; submit with the original names | 2 names |
| D10 | Data end on 24 May 2026 | 100 matches of 2026/27 available (to 8 November) | Append from the same source, drop odds columns, run the same checks | +100 rows |
| Extra | Found in the comparison with the official files | Two single-value differences: one half-time score, one referee | Patch to the official value, record in the log | 2 |

**Order of execution**: D1 → D3 → D2 → D4 → patches → D5 → D6 → D7 → D8 → D9 → D10.

The order matters:
- D2 needs parsed dates to find duplicates by key.
- The D5 assertions must run after every modification.
- The D9 name mapping must be in place before D10 appends new data, so that both parts use the same table.

---

## Step 0: Reading and record-keeping (prerequisite for everything)

**What we did**

1. Read every column **as text** (`dtype=str, keep_default_na=False`). pandas is not allowed to infer types, so stray spaces and empty strings stay visible.
2. Assert that the header is exactly the expected 22 columns, `Date` … `AR`, in order.
3. Record the original line number of every row as `src_row` (the header is line 1). All log entries refer to this number, so teammates can check any row in the raw file.
4. Compute and record the SHA-256 of each input file:
   - `epl-training.csv`: `ebed6cb2…ed3b`
   - `epl-test.csv`: `d3b3b5ee…acf3a`
   - `E0_2627.csv` (downloaded 11 November 2026): `d598a5f6…4593`

   The full values are in the log. If a teammate's or the lecturer's file has a different hash, every line number may differ, so check this first.
5. Results of the file-format check:
   - UTF-8, no BOM, `\n` line endings, final newline present;
   - no stray spaces in team names, FTR or HTR;
   - 22 referee values have leading or trailing spaces (see D7).

---

## D1. Blank row

**Finding**

- The raw training file has 9,981 data rows. Line 5702 is empty in all 22 columns.
- It sits exactly between the last day of 2014/15 (24 May 2015) and the first day of 2015/16 (8 August 2015), so it was probably carried over when the season files were concatenated. The official `1415/E0.csv` also ends with a blank line, which supports this.
- There are no partially empty rows (asserted in the script), and no missing values anywhere else in the file.

**What we did**

1. Find fully empty rows with `(raw[CORE] == '').all(axis=1)`, record their line numbers, and delete them.
2. Assert that no partially empty row exists. If one ever appears, the script stops and leaves it for a person to decide. **Nothing is filled in automatically.**
3. We deliberately do **not** use `dropna(subset=["FTR"])`. It looks at one column only and would silently drop a broken row that has FTR missing but other values present, without telling us.

**Verification**: 9,980 rows remain; the log field is `D1_blank_rows_src_line = [5702]`.

**Report**: one sentence.

---

## D2. Duplicate rows, and swapped corner and foul columns (new finding)

**Finding**

1. 2023/24 has 480 rows instead of 380:
   - Lines 8743–8842 are the first 100 matches of the season (11 August to 29 October 2023).
   - From line 8843 onwards, **the whole of 2023/24 is listed again from 11 August** (380 matches), so the first 100 matches appear twice.
   - The only backwards jump in dates in the whole file (29 October → 11 August) is at this point.
2. The two copies are **not identical**. Of the 100 duplicate pairs, 95–96 differ in HC, AC, HF and AF, and one differs in the referee.
3. Comparison with the official `2324/E0.csv` shows that **the first copy is correct** and **the second copy has the corner and foul columns swapped**, for both home and away teams.
4. The problem does not stop at the duplicates. **All 1,140 rows from line 8843 to the end of the file** (all of 2023/24, 2024/25 and 2025/26) are swapped:
   - 1,138 rows are exactly swapped;
   - the other 2 happen to have HC = HF and AC = AF, so a swap makes no difference;
   - all 8,840 rows before line 8843 agree with the official files.
5. The error is visible from the training file alone:

| Season | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 |
|---|---|---|---|---|---|
| Home corners per match, raw file | 5.6 | 5.6 | 9.4 | 10.8 | 10.7 |
| Home fouls per match, raw file | 10.1 | 10.6 | 7.4 | 5.4 | 5.4 |
| Home corners per match, fixed | 5.6 | 5.6 | 6.1 | 5.4 | 5.4 |
| Home fouls per match, fixed | 10.1 | 10.6 | 10.7 | 10.8 | 10.7 |

   The raw 2023/24 values lie in between because its first 100 matches are correct and the remaining 280 are swapped.

**Impact.** Any feature based on corners or fouls (for example "average corners over the last five matches") would be completely wrong for the three most recent seasons. Those are exactly the seasons that matter most for predicting 2026/27. Models that use only goals and shots are unaffected. Any earlier script that read HC, HF, AC or AF directly from the raw training file must be switched to the cleaned file.

**What we did**

1. Find duplicates by the key (Date, HomeTeam, AwayTeam) with `duplicated(KEY, keep='first')`, which finds 100 rows. Record the **line number of the first duplicate** (8843) as the start of the swapped block. This start is computed from the data, not hard-coded.
2. Check the **two copies against each other** first. After swapping the second copy's columns back, the two copies differ in only one referee value (step 5). So the swap explains every difference between them.
3. Delete the second copy, keeping the copy with the smaller line number.
4. In every remaining row with `src_row ≥ 8843` (1,040 rows), swap `HC` with `HF` and `AC` with `AF`.
5. The one referee difference, 29 October 2023 Liverpool v Nott'm Forest: the first copy says `C Salisbury`, while the second copy and the official file say `C Kavanagh`. It is corrected to `C Kavanagh` by a patch (see "Patches").
6. In D10, a guard assertion requires that newly appended data have fewer corners than fouls per match on average, so the same error cannot slip in again.

```python
dupmask = d.duplicated(KEY, keep='first')
first_dup_line = d.loc[dupmask, 'src_row'].min()          # 8843
d = d[~dupmask].copy()
swap = d.src_row >= first_dup_line
d.loc[swap, ['HC', 'HF', 'AC', 'AF']] = d.loc[swap, ['HF', 'HC', 'AF', 'AC']].to_numpy()
```

**Verification**

- 380 matches per season, 38 per team per season, 20 teams.
- Each fixture appears only once per season.
- After the fix, corners and fouls agree with the official files match by match.

**Report.** This deserves a place in the data part of the Methodology as a data-quality finding, perhaps with a small figure of corners and fouls per match before and after the fix. It shows directly that we checked the data rather than using it as given, which the marking scheme values under both Methodology and Interest.

---

## D3. Date formats

**Finding**

- All 9,980 training rows use `dd/mm/yyyy` with a four-digit year.
- The test file and the sample submission use `30 Jan 27`, i.e. `%d %b %y` with a two-digit year.
- The new Football-Data.co.uk file (2026/27) also uses `dd/mm/yyyy`. Some older official files use two-digit years, which matters if we ever read historical official files directly.
- Dates in the training file increase throughout, except for the single backwards jump caused by D2.

**What we did**

1. Assert the format with a regular expression first: `\d{2}/\d{2}/\d{4}` for training, `\d{1,2} [A-Z][a-z]{2} \d{2}` for test.
2. Parse with explicit formats: `format='%d/%m/%Y'` for training and `format='%d %b %y'` for test. We do **not** use `dayfirst=True` or automatic inference: `03/04/2021` can be read as 3 April or 4 March depending on the method, without any error.
3. Python parses the two-digit year `27` as 2027. Verified: `test.Date_parsed = 2027-01-30`.
4. The test file **keeps its original string column `Date`** and stores the parsed date separately as `Date_parsed`. The submission writes back the original string, so its format matches the sample submission character for character.
5. Output CSVs write all dates in ISO format (`%Y-%m-%d`), so later reads are unambiguous.

**Verification**: training dates run from 19 August 2000 to 24 May 2026; all 10 test matches are on 30 January 2027.

---

## D4. Season boundaries

**Finding**

- 2019/20 was suspended because of COVID-19 and finished on **26 July 2020**; 2020/21 started on 12 September 2020.
- A rule that starts a new season on 1 July would therefore put the 66 matches of July 2020 into 2020/21.
- The training file has 26 matches in June and 66 in July, all belonging to 2019/20.
- Every other season starts in August (earliest 5 August 2022) and ends in May (latest 28 May 2023).

**What we did**

1. `season = year` if the month is August or later, otherwise `year − 1`. 2019/20 is stored as 2019, 2026/27 as 2026.
2. Add a readable label `season_label`, for example `2019/20`.
3. Assert exactly 380 matches and 20 teams for each completed season. 2026/27 is incomplete: it is checked separately in D10, and any code that assumes 380 matches per season must exclude the current season.
4. Note that the manager analysis (E6) and elofootball both use 1 July to 30 June seasons. In our data the two rules disagree only for July 2020. When merging external data, always use our `season`.

**Verification**: 26 seasons from 2000/01 to 2025/26, each with 380 matches.

---

## Patches: single-value differences found against the official files

After the D2 fix, only two value differences remain between the training file and the official files:

| Match | Column | Training file | Official | Action |
|---|---|---|---|---|
| 10 March 2022, Wolves v Watford (4-0) | HTHG | 2 | 3 | Set to 3. The half-time result HTR = H is unchanged |
| 29 October 2023, Liverpool v Nott'm Forest | Referee | C Salisbury | C Kavanagh | Set to C Kavanagh (the second copy in the training file also says so) |

**What we did**

- The patches are written as a list. Each entry records the date, fixture, column, old value, new value and evidence.
- Before each patch is applied, the script **asserts that the old value is the expected one**. If the file ever changes, the script fails instead of changing the wrong cell.
- All patches are written to the `patches` field of the log.

The referee column also has differences that are only invisible characters. These are handled in D7 and do not count as value differences:
- on 23 April 2005 (9 matches) the training file has `†` before the name where the official file has a non-breaking space `\xa0`;
- 22 values have leading or trailing spaces.

**Report**: can be combined with D2, e.g. "after checking against the original source we corrected 1,040 swapped rows and 2 single values".

---

## D5. Logical consistency checks

**What we did.** After all modifications, the following eight conditions are **hard assertions** (`assert`). If any fails, the script stops.

1. FTR agrees with the full-time score.
2. HTR agrees with the half-time score.
3. Half-time goals do not exceed full-time goals, for each side.
4. None of the 16 numeric columns is negative, and all values are integers (enforced with `astype(int)` on reading).
5. Home team differs from away team.
6. Each (home, away) pair appears at most once per season.
7. No team plays twice on the same day.
8. Each team plays exactly 38 matches per season (home and away together).

**Result**: all pass (log field `D5_checks`). The appended 2026/27 data are also checked against conditions 1–2 and for duplicates.

**Why assertions rather than a one-off check?** The data will be refreshed (D10) and the name mapping may change (D9). Assertions guarantee that every future run still satisfies these conditions.

---

## D6. Shots on target exceeding shots

**Finding.** Five values in three matches are impossible. The official source files contain the same values, so these are data-entry errors at the source.

| Match | Home shots / on target | Away shots / on target | Score |
|---|---|---|---|
| 14 October 2000, Coventry v Tottenham | **0 / 5** | **4 / 5** | 2-1 |
| 13 April 2001, Bradford v Charlton | **4 / 8** | **3 / 8** | 2-0 |
| 15 August 2021, Newcastle v West Ham | 17 / 3 | **8 / 9** | 2-4 |

The 51 matches where **goals exceed shots on target are plausible**, because own goals do not count as shots. For example, on 28 December 2004 West Brom drew 1-1 at Man City with zero shots. These 51 matches are flagged but keep their original values.

**Options considered**

- **Drop the match**: rejected. It would lose a real result, which Elo and league points both need.
- **Swap the two columns**: plausible for Bradford (4/8 → 8/4) but not for Coventry (after swapping, 5 shots and 0 on target, yet 2 goals). There is no consistent rule, only guessing.
- **Cap shots on target at shots**: this invents a number.
- **Set to missing (adopted)**: only the offending side's shots and shots on target are set to missing; the other side's valid values are kept.

**What we did**

1. Check `HST > HS` and `AST > AS` separately. For the offending side, set both the shots and shots-on-target values to missing. These columns become nullable integers (`Int64`).
2. Add a `flag_shots` column recording which side was set to missing, for example `home:SOT>S;`.
3. Add a `flag_goals_gt_sot` column marking the 51 matches with more goals than shots on target, without changing their values.
4. Downstream features, such as average shots over the last N matches, must use means that skip missing values (the pandas default). Only 5 of about 20,000 team-match shot values over 26 seasons are missing, so the effect is negligible.

**Report**: one sentence, stating that we followed the principle of not inventing data.

---

## D7. Referee names

**Finding.** There are 190 spellings for 84 people, mostly from the inconsistent formats of 2000/01 to 2002/03:

- full names: `Alan Wiley`, `Dermot Gallagher`;
- middle initials: `A. G. Wiley`, `A.G. Wiley`;
- surname first: `Wiley, A. G.`, `Dean, M. L`;
- leading or trailing spaces: `P. Jones ` (22 values);
- invisible characters: `†U Rennie`, `\xa0C Foy`;
- typos and truncations: `D Gallaghe`, `D Gallagh`, `Mn Atkinson`, `St Bennett`, `l Mason`, `O Oliver`, `K Kavanagh`.

**What we did**

1. **Rule-based normalisation** (function `ref_key`):
   1. Apply Unicode NFKC normalisation, remove `†` and non-breaking spaces, strip leading and trailing spaces, and collapse repeated spaces.
   2. If there is a comma (surname first), turn "Surname, Given" into "Given Surname".
   3. Remove full stops, split on spaces, and use "first initial + space + surname" as the key, so `A. G. Wiley` becomes `A Wiley`.

   This step reduces the 190 spellings to 92 keys.
2. **Manual mappings** ([cleaning/referee_map.csv](cleaning/referee_map.csv)): 10 entries, each with a confidence level and a reason.
   - **6 high-confidence entries**:
     - truncated names (two for Gallagher);
     - cases where only one active referee had that surname at the time and the spelling occurs in a single match (`O Oliver` → `M Oliver`, `K Kavanagh` → `C Kavanagh`);
     - a few identity mappings for confirmation.
   - **2 medium-confidence entries**: `A Moss` → `J Moss` (2020/21, 1 match) and `S Scott` → `G Scott` (2019/20, 1 match).
   - **Not merged** where we are not sure enough, e.g. `Ian Harris` and `Rob Harris` in 2000/01, or `F Taylor` and `Paul Taylor`.
3. Keep the original value in `Referee_raw` for checking.
4. Different people with the same surname must **not** be merged on surname alone. `A Taylor` and `P Taylor`, `M Oliver`, `M Salisbury`, `R Madley` and `A Madley`, `L Smith` and `J Smith` are all different referees, so the key must keep the initial.

**Result**: 84 referees in the training data, 25 of whom officiated fewer than 20 matches. 2026/27 adds one new referee, A Herczeg.

**Recommendation**

- Referees are a low-value feature (problem list, part F). If used, referees with fewer than 20 matches should be pooled as "Other", and the remaining averages shrunk towards the league average by empirical Bayes.
- Any referee statistic may use only matches before the match date.
- Most importantly, **the test file has no referee information**, and the referees for 30 January will not be announced before the deadline. Referees therefore **cannot be prediction features**; at most they help explain the training data. The Feature section of the report should state this as the reason for excluding them.

---

## D8. Outliers in other columns, and changes of definition

**What we did**

1. For each of the 16 numeric columns, compute the minimum, 0.1% quantile, median, 99.9% quantile and maximum, and look at the most extreme match.
2. Compute per-season means and **the share of shots that are on target**, to detect changes of definition.
3. Count values above Q3 + 3 × IQR for reference. For small counts such as cards this rule is meaningless (the IQR of red cards is 0), so for those we look only at the maximum and the distribution.

**The extreme values are all real matches. Nothing is deleted or trimmed.**

| Variable | Maximum | Match |
|---|---|---|
| Goals | 9 | e.g. 25 October 2019 Southampton 0-9 Leicester; 2 February 2021 Man United 9-0 Southampton |
| Home shots | 43 | 21 March 2015, Man City v West Brom |
| Away shots | 37 | 18 January 2025, Brentford v Liverpool |
| Fouls | 33 | 25 November 2007, West Ham v Tottenham |
| Red cards | 3 | 2 April 2005, Newcastle v Aston Villa (two Newcastle players fought each other) |

Trimming would distort count-based models such as the Poisson model, and rolling-average features already dampen single extreme matches.

**A break in the definition of shots on target (important)**

| Seasons | 2000/01–2001/02 | 2002/03–2012/13 | **2013/14 onwards** |
|---|---|---|---|
| Share of shots on target | 0.47–0.48 | 0.51–0.57 | **0.32–0.36** |

- Between 2012/13 and 2013/14 the share falls from 0.566 to 0.332, while the total number of shots barely changes. Football does not change that much in one year: **the definition of a shot on target, or the data provider, changed**. Football-Data's notes.txt gives no reason, so the report should simply say "a break in definition, cause not published".
- The match statistics for 2000/01 and 2001/02 came from a different provider, Sports.com (notes.txt, line 202). Their share is also slightly lower, possibly a second, smaller definitional difference.
- Yellow cards rise around 2016/17 and 2023/24, consistent with rule changes such as the 2023/24 clampdown on time-wasting and dissent. These are real changes. Fouls fall slowly from about 13 to 10–11 per match, a gradual trend rather than a break.

**How we handle it**

1. Leave the values unchanged and add an `era_sot` column (`pre2013` / `post2013`).
2. **Standardise shot-based features within each season** (shots, shots on target, on-target share, any shots-on-target xG proxy), taking that season's league average as the reference, by difference or ratio. Alternatively, estimate models that use shots on target on 2013/14 onwards only.
3. Optionally run a small ablation comparing features with and without standardisation, as an evaluation result.
4. The test season 2026/27 belongs to the `post2013` definition (on-target share 0.31, home shots on target 4.7 per match), so it is comparable with the last 13 seasons.

**Report**: worth including in the Methodology. It shows we noticed the non-stationarity of the data (problem list, part T).

---

## D9. Team names

**Finding**

- The training file has 46 teams, using Football-Data's short names (`Man United`, `Nott'm Forest`, `Wolves`).
- Two of the 20 teams in the test file are written differently: `Ipswich Town` (training: `Ipswich`) and `Nottingham Forest` (training: `Nott'm Forest`).
- `Man United`, `Man City`, `Hull` and `Coventry` are written the same way in both files.
- External data use even more variants:
  - Wikipedia uses full names such as `Manchester United`, `Wolverhampton Wanderers`, `Brighton & Hove Albion`;
  - other sources often use `Man Utd` or `Spurs`;
  - the Championship contains clubs never seen in the training file (Wrexham, Millwall, Preston and others).

**What we did**

1. **The Football-Data short names in the training file are the single canonical names.** Football-Data's Championship file (E1) uses the same convention, so the joint modelling planned in E2 can use them directly.
2. Build the mapping table [cleaning/team_names.csv](cleaning/team_names.csv) with 52 clubs and three columns: canonical name, full name, aliases separated by `|`. It covers:
   - the 46 training-file teams;
   - the extra 2025/26 Championship clubs Bristol City, Millwall, Oxford, Preston and Wrexham;
   - the test-file spellings and common external spellings.
3. When the table is loaded, check for **alias conflicts**: no alias may point to two clubs.
4. During mapping, **an unknown name raises an error** (dictionary lookup with `[]`). We do **not** use `.get(x, x)`, which would let an unknown name through unchanged. It would then be treated as a "new club", Elo would start it from the initial rating, and nothing would warn us.
5. The test file also keeps the original names in `HomeTeam_orig` and `AwayTeam_orig`. **The submission is written with the original names and the original date string**, and the script asserts that its first three columns are identical to `epl-test.csv`, as required in part P of the problem list.
6. Whenever an external source is connected (elofootball, Wikipedia, openfootball, FPL, …), all its team names are added to the mapping table first and the match rate is reported, with 100% as the target. The manager data (E6) already reach 46/46.

**Verification**: every team name in the training data, 2026/27 and the test file can be mapped. All 20 test teams have 2026/27 matches (log field `D10_test_teams_without_2026_27_data = []`).

---

## D10. Training data end on 24 May 2026

**Finding**

- Football-Data's `mmz4281/2627/E0.csv` (downloaded 11 November 2026) contains **100 matches** (21 August to 8 November 2026, 10 per team) and 114 columns.
- Its 22 core columns are identical to the training file. It adds:
  - `Div` and `Time` (kick-off time);
  - `HxG` and `AxG` (this season only);
  - about 90 **odds columns**, which rule R3 requires us to remove.
- No match overlaps with the training file.
- All quality checks pass: scores agree with results, shots on target never exceed shots, and there are no duplicates. Corners average 5.0 and fouls 11.2 per match, so the columns are not swapped.
- The promoted clubs have gaps in their Premier League history: Coventry last played in it in 2000/01, Hull in 2016/17 and Ipswich in 2024/25. This is the cold-start problem (problem list, part C), solved with Championship data (E2), not a cleaning issue.

**What we did**

1. Download the file, record its SHA-256 and the download date, and keep a local cached copy. The notebook looks for the cached copy first and downloads only if it is missing (problem list, part S).
2. **Keep only** the 22 core columns plus `Time`, `HxG` and `AxG`; drop everything else. Because this is a whitelist, any odds columns added to the file in future cannot slip in.
3. Run the same pipeline:
   - parse dates with `%d/%m/%Y`;
   - convert numeric columns to integers;
   - compute the season with the D4 rule (label `2026/27`);
   - process referees as in D7 and team names as in D9.
4. Assertions:
   - the earliest new date is after the last training date;
   - no duplicates;
   - FTR and HTR agree with the scores;
   - shots on target never exceed shots;
   - average corners are below average fouls (the guard against the D2 swap).
5. Add a `source` column (`epl-training.csv` / `E0_2627.csv`), sort by date and create `match_id`.
6. **Columns the training file lacks are not back-filled.** `Time`, `HxG` and `AxG` are empty before 2026/27, so any xG-based feature can only be used within 2026/27 (see E3 in the external-data notes).
7. **Re-run once more shortly before the deadline.** In mid-December, re-download (about 160 matches should be available), re-run the whole pipeline, and state the snapshot date in the report. Rounds 17–22 (about 60 matches) will not have been played by the deadline. That is the forecast-horizon problem (problem list, V7), not a cleaning issue.
8. Any code that assumes 380 matches per season (end-of-season points, season-based validation splits) must treat the incomplete 2026/27 separately.

**Verification**: 9,980 rows after merging. Rows per season are in the log field `rows_per_season`; 2026/27 has 100.

---

## Columns of the output file (`matches_clean.csv`)

| Column | Meaning |
|---|---|
| `match_id` | Sequence number after sorting by date |
| `season`, `season_label` | e.g. 2019 / `2019/20` (D4) |
| `Date`, `Time` | ISO date; kick-off time only in 2026/27 |
| `HomeTeam`, `AwayTeam` | Canonical team names (D9) |
| `FTHG` … `AR` | The original 22 columns, with the D2 swap, patches and D6 missing values applied |
| `Referee`, `Referee_raw` | Normalised and original referee name (D7) |
| `HxG`, `AxG` | 2026/27 only |
| `era_sot` | Shots-on-target definition era (D8) |
| `flag_shots`, `flag_goals_gt_sot` | D6 flags |
| `closed` | 1 for matches played behind closed doors (17 June 2020 – 16 May 2021) |
| `source`, `src_row` | Source file and original line number, so any row can be traced back |

---

## Paragraph for the report (Data section)

```latex
\paragraph{Data cleaning.}
We validated the provided training file against the original Football-Data.co.uk
season files and found three issues beyond a single blank row. First, the first 100
matches of 2023/24 appear twice; the second copy, and every row after it (1,040 matches
from 2023/24 to 2025/26), has the corner and foul columns swapped (HC$\leftrightarrow$HF,
AC$\leftrightarrow$AF), which raises the mean home corners per match from 5.6 to 10.8.
We kept the first copy and swapped the columns back. Second, three matches record more
shots on target than shots; as no correction rule is consistent with the scores, we set
these values to missing. Third, the proportion of shots that are on target drops from
0.57 in 2012/13 to 0.33 in 2013/14 with no change in total shots, indicating a change of
definition; shot-based features are therefore standardised within each season. Referee
names (190 spellings, 84 referees) and team names were mapped to canonical forms, and
the 2026/27 matches played so far were appended from the same source after removing all
betting-odds columns. All checks are implemented as assertions in the notebook.
```

---

## Still to be decided or confirmed by the group

1. **D6**: does the group accept setting the values to missing? Swapping the columns for the Bradford match is an alternative, but we do not recommend it.
2. **D7**: the two medium-confidence mappings (Moss, Scott). Referees are not used in the model, so their impact is minimal.
3. **D2 must be communicated to everyone**: any earlier analysis that used corners or fouls has to be re-run on the cleaned file.
4. Does correcting the training file against the official files count as "using external data"? We consider it data validation, since it adds no new variables. To be safe, the report can say so, and we can also ask the lecturer, together with problem-list item X4.
