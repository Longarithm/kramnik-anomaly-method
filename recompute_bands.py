#!/usr/bin/env python3

import pandas as pd
import math

def perf_rating(score: float, n: int, avg_opp: float) -> float:
    """Compute performance rating given score out of n vs avg_opp Elo."""
    if n == 0:
        return float("nan")
    if score <= 0:
        return avg_opp - 800.0
    if score >= n:
        return avg_opp + 800.0
    return avg_opp + 400.0 * math.log10(score / (n - score))

def assign_band_from_rating(r: float) -> str:
    """Assign band based on FIDE rating with corrected 800+ threshold."""
    if r >= 2800:  # Corrected threshold for 800+ band
        return "800+"
    elif r >= 2700:
        return "700"
    elif r >= 2600:
        return "600"
    elif r >= 2500:
        return "500"
    else:
        return "below_2500"

def main():
    # Read the opponent breakdown CSV
    df = pd.read_csv('shimastream_opponent_breakdown_20250907-004743.csv')
    
    print("Original data summary:")
    print(f"Total opponents: {len(df)}")
    print(f"Total games: {df['games'].sum()}")
    print(f"Total score: {df['score'].sum():.1f}")
    print(f"FIDE rating range: {df['fide_rating'].min():.0f} - {df['fide_rating'].max():.0f}")
    print()
    
    # Assign bands using corrected thresholds
    df['band'] = df['fide_rating'].apply(assign_band_from_rating)
    
    # Filter out below_2500 band for analysis
    df_filtered = df[df['band'] != 'below_2500'].copy()
    
    print("Band assignment with corrected 800+ threshold (>=2800):")
    band_counts = df['band'].value_counts()
    for band in ['500', '600', '700', '800+']:
        if band in band_counts:
            print(f"  {band}: {band_counts[band]} opponents")
    if 'below_2500' in band_counts:
        print(f"  below_2500: {band_counts['below_2500']} opponents (excluded from analysis)")
    print()
    
    # Calculate performance by band
    band_performance = []
    order = {"500": 0, "600": 1, "700": 2, "800+": 3}
    
    for band in ['500', '600', '700', '800+']:
        band_data = df_filtered[df_filtered['band'] == band]
        if len(band_data) > 0:
            n = band_data['games'].sum()
            score = band_data['score'].sum()
            avg_opp = (band_data['avg_opp'] * band_data['games']).sum() / n
            perf = perf_rating(score, n, avg_opp)
            
            band_performance.append({
                'band': band,
                'games': n,
                'score': score,
                'avg_opp': round(avg_opp, 1),
                'perf': round(perf, 1)
            })
    
    # Sort by band order
    band_performance.sort(key=lambda x: order.get(x['band'], 99))
    
    print("Performance vs bands (corrected 800+ threshold >=2800):")
    print("band  games  score  avg_opp   perf")
    for bp in band_performance:
        print(f"{bp['band']:>4}   {bp['games']:>4}   {bp['score']:>4.1f}   {bp['avg_opp']:>6.1f}  {bp['perf']:>6.1f}")
    
    # Calculate overall performance
    total_games = df_filtered['games'].sum()
    total_score = df_filtered['score'].sum()
    weighted_opp_rating = (df_filtered['avg_opp'] * df_filtered['games']).sum() / total_games
    overall_perf = perf_rating(total_score, total_games, weighted_opp_rating)
    
    print(f"\nOverall Performance Analysis:")
    print(f"Total games: {total_games}")
    print(f"Total score: {total_score:.1f}")
    print(f"Score percentage: {(total_score/total_games*100):.1f}%")
    print(f"Weighted average opponent rating: {weighted_opp_rating:.1f}")
    print(f"Overall performance rating: {overall_perf:.1f}")
    
    # Show which players are in 800+ band with corrected threshold
    print(f"\nPlayers in 800+ band (FIDE >=2800):")
    top_players = df_filtered[df_filtered['band'] == '800+'].sort_values('fide_rating', ascending=False)
    for _, player in top_players.iterrows():
        print(f"  {player['real_name']} ({player['opp']}): {player['fide_rating']:.0f} FIDE, {player['games']} games, {player['score']:.1f} score")

if __name__ == "__main__":
    main()
