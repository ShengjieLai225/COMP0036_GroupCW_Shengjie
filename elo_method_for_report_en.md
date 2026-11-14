# Elo Ratings: Method Notes for the Report

English version of `elo_method_for_report.md`. First written 10 November 2026; updated 14 November 2026 with the tuned parameters from `time_structure.md`.

**Sources.** The method below follows the "about" page of elofootball.com, whose author states that he adopts the formulae of eloratings.net, and the "about" page of eloratings.net itself. Both pages were downloaded and checked on 10 November 2026.

**Which site?** elofootball.com (Erik Pfeiffer) and clubelo.com are two different sites with different formulas and different numbers. We replicate **elofootball.com**. clubelo.com could not be reached from our machine in November 2026 (API 502, home page 403), so we do not use it. The report should never refer to the two interchangeably.

---

## 1. The method, step by step

### 1.1 Expected score (not a win probability)

$$E_h=\frac{1}{1+10^{-d/400}},\qquad d=R_h+H-R_a$$

- $R_h$ and $R_a$ are the pre-match ratings, and $H$ is the home advantage in rating points. Both elofootball and eloratings.net use **H = 100**.
- **$E_h$ is an expected score in which a draw counts as half a point. It is not the probability of a home win.** $E_h = 0.6$ means $P(H)+\tfrac12P(D)=0.6$. The report must keep this distinction; confusing the two is a common mistake.
- A rating gap of 400 points corresponds to expected-score odds of 10:1, i.e. $E_h\approx0.909$.

### 1.2 Update after the match

$$R_h' = R_h + K\cdot G\cdot(S_h-E_h),\qquad R_a' = R_a - K\cdot G\cdot(S_h-E_h)$$

- $S_h$ is 1 for a home win, 0.5 for a draw and 0 for a home loss.
- Both teams change by the same amount in opposite directions. The update is **zero-sum**, so the mean rating of a closed league does not change.
- **$K$ is the step size.** elofootball currently uses:
  - 20 for domestic league, cup, super-cup and play-off matches;
  - 15 for the league cup;
  - 30 for the Champions League, 25 for the Europa League and 20 for the Conference League.

  The author compared $K\in\{5,10,\dots,50\}$ by least squares on samples of 1,000 to 50,000 matches. With 10,000 or more matches the error was smallest at about $K = 15$, and he lowered $K$ accordingly.
- **$G$ is the goal-difference multiplier.** In the wording of eloratings.net, $K$ is increased by half for a two-goal win, by three quarters for a three-goal win, and by $3/4+(N-3)/8$ for wins by four or more goals. In closed form:

$$G(N)=\begin{cases}1 & N\le1\\ 3/2 & N=2\\ (11+N)/8 & N\ge3\end{cases}$$

  Check: $N=3$ gives $14/8=1.75$, and $N=4$ gives $15/8=1.875=1.75+1/8$, which matches the original wording.

### 1.3 Link to statistical learning (a point of depth for the report)

- The update is **one stochastic-gradient step** on the squared error of the expected score. Each match corrects the ratings in proportion to the error $S_h-E_h$, and $K$ is the learning rate.
- The rating model of Berrar et al. (2019) has the same structure, except that it uses the error in goals while Elo uses the error in results.
- A large $K$ reacts quickly to recent form but is noisy; a small $K$ is stable but slow. This is a bias–variance trade-off, and it plays the same role as the half-life $\xi$ of Dixon–Coles time weighting.

### 1.4 New clubs and promotion

- On elofootball, a club joining a league starts at **the average rating of the clubs relegated from that league in the previous season**. A relegated club keeps its rating until it is promoted again or meets a rated club in a cup.
- elofootball covers English football down to the fifth tier, so Coventry, Hull and Ipswich have continuous rating histories.
- Seasons run from 1 July to 30 June.
- **The site does not regress ratings between seasons**; ratings carry over the summer unchanged.

### 1.5 What the site does not explain

- **How the draw probability is obtained is not published.** The about page gives only the two-way expected score $E_h$. The site's three-way probabilities therefore cannot be reproduced from the formulas, and we have to build our own mapping from $d$ to (H, D, A).

---

## 2. Our replication and extensions (for the Methodology section)

1. **Data.** We use Football-Data.co.uk Premier League (E0) results. Championship (E1) results are the next step: processed together in date order, they will let promoted clubs carry ratings earned in the second tier. Coventry's rating, for example, would then come from its Championship matches. The first available Championship season still needs to be checked.
2. **Initialisation.** All clubs in the first season start at 1500. A club entering later starts at the mean rating of the previous season's three relegated clubs. The first five seasons serve as a burn-in and are not used for evaluation.
3. **Season shrinkage** (our extension; the site has none). At the start of each season, $R_i\leftarrow\lambda R_i+(1-\lambda)\bar R$. This reflects the uncertainty created by summer transfers and manager changes.
4. **Three-way probabilities from an ordered logit.** The categories are ordered H < D < A, the same order the RPS uses:

$$P(\text{H})=\sigma(\beta d-\theta_1),\qquad P(\text{H}\cup\text{D})=\sigma(\beta d-\theta_2),\qquad \theta_1>\theta_2$$

   $P(\text{D})$ and $P(\text{A})$ follow by subtraction. The three parameters $(\beta,\theta_1,\theta_2)$ are estimated by maximum likelihood on the five seasons before each evaluation season.
5. **Hyperparameters.** $K$, $H$ and $\lambda$ are chosen in **walk-forward validation**, using only seasons before the one being evaluated, with RPS as the criterion. The site's values ($K=20$, $H=100$) are the starting point and the comparison.
   - **Result (see `time_structure_en.md`, T4):** nested selection picks **K = 15, H = 65, λ = 0.9** in almost every season.
   - The difference from the published setting is not significant.
   - K = 15 agrees with the site author's own experiments, and H = 65 agrees with the decline in home advantage (T1).
6. **No leakage.** Each match is predicted with pre-match ratings only; ratings are updated after the match.
7. **Check against the site.** On the 100 Premier League matches of 2026/27 played by 8 November 2026:

| Model | RPS |
|---|---|
| Our replicated Elo | 0.2077 ± 0.0123 |
| The site's pre-match probabilities | 0.2118 |
| Frequency baseline | 0.2290 |

   With only 100 matches the two Elo systems are at the same level; both are clearly better than the baseline.

The implementation is `run_elo()` in `time_structure/t_elo.py`.

---

## 3. LaTeX ready to paste

```latex
\subsection{Elo ratings}
We maintain a rating $R_i$ for every club and process matches in chronological
order. Following the club-level adaptation at elofootball.com, which in turn
adopts the formulae of eloratings.net, the expected score of the home team is
\begin{equation}
  E_h = \frac{1}{1 + 10^{-d/400}}, \qquad d = R_h + H - R_a ,
\end{equation}
where $H$ is the home advantage in rating points. Note that $E_h$ is an
\emph{expected score}, counting a draw as half a win, i.e.\
$E_h = P(\mathrm{H}) + \tfrac12 P(\mathrm{D})$; it is not a win probability.
After the match, both ratings are updated by the same amount in opposite
directions,
\begin{equation}
  R_h \leftarrow R_h + K\,G(N)\,(S_h - E_h), \qquad
  R_a \leftarrow R_a - K\,G(N)\,(S_h - E_h),
\end{equation}
where $S_h \in \{1, \tfrac12, 0\}$ is the result for the home team, $K$ is
a step size, and $G(N)$ is a goal-difference multiplier with $G(N)=1$ for
$N \le 1$, $G(2)=3/2$ and $G(N)=(11+N)/8$ for $N \ge 3$. The update is a
single stochastic-gradient step on the squared error of the expected score,
so $K$ plays the role of a learning rate and controls how quickly ratings
react to recent form.

We extend the published method in three ways. First, we run the system
jointly on Premier League and Championship matches, so that promoted clubs
carry ratings earned in the second tier rather than starting cold. Second,
at the start of each season we shrink ratings towards the mean,
$R_i \leftarrow \lambda R_i + (1-\lambda)\bar R$, to reflect squad changes
over the summer. Third, because the published method gives no rule for the
probability of a draw, we map the rating difference $d$ to three outcome
probabilities with an ordered logistic model,
\begin{equation}
  P(\mathrm{H}) = \sigma(\beta d - \theta_1), \qquad
  P(\mathrm{H} \cup \mathrm{D}) = \sigma(\beta d - \theta_2), \qquad
  \theta_1 > \theta_2 ,
\end{equation}
fitted by maximum likelihood on the training seasons. The hyperparameters
$K$, $H$ and $\lambda$ are chosen by walk-forward validation on seasons
preceding each evaluation season, starting from the published values
$K = 20$ and $H = 100$.
```

**Before pasting:** the first extension, joint Championship modelling, is still to be done. Until it is, either delete that sentence or rewrite it as future work.

---

## 4. References

The IEEE-formatted entries are in `report/references.bib`:

| Key | Reference |
|---|---|
| `elo1978` | Elo, *The Rating of Chessplayers, Past and Present*, 1978 |
| `elofootball` | elofootball.com method page, accessed 10 November 2026 |
| `eloratings` | eloratings.net about page, accessed 10 November 2026 |
| `hvattum2010` | Hvattum & Arntzen, "Using ELO ratings for match result prediction in association football," *Int. J. Forecasting* 26(3), 2010 |
| `berrar2019` | Berrar, Lopes & Dubitzky, "Incorporating domain knowledge in machine learning for soccer outcome prediction," *Machine Learning* 108(1), 2019 |

Hvattum & Arntzen (2010) is the standard reference for feeding Elo differences into an ordered logit to predict football results, which is exactly our step 4. The volume and page numbers were written from memory, so **check them against the publisher's page before submission**.
