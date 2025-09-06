# Kramnik Anomaly Method

A statistical analysis tool for analyzing chess player performance against different rating bands, inspired by Vladimir Kramnik's approach to detecting rating anomalies.

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

### Example Output
```
Performance vs bands:
band  games  score  avg_opp   perf
 500     94   56.0   2542.4 2609.8
 600     41   18.0   2637.1 2594.5
 700     54   24.5   2732.5 2700.3
800+     17    1.5   2844.3 2438.6
Adding FIDE ratings to opponent breakdown...
Saved FIDE mapping to shimastream_fide_mapping_20250907-013524.json
Saved username-to-name mapping to shimastream_username_mapping_20250907-013524.json
Found FIDE ratings for 100 out of 100 opponents
FIDE rating range: 2501.0 - 2881.0
Average FIDE rating: 2606.0

Top opponents by games (first 20):
                 opp  games  score  avg_opp  score_pct  fide_rating          real_name
            jefferyx      8    4.5   2703.0       56.2       2703.0      Jeffery Xiong
           mishanick      8    3.5   2705.0       43.8       2705.0     Aleksei Sarana
              hikaru      8    0.5   2838.0        6.2       2838.0    Hikaru Nakamura
          scarabee43      7    4.5   2510.0       64.3       2510.0      Marco Materia
   oleksandr_bortnyk      6    4.5   2793.0       75.0       2793.0  Oleksandr Bortnyk
  polish_fighter3000      6    1.0   2752.0       16.7       2752.0 Jan-Krzysztof Duda
       magnuscarlsen      5    0.0   2881.0        0.0       2881.0     Magnus Carlsen
    vladislavkovalev      4    4.0   2553.0      100.0       2553.0  Vladislav Kovalev
              baki83      4    2.0   2590.0       50.0       2590.0     Etienne Bacrot
fairchess_on_youtube      4    2.0   2714.0       50.0       2714.0   Dmitry Andreikin
           vi_pranav      4    1.5   2606.0       37.5       2606.0           Pranav V
              denlaz      4    1.0   2609.0       25.0       2609.0      Denis Lazavik
            parhamov      4    0.5   2703.0       12.5       2703.0 Parham Maghsoodloo
        gmakobianstl      3    3.0   2512.0      100.0       2512.0   Varuzhan Akobian
                msb2      3    3.0   2635.0      100.0       2635.0  Matthias Bluebaum
          durarbayli      3    2.0   2570.0       66.7       2570.0   Vasif Durarbayli
            grischuk      3    2.0   2676.0       66.7       2676.0 Alexander Grischuk
    danielnaroditsky      3    1.5   2729.0       50.0       2729.0  Daniel Naroditsky
      ghandeevam2003      3    1.5   2750.0       50.0       2750.0     Arjun Erigaisi
          igor_lysyj      3    1.0   2517.0       33.3       2517.0         Igor Lysyj

Saved CSVs in current directory:
  shimastream_blitz_sample_20250907-013524.csv
  shimastream_band_summary_20250907-013524.csv
  shimastream_opponent_breakdown_20250907-013524.csv
```

**IMPORTANT:** GPT thinks it's noise anyway. Didn't check though

Using your overall strength as baseline and each band’s avg_opp, the Elo model predicts the following scores; compare to what you observed:

Expected vs observed (Elo logistic), z-scores

* 500 (N=94, avg_opp 2542.4): expected 0.619, observed 0.596 → z = −0.47σ
95% CI for perf ≈ 2609.8 ± 72 Elo
* 600 (N=41, avg_opp 2637.1): expected 0.485, observed 0.439 → z = −0.60σ
95% CI ≈ 2594.5 ± 106 Elo
* 700 (N=54, avg_opp 2732.5): expected 0.353, observed 0.454 → z = +1.55σ
95% CI ≈ 2700.3 ± 97 Elo
* 800+ (N=17, avg_opp 2844.3): expected 0.223, observed 0.088 → z = −1.33σ
95% CI ≈ 2438.6 ± 199 Elo

Conclusion: none of the bands reaches |z| ≥ 2, so the 700 bump and 800+ dip are not statistically significant with these sample sizes.

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
