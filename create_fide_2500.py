#!/usr/bin/env python3
"""
Script to correctly parse FIDE ratings data and create a clean JSON file with 2500+ ratings.
"""

import json
import re
import os
import subprocess
import sys

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

def parse_fide_ratings_correct(data: str, min_rating: int = 2500) -> dict:
    """Parse FIDE ratings data correctly using fixed-width column positions."""
    fide_mapping = {}
    
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

def main():
    # Check if FIDE data file exists, download if needed
    fide_file = "players_list_foa.txt"
    
    # Try to download if file doesn't exist
    if not os.path.exists(fide_file):
        print("FIDE players list not found. Attempting to download...")
        if not download_fide_players_list(verbose=True):
            print("Failed to download FIDE players list. Please ensure you have internet access and curl/unzip installed.")
            return 1
    
    try:
        with open(fide_file, 'r', encoding='utf-8', errors='ignore') as f:
            data = f.read()
        
        # Parse for 2500+ ratings with correct logic
        fide_data_2500 = parse_fide_ratings_correct(data, 2500)
        
        if fide_data_2500:
            # Sort the data by rating in descending order
            sorted_fide_data = dict(sorted(fide_data_2500.items(), key=lambda x: x[1], reverse=True))
            
            # Save to JSON file
            output_file = "fide_blitz_ratings_2500+.json"
            with open(output_file, 'w') as f:
                json.dump(sorted_fide_data, f, indent=2)
            print(f"Saved {len(sorted_fide_data)} FIDE ratings to {output_file} (sorted by rating)")
            
            # Show some statistics
            ratings = list(sorted_fide_data.values())
            print(f"Rating range: {min(ratings)} - {max(ratings)}")
            print(f"Average rating: {sum(ratings) / len(ratings):.1f}")
            
            # Show some examples (top 10 highest rated)
            print("\nTop 10 highest rated players:")
            for i, (name, rating) in enumerate(list(sorted_fide_data.items())[:10]):
                print(f"  {name}: {rating}")
                
            # Check for any remaining high ratings
            high_ratings = [(name, rating) for name, rating in sorted_fide_data.items() if rating > 3000]
            if high_ratings:
                print(f"\nHigh ratings (>3000): {len(high_ratings)}")
                for name, rating in sorted(high_ratings, key=lambda x: x[1], reverse=True)[:5]:
                    print(f"  {name}: {rating}")
        else:
            print("No FIDE data parsed")
            
    except Exception as e:
        print(f"Error reading FIDE data file: {e}")

if __name__ == "__main__":
    main()
