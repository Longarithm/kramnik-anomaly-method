
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
import time
import re
import subprocess
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta
from tqdm import tqdm

BASE = "https://api.chess.com/pub"
FIDE_BASE = "https://ratings.fide.com"

# Global cache for API responses to avoid redundant network requests
_api_cache: Dict[str, dict] = {}
_api_cache_file = "chess_api_cache.json"

def load_api_cache():
    """Load API cache from file."""
    global _api_cache
    if os.path.exists(_api_cache_file):
        try:
            with open(_api_cache_file, 'r') as f:
                _api_cache = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load API cache from {_api_cache_file}: {e}")
            _api_cache = {}

def save_api_cache():
    """Save API cache to file."""
    try:
        with open(_api_cache_file, 'w') as f:
            json.dump(_api_cache, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save API cache to {_api_cache_file}: {e}")

def clear_api_cache():
    """Clear the API response cache."""
    global _api_cache
    _api_cache.clear()
    if os.path.exists(_api_cache_file):
        try:
            os.remove(_api_cache_file)
        except Exception as e:
            print(f"Warning: Could not remove cache file {_api_cache_file}: {e}")

def get_cache_stats():
    """Get statistics about the API cache."""
    basic_player_profiles = [url for url in _api_cache.keys() 
                           if url.startswith(f"{BASE}/player/") 
                           and not url.endswith("/games/archives") 
                           and "/games/" not in url]
    return {
        'cached_urls': len(_api_cache),
        'basic_player_profiles': len(basic_player_profiles),
        'game_archives': len([url for url in _api_cache.keys() if url.endswith("/games/archives")]),
        'monthly_games': len([url for url in _api_cache.keys() if "/games/" in url and not url.endswith("/games/archives")]),
        'other_urls': len(_api_cache) - len(basic_player_profiles) - len([url for url in _api_cache.keys() if "/games/" in url]),
        'urls': list(_api_cache.keys()),
        'cache_file': _api_cache_file,
        'cache_file_exists': os.path.exists(_api_cache_file)
    }

def cleanup_api_cache():
    """Remove non-basic-player-profile entries from the cache."""
    global _api_cache
    basic_player_profiles = {url: data for url, data in _api_cache.items() 
                           if url.startswith(f"{BASE}/player/") 
                           and not url.endswith("/games/archives") 
                           and "/games/" not in url}
    removed_count = len(_api_cache) - len(basic_player_profiles)
    _api_cache = basic_player_profiles
    if removed_count > 0:
        save_api_cache()
        print(f"Removed {removed_count} non-basic-player-profile entries from cache")
    return removed_count

def parse_date(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%Y-%m-%d").date()

def month_range(start: dt.date, end: dt.date) -> List[Tuple[int, int]]:
    """Inclusive month range (YYYY, MM) covering [start, end]."""
    months = []
    cur = start.replace(day=1)
    end_first = end.replace(day=1)
    while cur <= end_first:
        months.append((cur.year, cur.month))
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
    return months

def fetch_json(url: str, retries: int = 3, sleep: float = 0.8, verbose: bool = False, use_cache: bool = True) -> Optional[dict]:
    # Check cache first if enabled and URL is a basic Chess.com player profile (not games/archives)
    is_basic_player_profile = url.startswith(f"{BASE}/player/") and not url.endswith("/games/archives") and "/games/" not in url
    if use_cache and is_basic_player_profile and url in _api_cache:
        if verbose:
            print(f"  Using cached response for: {url}")
        return _api_cache[url]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    for i in range(retries):
        if verbose:
            print(f"  Fetching: {url} (attempt {i+1}/{retries})")
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if verbose:
                print(f"  Status: {r.status_code}")
            if r.status_code == 200:
                try:
                    data = r.json()
                    # Cache successful responses if caching is enabled and URL is a basic Chess.com player profile
                    if use_cache and is_basic_player_profile:
                        _api_cache[url] = data
                        save_api_cache()  # Save to persistent file
                        if verbose:
                            print(f"  Cached response for: {url}")
                    return data
                except Exception as e:
                    if verbose:
                        print(f"  JSON parse error: {e}")
                    return None
            elif r.status_code == 403:
                if verbose:
                    print("  Got 403 - API might be blocking requests")
                time.sleep(sleep * (i + 1) * 2)  # Longer wait for 403
            else:
                if verbose:
                    print(f"  HTTP error: {r.status_code}")
        except Exception as e:
            if verbose:
                print(f"  Request error: {e}")
        time.sleep(sleep * (i + 1))
    return None

def list_archives(username: str, verbose: bool = False) -> List[str]:
    url = f"{BASE}/player/{username}/games/archives"
    if verbose:
        print(f"Fetching archives for {username}...")
    j = fetch_json(url, verbose=verbose)
    if not j or "archives" not in j:
        if verbose:
            print("  No archives found in API response")
        return []
    archives = j["archives"]
    if verbose:
        print(f"  Found {len(archives)} archive months")
    return archives

def monthly_games(username: str, year: int, month: int, verbose: bool = False) -> List[dict]:
    url = f"{BASE}/player/{username}/games/{year}/{month:02d}"
    if verbose:
        print(f"  Fetching games for {year}-{month:02d}...")
    j = fetch_json(url, verbose=verbose)
    if not j or "games" not in j:
        if verbose:
            print(f"    No games found for {year}-{month:02d}")
        return []
    games = j["games"]
    if verbose:
        print(f"    Found {len(games)} games for {year}-{month:02d}")
    return games

def normalize_username(u: str) -> str:
    return u.lower()

@dataclass
class GameRec:
    ts: dt.datetime
    me: str
    opp: str
    result: float  # 1, 0.5, 0
    opp_rating_game: Optional[int]
    opp_color: str
    tournament: Optional[str]
    url: Optional[str]

def parse_game_for_player(game: dict, player: str, include_unrated: bool = False, time_classes: List[str] = None) -> Optional[GameRec]:
    """Return a GameRec if 'player' is white or black and game matches criteria."""
    if time_classes is None:
        time_classes = ["blitz"]
    
    # Check if game is rated (unless we include unrated)
    if not include_unrated and game.get("rated") is not True:
        return None
    
    # Check time class
    if game.get("time_class") not in time_classes:
        return None
    white = game.get("white", {})
    black = game.get("black", {})
    uw = normalize_username(white.get("username", ""))
    ub = normalize_username(black.get("username", ""))
    p = normalize_username(player)
    if uw != p and ub != p:
        return None

    ts = dt.datetime.utcfromtimestamp(game.get("end_time", game.get("start_time", 0)))
    tournament = game.get("tournament")
    url = game.get("url")

    result_map = {
        "win": 1.0,
        "checkmated": 0.0,
        "agreed": 0.5,
        "repetition": 0.5,
        "stalemate": 0.5,
        "timevsinsufficient": 0.5,
        "insufficient": 0.5,
        "lose": 0.0,
        "timeout": 0.0,
        "resigned": 0.0,
        "abandoned": 0.0,
        "50move": 0.5,
    }

    if uw == p:
        my_res = white.get("result")
        opp_rating = black.get("rating")
        opp_name = ub
        opp_color = "black"
    else:
        my_res = black.get("result")
        opp_rating = white.get("rating")
        opp_name = uw
        opp_color = "white"

    r = result_map.get(my_res)
    if r is None:
        return None

    return GameRec(
        ts=ts,
        me=p,
        opp=opp_name,
        result=r,
        opp_rating_game=int(opp_rating) if opp_rating else None,
        opp_color=opp_color,
        tournament=tournament,
        url=url,
    )

def fetch_player_games_manual(player: str, since: dt.date, until: dt.date, verbose: bool = False, include_unrated: bool = False, time_classes: List[str] = None) -> List[GameRec]:
    """Manually fetch games month by month when archives API fails."""
    records: List[GameRec] = []
    months = month_range(since, until)
    
    if verbose:
        print(f"Manually fetching games for {len(months)} months...")
    
    for year, month in months:
        games = monthly_games(player, year, month, verbose=verbose)
        for g in games:
            rec = parse_game_for_player(g, player, include_unrated, time_classes)
            if rec is None:
                continue
            d = rec.ts.date()
            if since <= d <= until:
                records.append(rec)
    return records

def fetch_player_games(player: str, since: dt.date, until: dt.date, verbose: bool = False, include_unrated: bool = False, time_classes: List[str] = None) -> List[GameRec]:
    """Fetch games for 'player' in [since, until]."""
    records: List[GameRec] = []
    
    # First try the archives API
    archives = list_archives(player, verbose=verbose)
    if not archives:
        if verbose:
            print("Archives API failed, trying manual month-by-month fetch...")
        return fetch_player_games_manual(player, since, until, verbose=verbose, include_unrated=include_unrated, time_classes=time_classes)

    want = set((y, m) for (y, m) in month_range(since, until))
    found_any = False
    
    for archive_url in archives:
        try:
            parts = archive_url.rstrip("/").split("/")[-2:]
            y, m = int(parts[0]), int(parts[1])
        except Exception:
            continue
        if (y, m) not in want:
            continue
        games = monthly_games(player, y, m, verbose=verbose)
        if games:  # Found games in this month
            found_any = True
        for g in games:
            rec = parse_game_for_player(g, player, include_unrated, time_classes)
            if rec is None:
                continue
            d = rec.ts.date()
            if since <= d <= until:
                records.append(rec)
    
    # If archives API returned empty results, try manual fetch
    if not found_any and verbose:
        print("Archives API returned no games, trying manual month-by-month fetch...")
        return fetch_player_games_manual(player, since, until, verbose=verbose, include_unrated=include_unrated, time_classes=time_classes)
    
    return records

def filter_titled_tuesday_only(games: List[GameRec]) -> List[GameRec]:
    out = []
    for g in games:
        t = (g.tournament or "").lower()
        if "titled" in t and "tuesday" in t:
            out.append(g)
    return out

def perf_rating(score: float, n: int, avg_opp: float) -> float:
    """Compute performance rating given score out of n vs avg_opp Elo."""
    if n == 0:
        return float("nan")
    if score <= 0:
        return avg_opp - 800.0
    if score >= n:
        return avg_opp + 800.0
    return avg_opp + 400.0 * math.log10(score / (n - score))

def download_fide_players_list(verbose: bool = False) -> bool:
    """Download FIDE players list if foa.txt doesn't exist."""
    fide_file = "players_list_foa.txt"
    
    if os.path.exists(fide_file):
        if verbose:
            print(f"FIDE players list already exists: {fide_file}")
        return True
    
    print("FIDE players list not found. Downloading from FIDE website...")
    
    try:
        # Download the zip file
        download_cmd = [
            "curl", "-s", 
            "http://ratings.fide.com/download/players_list.zip", 
            "-o", "fide_players.zip"
        ]
        
        if verbose:
            print(f"Running: {' '.join(download_cmd)}")
        
        result = subprocess.run(download_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error downloading FIDE players list: {result.stderr}")
            return False
        
        if not os.path.exists("fide_players.zip"):
            print("Download failed: fide_players.zip not created")
            return False
        
        print("Download successful. Extracting...")
        
        # Extract the zip file
        extract_cmd = ["unzip", "-o", "fide_players.zip"]
        if verbose:
            print(f"Running: {' '.join(extract_cmd)}")
        
        result = subprocess.run(extract_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error extracting zip file: {result.stderr}")
            return False
        
        # Check if foa.txt was extracted
        if not os.path.exists(fide_file):
            print(f"Error: {fide_file} not found after extraction")
            print("Available files:")
            for f in os.listdir("."):
                if f.endswith(".txt"):
                    print(f"  {f}")
            return False
        
        # Clean up the zip file
        try:
            os.remove("fide_players.zip")
            if verbose:
                print("Cleaned up fide_players.zip")
        except Exception as e:
            print(f"Warning: Could not remove fide_players.zip: {e}")
        
        print(f"Successfully downloaded and extracted {fide_file}")
        return True
        
    except Exception as e:
        print(f"Error downloading FIDE players list: {e}")
        return False

def assign_band_from_rating(r: Optional[float], use_fide: bool = False) -> Optional[str]:
    if r is None:
        return None
    
    if use_fide:
        # FIDE rating buckets based on actual FIDE ratings
        if r >= 2800:  # Top FIDE players
            return "800+"
        if r >= 2700:  # Strong FIDE players  
            return "700"
        if r >= 2600:  # Good FIDE players
            return "600"
        if r >= 2500:  # Decent FIDE players
            return "500"
    else:
        # Chess.com blitz ratings are different from FIDE
        # Adjust thresholds for Chess.com blitz ratings
        if r >= 2800:  # Top Chess.com blitz players
            return "800+"
        if r >= 2700:  # Strong Chess.com blitz players  
            return "700"
        if r >= 2600:  # Good Chess.com blitz players
            return "600"
    return None

def download_fide_ratings(min_rating: int = 2500, verbose: bool = False) -> Dict[str, int]:
    """Load FIDE ratings from the pre-processed JSON file, or create it from raw data if needed."""
    fide_cache_file = f"fide_blitz_ratings_{min_rating}+.json"
    
    # Check if we have the pre-processed JSON file
    if os.path.exists(fide_cache_file):
        if verbose:
            print(f"Loading FIDE ratings from {fide_cache_file}")
        try:
            with open(fide_cache_file, 'r') as f:
                fide_data = json.load(f)
                if verbose:
                    print(f"Loaded {len(fide_data)} FIDE ratings from {fide_cache_file}")
                return fide_data
        except Exception as e:
            if verbose:
                print(f"Error loading FIDE ratings from {fide_cache_file}: {e}")
            return {}
    
    # Otherwise, create the file from raw data
    if verbose:
        print(f"FIDE ratings file {fide_cache_file} not found. Attempting to create it...")
    
    # Try to create the JSON file from raw FIDE data
    fide_file = "players_list_foa.txt"
    
    # Check if raw FIDE data exists, download if needed
    if not os.path.exists(fide_file):
        if verbose:
            print("Raw FIDE data not found. Attempting to download...")
        if not download_fide_players_list(verbose=verbose):
            if verbose:
                print("Failed to download FIDE players list.")
            return {}
    
    # Try to parse the raw data and create the JSON file
    try:
        with open(fide_file, 'r', encoding='utf-8', errors='ignore') as f:
            data = f.read()
        
        # Parse the FIDE data
        fide_data = parse_fide_ratings_data(data, min_rating, verbose=verbose)
        
        if fide_data:
            # Sort the data by rating in descending order
            sorted_fide_data = dict(sorted(fide_data.items(), key=lambda x: x[1], reverse=True))
            
            # Save to JSON file for future use
            with open(fide_cache_file, 'w') as f:
                json.dump(sorted_fide_data, f, indent=2)
            if verbose:
                print(f"Created and saved {len(sorted_fide_data)} FIDE ratings to {fide_cache_file} (sorted by rating)")
            return sorted_fide_data
        else:
            if verbose:
                print("No FIDE data could be parsed from raw file")
            return {}
            
    except Exception as e:
        if verbose:
            print(f"Error processing FIDE data: {e}")
        return {}

def parse_fide_ratings_data(data: str, min_rating: int, verbose: bool = False) -> Dict[str, int]:
    """Parse FIDE ratings data correctly using fixed-width column positions."""
    fide_mapping = {}
    
    if verbose:
        print(f"Parsing FIDE ratings data for players with rating >= {min_rating}...")
    
    lines = data.strip().split('\n')
    processed = 0
    
    # Find the header line to determine column positions
    header_line = None
    for i, line in enumerate(lines):
        if "ID Number" in line and "Name" in line:
            header_line = line
            break
    
    if not header_line:
        if verbose:
            print("Could not find header line")
        return {}
    
    # Find column positions
    name_start = header_line.find("Name")
    fed_start = header_line.find("Fed")
    sex_start = header_line.find("Sex")
    tit_start = header_line.find("Tit")
    foa_start = header_line.find("FOA")
    srtng_start = header_line.find("SRtng")
    rrtng_start = header_line.find("RRtng")
    brtng_start = header_line.find("BRtng")
    
    if verbose:
        print(f"Column positions: Name={name_start}, Fed={fed_start}, Sex={sex_start}, Tit={tit_start}")
        print(f"Rating positions: FOA={foa_start}, SRtng={srtng_start}, RRtng={rrtng_start}, BRtng={brtng_start}")
    
    # Process each line starting after the header
    for i, line in enumerate(lines):
        if i < 2:  # Skip header lines
            continue
            
        if not line.strip():
            continue
            
        # Check if line starts with a FIDE ID (numeric)
        if not line[:10].strip().isdigit():
            continue
            
        try:
            # Extract FIDE ID (first 10 characters)
            fide_id = line[:10].strip()
            
            # Extract name (between Name and Fed columns)
            if name_start < len(line) and fed_start < len(line):
                name = line[name_start:fed_start].strip()
            else:
                continue
                
            if name == '-' or name == '-, -' or not name:
                continue
                
            # Extract blitz rating (BRtng column)
            if brtng_start < len(line):
                # BRtng is 5 characters wide
                brtng_str = line[brtng_start:brtng_start+5].strip()
                if brtng_str.isdigit():
                    blitz_rating = int(brtng_str)
                    if blitz_rating >= min_rating:
                        # Normalize name for matching
                        normalized_name = normalize_fide_name(name)
                        if normalized_name:
                            fide_mapping[normalized_name] = blitz_rating
                            processed += 1
                            if processed <= 10:  # Show first 10 matches
                                print(f"  Found: {name} -> {blitz_rating} (blitz)")
                
        except Exception as e:
            if processed < 10:
                print(f"Error parsing line {i}: {e}")
    
    if verbose:
        print(f"Parsed {processed} players with rating >= {min_rating}")
    
    return fide_mapping

def normalize_fide_name(name: str) -> str:
    """Normalize FIDE name format (Last, First) to a searchable format."""
    if not name or name == '-' or name == '-, -':
        return ""
    
    # FIDE format is typically "Last, First" or "Last, First Middle"
    parts = name.split(',')
    if len(parts) >= 2:
        last_name = parts[0].strip()
        first_parts = parts[1].strip().split()
        first_name = first_parts[0] if first_parts else ""
        
        # Create variations for matching
        # Format: "firstname_lastname" (lowercase)
        if first_name and last_name:
            return f"{first_name.lower()}_{last_name.lower()}"
    
    # Fallback: just use the name as-is, normalized
    return name.lower().replace(' ', '_').replace(',', '')


def normalize_name_for_matching(name: str) -> str:
    """Normalize a name for fuzzy matching."""
    if not name:
        return ""
    
    # Remove common prefixes/suffixes and normalize
    name = name.lower().strip()
    
    # Remove titles (both with and without spaces) - use word boundaries to avoid partial matches
    titles = ["gm", "im", "fm", "cm", "wgm", "wim", "wfm", "wcm", "grandmaster", "international master", "fide master", "candidate master"]
    for title in titles:
        # Use word boundaries to ensure we only match complete words
        name = re.sub(r'\b' + re.escape(title) + r'\b', '', name).strip()
    
    # Remove country codes in parentheses
    name = re.sub(r'\([a-z]{2,3}\)', '', name).strip()
    
    # Remove extra spaces and normalize
    name = " ".join(name.split())
    
    return name

def find_fide_rating_for_player(username: str, fide_mapping: Dict[str, int], verbose: bool = False) -> Optional[int]:
    """Find FIDE rating for a player using fuzzy matching."""
    try:
        # Get player profile from Chess.com
        profile_url = f"{BASE}/player/{username}"
        profile_data = fetch_json(profile_url, verbose=verbose)
        if not profile_data:
            return None
            
        player_name = profile_data.get("name", "")
        country = profile_data.get("country", "").split("/")[-1] if profile_data.get("country") else ""
        title = profile_data.get("title", "")
        
        if verbose:
            print(f"  Looking up FIDE rating for {username}: {player_name} ({country}) {title}")
        
        # Try exact username match first
        if username.lower() in fide_mapping:
            if verbose:
                print(f"    Found exact username match: {username.lower()} -> {fide_mapping[username.lower()]}")
            return fide_mapping[username.lower()]
        
        # Convert Chess.com name format to FIDE format for matching
        # Chess.com: "First Last" -> FIDE: "first_last"
        if player_name:
            # Remove titles and normalize
            clean_name = normalize_name_for_matching(player_name)
            name_parts = clean_name.split()
            if len(name_parts) >= 2:
                # Try "first_last" format
                fide_format = f"{name_parts[0]}_{name_parts[-1]}"
                if fide_format in fide_mapping:
                    if verbose:
                        print(f"    Found FIDE format match: {fide_format} -> {fide_mapping[fide_format]}")
                    return fide_mapping[fide_format]
                
                # Try "last_first" format (reverse order)
                fide_format_reverse = f"{name_parts[-1]}_{name_parts[0]}"
                if fide_format_reverse in fide_mapping:
                    if verbose:
                        print(f"    Found reverse FIDE format match: {fide_format_reverse} -> {fide_mapping[fide_format_reverse]}")
                    return fide_mapping[fide_format_reverse]
        
        # Try more strict partial matching - only if we have very high confidence
        if player_name:
            clean_name = normalize_name_for_matching(player_name)
            name_parts = clean_name.split()
            
            # Only try partial matching if we have exactly 2 name parts (first and last)
            if len(name_parts) == 2:
                first_name, last_name = name_parts
                
                for fide_name, rating in fide_mapping.items():
                    fide_parts = fide_name.split('_')
                    
                    # Only match if both first and last names are present and match
                    if len(fide_parts) >= 2:
                        fide_first = fide_parts[0]
                        fide_last = fide_parts[-1]
                        
                        # Check if both first and last names match (exact or very close)
                        first_match = (first_name == fide_first or 
                                     (len(first_name) > 4 and len(fide_first) > 4 and 
                                      (first_name in fide_first or fide_first in first_name)))
                        last_match = (last_name == fide_last or 
                                    (len(last_name) > 4 and len(fide_last) > 4 and 
                                     (last_name in fide_last or fide_last in last_name)))
                        
                        if first_match and last_match:
                            if verbose:
                                print(f"    Found strict partial match: {fide_name} -> {rating}")
                            return rating
        
        if verbose:
            print(f"    No FIDE mapping found for {username}")
        return None
        
    except Exception as e:
        if verbose:
            print(f"    Error looking up FIDE rating for {username}: {e}")
        return None

def get_fide_rating_for_player(username: str, fide_mapping: Dict[str, int], verbose: bool = False) -> Optional[int]:
    """Get FIDE rating for a player using the provided FIDE mapping."""
    return find_fide_rating_for_player(username, fide_mapping, verbose)

def get_fide_rating_for_player_with_name(username: str, fide_mapping: Dict[str, int], verbose: bool = False) -> Tuple[Optional[int], Optional[str]]:
    """Get FIDE rating and real name for a player using the provided FIDE mapping."""
    try:
        # Get player profile from Chess.com
        profile_url = f"{BASE}/player/{username}"
        profile_data = fetch_json(profile_url, verbose=verbose)
        if not profile_data:
            return None, None
            
        player_name = profile_data.get("name", "")
        country = profile_data.get("country", "").split("/")[-1] if profile_data.get("country") else ""
        title = profile_data.get("title", "")
        
        if verbose:
            print(f"  Looking up FIDE rating for {username}: {player_name} ({country}) {title}")
        
        # Try exact username match first
        if username.lower() in fide_mapping:
            if verbose:
                print(f"    Found exact username match: {username.lower()} -> {fide_mapping[username.lower()]}")
            return fide_mapping[username.lower()], player_name
        
        # Convert Chess.com name format to FIDE format for matching
        # Chess.com: "First Last" -> FIDE: "first_last"
        if player_name:
            # Remove titles and normalize
            clean_name = normalize_name_for_matching(player_name)
            name_parts = clean_name.split()
            if len(name_parts) >= 2:
                # Try "first_last" format
                fide_format = f"{name_parts[0]}_{name_parts[-1]}"
                if fide_format in fide_mapping:
                    if verbose:
                        print(f"    Found FIDE format match: {fide_format} -> {fide_mapping[fide_format]}")
                    return fide_mapping[fide_format], player_name
                
                # Try "last_first" format (reverse order)
                fide_format_reverse = f"{name_parts[-1]}_{name_parts[0]}"
                if fide_format_reverse in fide_mapping:
                    if verbose:
                        print(f"    Found reverse FIDE format match: {fide_format_reverse} -> {fide_mapping[fide_format_reverse]}")
                    return fide_mapping[fide_format_reverse], player_name
        
        # Try more strict partial matching - only if we have very high confidence
        if player_name:
            clean_name = normalize_name_for_matching(player_name)
            name_parts = clean_name.split()
            
            # Only try partial matching if we have exactly 2 name parts (first and last)
            if len(name_parts) == 2:
                first_name, last_name = name_parts
                
                for fide_name, rating in fide_mapping.items():
                    fide_parts = fide_name.split('_')
                    
                    # Only match if both first and last names are present and match
                    if len(fide_parts) >= 2:
                        fide_first = fide_parts[0]
                        fide_last = fide_parts[-1]
                        
                        # Check if both first and last names match (exact or very close)
                        first_match = (first_name == fide_first or 
                                     (len(first_name) > 4 and len(fide_first) > 4 and 
                                      (first_name in fide_first or fide_first in first_name)))
                        last_match = (last_name == fide_last or 
                                    (len(last_name) > 4 and len(fide_last) > 4 and 
                                     (last_name in fide_last or fide_last in last_name)))
                        
                        if first_match and last_match:
                            if verbose:
                                print(f"    Found strict partial match: {fide_name} -> {rating}")
                            return rating, player_name
        
        # Try fuzzy matching for common name variations
        if player_name:
            clean_name = normalize_name_for_matching(player_name)
            name_parts = clean_name.split()
            
            if len(name_parts) >= 2:
                first_name, last_name = name_parts[0], name_parts[-1]
                
                # Common name variations
                first_variations = [first_name]
                last_variations = [last_name]
                
                # Add common spelling variations
                if first_name == "oleksandr":
                    first_variations.extend(["olexandr", "alexander", "aleksandr"])
                elif first_name == "aleksei":
                    first_variations.extend(["alexey", "alexei", "alexey"])
                elif first_name == "vladimir":
                    first_variations.extend(["vladimir"])  # Should match exactly
                
                for fide_name, rating in fide_mapping.items():
                    fide_parts = fide_name.split('_')
                    if len(fide_parts) >= 2:
                        fide_first = fide_parts[0]
                        fide_last = fide_parts[-1]
                        
                        # Check if any variation matches
                        for first_var in first_variations:
                            for last_var in last_variations:
                                if (first_var == fide_first and last_var == fide_last):
                                    if verbose:
                                        print(f"    Found variation match: {fide_name} -> {rating} (matched {first_var} {last_var})")
                                    return rating, player_name
        
        if verbose:
            print(f"    No FIDE mapping found for {username}")
        return None, player_name
        
    except Exception as e:
        if verbose:
            print(f"    Error looking up FIDE rating for {username}: {e}")
        return None, None

def compute_fide_ratings_for_opponents(opponents: Iterable[str], fide_mapping: Dict[str, int], verbose: bool = False) -> Tuple[Dict[str, Optional[float]], Dict[str, str]]:
    """Get FIDE ratings for opponents using the provided FIDE mapping.
    Returns both FIDE ratings and username to real name mapping."""
    opp_fide: Dict[str, Optional[float]] = {}
    username_to_name: Dict[str, str] = {}
    
    for opp in tqdm(list(set(opponents)), desc="FIDE ratings lookup"):
        fide_rating, real_name = get_fide_rating_for_player_with_name(opp, fide_mapping, verbose=verbose)
        opp_fide[opp] = fide_rating
        if real_name:
            username_to_name[opp] = real_name
    
    return opp_fide, username_to_name

def compute_two_year_avg_for_opponents(opponents: Iterable[str], window_start: dt.date, window_end: dt.date) -> Dict[str, Optional[float]]:
    """Approximate two‑year average blitz rating for each opponent from their own archives in [window_start, window_end]."""
    opp_avg: Dict[str, Optional[float]] = {}
    for opp in tqdm(list(set(opponents)), desc="Opponents 2y avg"):
        try:
            ars = list_archives(opp)
            ratings: List[int] = []
            if not ars:
                opp_avg[opp] = None
                continue
            want = set((y, m) for (y, m) in month_range(window_start, window_end))
            for aurl in ars:
                try:
                    parts = aurl.rstrip("/").split("/")[-2:]
                    y, m = int(parts[0]), int(parts[1])
                except Exception:
                    continue
                if (y, m) not in want:
                    continue
                gs = monthly_games(opp, y, m)
                for g in gs:
                    if g.get("rated") is not True or g.get("time_class") != "blitz":
                        continue
                    w = g.get("white", {})
                    b = g.get("black", {})
                    name_w = (w.get("username","") or "").lower()
                    name_b = (b.get("username","") or "").lower()
                    r = None
                    if name_w == opp:
                        r = w.get("rating")
                    elif name_b == opp:
                        r = b.get("rating")
                    if r:
                        ratings.append(int(r))
            opp_avg[opp] = (sum(ratings) / len(ratings)) if ratings else None
        except Exception:
            opp_avg[opp] = None
    return opp_avg

def summarize_by_band(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    order = {"500":0,"600":1,"700":2,"800+":3}
    for band, sub in df.groupby("band"):
        n = len(sub)
        score = sub["result"].sum()
        avg_opp = sub["opp_rating_band_avg"].mean()
        perf = perf_rating(score, n, avg_opp)
        out.append({"band": band, "games": n, "score": score, "avg_opp": round(avg_opp, 1), "perf": round(perf, 1)})
    out = sorted(out, key=lambda x: order.get(x["band"], 99))
    return pd.DataFrame(out)

def main(argv=None):
    ap = argparse.ArgumentParser(description="Reproduce Kramnik-style anomaly test vs elite rating bands")
    ap.add_argument("--player", required=True, help="Chess.com username (case-insensitive)")
    ap.add_argument("--since", required=True, help="Start date (YYYY-MM-DD)")
    ap.add_argument("--until", required=True, help="End date (YYYY-MM-DD)")
    ap.add_argument("--titled-tuesday", action="store_true", help="Restrict to Titled Tuesday tournaments only (recommended)")
    ap.add_argument("--two-year-avg", action="store_true", help="Use two-year average for opponent band assignment (approx)")
    ap.add_argument("--use-fide", action="store_true", help="Use FIDE ratings for band assignment instead of Chess.com ratings")
    ap.add_argument("--min-opp", type=int, default=2500, help="Minimum opponent rating to include (default 2500)")
    ap.add_argument("--include-unrated", action="store_true", help="Include unrated games (some tournaments are marked as unrated)")
    ap.add_argument("--time-classes", default="blitz", help="Comma-separated time classes to include (default: blitz)")
    ap.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = ap.parse_args(argv)

    player = (args.player or "").lower()
    since = parse_date(args.since)
    until = parse_date(args.until)
    time_classes = [tc.strip() for tc in args.time_classes.split(",")]

    print(f"Fetching games for {player} from {since} to {until} ...")
    if args.verbose:
        print(f"Time classes: {time_classes}")
        print(f"Include unrated: {args.include_unrated}")
    
    games = fetch_player_games(player, since, until, verbose=args.verbose, include_unrated=args.include_unrated, time_classes=time_classes)
    if args.titled_tuesday:
        games = filter_titled_tuesday_only(games)
    elif not args.titled_tuesday:
        print("Note: Consider using --titled-tuesday for tournament games only")

    if not games:
        print("No games fetched. Possible issues:")
        print("1. Player username might be incorrect")
        print("2. No games in the specified time range")
        print("3. Try --include-unrated flag (some tournaments are marked as unrated)")
        print("4. Try different time classes with --time-classes bullet,blitz,rapid")
        print("5. Check if the player has public games on Chess.com")
        return 0

    rows = []
    for g in games:
        rows.append({
            "ts": g.ts,
            "opp": g.opp,
            "result": g.result,
            "opp_rating_game": g.opp_rating_game,
            "tournament": g.tournament,
            "url": g.url,
        })
    df = pd.DataFrame(rows)
    print(f"Total rated blitz games in sample: {len(df)}")

    if args.use_fide:
        print("Using FIDE ratings for band assignment...")
        # Load FIDE ratings
        fide_mapping = download_fide_ratings(args.min_opp, verbose=args.verbose)
        if not fide_mapping:
            print("ERROR: No FIDE ratings loaded. Make sure fide_blitz_ratings_2500+.json exists.")
            return 1
        
        # Get FIDE ratings for opponents
        print("Looking up FIDE ratings for opponents...")
        opp_fide_ratings, username_to_name = compute_fide_ratings_for_opponents(df["opp"].unique(), fide_mapping, verbose=args.verbose)
        
        # Map FIDE ratings to opponents
        df["opp_rating_band_avg"] = df["opp"].map(opp_fide_ratings)
        df["band"] = df["opp_rating_band_avg"].map(lambda r: assign_band_from_rating(r, use_fide=True))
    elif args.two_year_avg:
        window_start = since - relativedelta(years=2)
        window_end = until
        print(f"Computing opponents' two‑year average blitz ratings in [{window_start}, {window_end}] ...")
        avg_map = compute_two_year_avg_for_opponents(df["opp"].unique(), window_start, window_end)
        df["opp_rating_band_avg"] = df["opp"].map(avg_map)
        df["band"] = df["opp_rating_band_avg"].map(lambda r: assign_band_from_rating(r, use_fide=False))
    else:
        df["opp_rating_band_avg"] = df["opp_rating_game"]
        df["band"] = df["opp_rating_band_avg"].map(lambda r: assign_band_from_rating(r, use_fide=False))

    df = df[df["opp_rating_band_avg"].notnull()]
    df = df[df["opp_rating_band_avg"] >= args.min_opp]

    if df.empty:
        print("No games remain after applying rating filters/bands.")
        return 0

    summary = summarize_by_band(df)
    print("\nPerformance vs bands:")
    print(summary.to_string(index=False))

    ts_label = dt.datetime.now().strftime("%Y%m%d-%H%M%S")

    cnt = (
        df.groupby(["opp"])
          .agg(games=("result","size"), score=("result","sum"), avg_opp=("opp_rating_band_avg","mean"))
          .reset_index()
          .sort_values(["games","score"], ascending=[False, False])
    )
    cnt["score_pct"] = (cnt["score"]/cnt["games"]*100).round(1)
    
    # Add FIDE ratings if using FIDE mode
    if args.use_fide:
        print("Adding FIDE ratings to opponent breakdown...")
        # The FIDE ratings are already computed and stored in opp_fide_ratings
        # We just need to add them to the opponent breakdown
        cnt["fide_rating"] = cnt["opp"].map(opp_fide_ratings)
        cnt["real_name"] = cnt["opp"].map(username_to_name)
        
        # Save the FIDE mapping and username-to-name mapping for reference
        fide_mapping_file = f"{player}_fide_mapping_{ts_label}.json"
        username_mapping_file = f"{player}_username_mapping_{ts_label}.json"
        
        with open(os.path.join('data', fide_mapping_file), 'w') as f:
            json.dump(opp_fide_ratings, f, indent=2)
        print(f"Saved FIDE mapping to {fide_mapping_file}")
        
        with open(os.path.join('data', username_mapping_file), 'w') as f:
            json.dump(username_to_name, f, indent=2)
        print(f"Saved username-to-name mapping to {username_mapping_file}")
        
        # Show FIDE rating statistics
        fide_rated = cnt[cnt["fide_rating"].notna()]
        if len(fide_rated) > 0:
            print(f"Found FIDE ratings for {len(fide_rated)} out of {len(cnt)} opponents")
            print(f"FIDE rating range: {fide_rated['fide_rating'].min()} - {fide_rated['fide_rating'].max()}")
            print(f"Average FIDE rating: {fide_rated['fide_rating'].mean():.1f}")
    
    print("\nTop opponents by games (first 20):")
    print(cnt.head(20).to_string(index=False))
    df.to_csv(os.path.join('data', f"{player}_blitz_sample_{ts_label}.csv"), index=False)
    summary.to_csv(os.path.join('data', f"{player}_band_summary_{ts_label}.csv"), index=False)
    cnt.to_csv(os.path.join('data', f"{player}_opponent_breakdown_{ts_label}.csv"), index=False)
    print(f"\nSaved CSVs in data directory:\n"
          f"  {player}_blitz_sample_{ts_label}.csv\n"
          f"  {player}_band_summary_{ts_label}.csv\n"
          f"  {player}_opponent_breakdown_{ts_label}.csv")
    return 0

# Load API cache on module import
load_api_cache()

# Create data directory if it doesn't exist
if not os.path.exists('data'):
    os.makedirs('data')

if __name__ == "__main__":
    sys.exit(main())
