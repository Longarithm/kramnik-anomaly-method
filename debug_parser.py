#!/usr/bin/env python3

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

def test_parser():
    print("Testing FIDE parser on sample data...")
    
    # Read a small sample
    with open('players_list_foa.txt', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()[:50]  # First 50 lines
    
    print(f"Read {len(lines)} lines")
    
    i = 0
    processed = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip header lines
        if not line or line.startswith('ID Number') or line.startswith('FOA'):
            i += 1
            continue
            
        # Check if this looks like a player line (starts with FIDE ID)
        if len(line) > 12 and line[:12].strip().isdigit():
            try:
                # Parse player info line
                fide_id = line[:12].strip()
                name = line[12:72].strip()
                fed = line[72:75].strip()
                sex = line[75:76].strip()
                tit = line[76:79].strip()
                
                print(f"Player: {name} ({fed}) {tit}")
                
                if not fide_id or not name or name == '-' or name == '-, -':
                    i += 1
                    continue
                
                # Get the next line for rating info (starts with spaces)
                if i + 1 < len(lines):
                    rating_line = lines[i + 1]
                    print(f"Rating line: '{rating_line}'")
                    print(f"Starts with spaces: {rating_line.startswith('      ')}")
                    
                    # Check if it's a rating line (starts with spaces)
                    if rating_line.startswith('      '):
                        # Parse rating line: FOA SRtng SGm SK RRtng RGm Rk BRtng BGm BK B-day Flag
                        parts = rating_line.strip().split()
                        print(f"Rating parts: {parts}")
                        if len(parts) >= 2:
                            try:
                                std_rating = int(parts[1]) if parts[1] != '0' else 0
                                print(f"Standard rating: {std_rating}")
                                
                                if std_rating >= 2600:
                                    normalized_name = normalize_fide_name(name)
                                    print(f"Normalized name: {normalized_name}")
                                    processed += 1
                            except ValueError as e:
                                print(f"Error parsing rating: {e}")
                                std_rating = 0
                        else:
                            std_rating = 0
                    else:
                        std_rating = 0
                else:
                    std_rating = 0
                
                i += 2  # Skip both lines
                
            except Exception as e:
                print(f"Error parsing line: {e}")
                i += 1
        else:
            i += 1
    
    print(f"\nProcessed {processed} players with rating >= 2600")

if __name__ == "__main__":
    test_parser()
