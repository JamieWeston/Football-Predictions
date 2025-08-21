import os
import csv
import json
from datetime import datetime

print("=" * 60)
print("DATA CHECK SCRIPT")
print("=" * 60)

# Check what files exist
print("\n📁 Checking files in data directory:")
if os.path.exists('data'):
    files = os.listdir('data')
    for file in files:
        file_path = os.path.join('data', file)
        size = os.path.getsize(file_path)
        print(f"  - {file}: {size} bytes")
else:
    print("  ❌ No data directory found!")

# Check predictions.json
print("\n📊 Checking predictions.json:")
if os.path.exists('predictions.json'):
    try:
        with open('predictions.json', 'r') as f:
            data = json.load(f)
        print(f"  ✅ File exists")
        print(f"  Generated: {data.get('generated', 'Unknown')}")
        print(f"  Total matches: {data.get('total_matches', 0)}")
        print(f"  Season: {data.get('season', 'Unknown')}")
        
        if 'predictions' in data and data['predictions']:
            print(f"\n  First prediction:")
            first = data['predictions'][0]
            print(f"    {first.get('home_team', 'Unknown')} vs {first.get('away_team', 'Unknown')}")
            print(f"    Date: {first.get('date', 'Unknown')}")
            print(f"    Probabilities: {first.get('probabilities', {})}")
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
else:
    print("  ❌ predictions.json does not exist!")

# Check upcoming matches
print("\n📅 Checking upcoming_matches.csv:")
if os.path.exists('data/upcoming_matches.csv'):
    try:
        with open('data/upcoming_matches.csv', 'r') as f:
            reader = csv.DictReader(f)
            matches = list(reader)
        print(f"  ✅ File exists with {len(matches)} matches")
        if matches:
            print(f"  First match: {matches[0].get('home_team', 'Unknown')} vs {matches[0].get('away_team', 'Unknown')}")
            print(f"  Date: {matches[0].get('date', 'Unknown')}")
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
else:
    print("  ❌ upcoming_matches.csv does not exist!")

# Check historical matches
print("\n📈 Checking historical_matches.csv:")
if os.path.exists('data/historical_matches.csv'):
    try:
        with open('data/historical_matches.csv', 'r') as f:
            reader = csv.DictReader(f)
            matches = list(reader)
        print(f"  ✅ File exists with {len(matches)} matches")
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
else:
    print("  ❌ historical_matches.csv does not exist!")

# Check old matches.csv
print("\n📝 Checking data/matches.csv (old format):")
if os.path.exists('data/matches.csv'):
    try:
        with open('data/matches.csv', 'r') as f:
            reader = csv.DictReader(f)
            matches = list(reader)
        print(f"  ✅ File exists with {len(matches)} matches")
        if matches:
            print(f"  First match date: {matches[0].get('date', 'Unknown')}")
            print(f"  Last match date: {matches[-1].get('date', 'Unknown')}")
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
else:
    print("  ❌ matches.csv does not exist")

print("\n" + "=" * 60)
print("END OF CHECK")
print("=" * 60)
