# Kramnik Anomaly Method

A statistical analysis tool for analyzing chess player performance against different rating bands, inspired by Vladimir Kramnik's approach to detecting rating anomalies.

## Interesting Statistics

### Initial reproduction
My primary goal was to reproduce analysis on `shimastream` and I succeeded:

```
Performance vs bands:
band  games  score  avg_opp   perf
 500     94   56.0   2542.4 2609.8
 600     41   18.0   2637.1 2594.5
 700     54   24.5   2732.5 2700.3
800+     17    1.5   2844.3 2438.6
```

* "Band" means buckets by FIDE Blitz ratings: 2500-2600, 2600-2700, 2700-2800, 2800+. Originally "500" bucket wasn't taken but I added it to get more observations.
* "Games" means number of Titled Tuesday games in each bucket.
* "Score" is total score where +1 is a win, +0.5 is a draw, 0 is loss.
* "avg_opp" is the average FIDE rating of opponent over all games.
* "perf" is the evaluated rating of the measured player, based on Elo formula and FIDE ratings of opponents.

The original claim was that performance against 2700-2800 bucket was higher than performance against 2600-2700. Indeed, 2594.5 deviates from 2700.3 by ~100.

GPT thinks this is noise anyway and +-50 fluctuations are within standard deviation. I tried to confirm this by assuming that single game result is a coin toss (Bernoulli random variable) with fixed probability of winning, but for that case deviation of 50 elo is actually on the significant side if we have sample of ~50 games.

However, I think that we cannot make this assumption, probably because the probability of winning every single game is very different in every case. This is supported by the variances which are similarly high for other players with similar FIDE blitz rating.

### More examples

#### Etienne Bacrot `baki83`

```
band  games  score  avg_opp   perf
 500     63   34.0   2560.1 2587.8
 600     48   12.5   2635.9 2454.5
 700     59   18.0   2729.4 2586.4
800+     17    4.0   2838.2 2633.5
```

Similarly, one can claim that the 100 elo perf difference between buckets "600" and "700" is unexpected.

#### Sergei Zhigalko `Zhigalko_Sergei`

```
band  games  score  avg_opp   perf
 500    160   82.5   2547.9 2558.8
 600     89   31.5   2642.2 2537.7
 700    148   44.0   2739.5 2590.1
800+     40    6.5   2844.0 2559.2
```

This is example of stable performance, for completeness. However, the sample is **much higher**, which explains why every perf is closer to mean.

#### José Carlos Ibarra Jerez (`jcibarra`)

```
band  games  score  avg_opp   perf
 500    105   57.5   2549.3 2582.5
 600     51   26.5   2636.0 2649.6
 700     66   14.0   2734.4 2506.4
800+     23    2.0   2832.7 2424.3
```

The opposite case: 140 elo perf difference between buckets "600" and "700". One could say that it means that the player plays much stronger against 2600 players.

#### Vladimir Kramnik (`vladimirkramnik`)

```
band  games  score  avg_opp   perf
 500     49   29.5   2546.1 2618.1
 600     21    9.5   2644.3 2611.1
 700     33   11.0   2737.3 2616.9
800+     11    2.5   2833.8 2621.2
```

Surprisingly, here the performance is **extremely stable**. I didn't see such low variance for other samples! I'd speculate it really depends on player' style.

All these samples were taken by just taking random players around ~2595 rating for which there was some reasonable amount of Titled Tuesday games.

### Conclusion

The deviations of 100 Elo on different buckets are common.

## Main Script: `kramnik_anomaly_method.py`

### Overview
This script analyzes a chess player's performance against opponents grouped by rating bands (500, 600, 700, 800+) to identify potential rating anomalies or performance patterns.

### Features
- Fetches games from Chess.com API for any player
- Groups opponents by rating bands (500: 2500-2599, 600: 2600-2699, 700: 2700-2799, 800+: 2800+)
- Calculates performance ratings against each band
- Supports FIDE rating integration for more accurate band assignment
- Filters for tournament games (Titled Tuesday recommended)
- Generates detailed opponent breakdowns with FIDE ratings

### Usage

#### Basic Analysis
```bash
python3 kramnik_anomaly_method.py --player shimastream --since 2023-08-01 --until 2025-09-01 --titled-tuesday --use-fide
```

#### Parameters
- `--player`: Chess.com username (required)
- `--since`: Start date in YYYY-MM-DD format (required)
- `--until`: End date in YYYY-MM-DD format (required)
- `--titled-tuesday`: Restrict to Titled Tuesday tournaments only (recommended)
- `--use-fide`: Use FIDE ratings for band assignment instead of Chess.com ratings
- `--min-opp`: Minimum opponent rating to include (default: 2500)
- `--verbose`: Enable detailed logging

### Output
The script generates:
- **Performance vs bands table**: Shows games, score, average opponent rating, and performance rating for each band
- **Opponent breakdown CSV**: Detailed statistics for each opponent with FIDE ratings
- **Sample games CSV**: All analyzed games with metadata
- **Band summary CSV**: Aggregated performance by rating band


### Requirements
- Python 3.7+
- pandas
- requests
- python-dateutil
- tqdm

### Files
- `fide_blitz_ratings_2500+.json`: Pre-processed FIDE ratings data (required for `--use-fide`)
- Generated CSV files are automatically saved with timestamps
- All generated files are ignored by git (see `.gitignore`)

### Notes
- The script includes robust name matching between Chess.com usernames and FIDE player names
- FIDE rating integration provides more accurate band assignments for elite players
- Tournament-only analysis (Titled Tuesday) is recommended for cleaner data
- The analysis focuses on blitz games by default but supports other time controls
- Vibe coded, use at your own risk
