#!/usr/bin/env python3

import sys
import os

# Add the current directory to path so we can import the functions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kramnik_anomaly_method import download_fide_ratings, normalize_fide_name, find_fide_rating_for_player

def test_fide_parsing():
    print("Testing FIDE data parsing...")
    
    # Test downloading FIDE ratings
    fide_mapping = download_fide_ratings(min_rating=2600, verbose=True)
    
    print(f"\nLoaded {len(fide_mapping)} players with FIDE ratings >= 2600")
    
    # Show first 10 players
    print("\nFirst 10 players found:")
    for i, (name, rating) in enumerate(list(fide_mapping.items())[:10]):
        print(f"  {name}: {rating}")
    
    # Test name normalization
    print("\nTesting name normalization:")
    test_names = [
        "Carlsen, Magnus",
        "Nakamura, Hikaru", 
        "Kramnik, Vladimir",
        "Shimanov, Aleksandr"
    ]
    
    for name in test_names:
        normalized = normalize_fide_name(name)
        print(f"  '{name}' -> '{normalized}'")
    
    # Test finding specific players
    print("\nTesting player lookup:")
    test_players = [
        "magnuscarlsen",
        "hikaru", 
        "vladimirkramnik",
        "shimastream"
    ]
    
    for player in test_players:
        rating = find_fide_rating_for_player(player, fide_mapping, verbose=True)
        print(f"  {player}: {rating}")

if __name__ == "__main__":
    test_fide_parsing()
