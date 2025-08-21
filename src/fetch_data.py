import os
import json
import csv
import requests
from datetime import datetime, timedelta

# Get API key from GitHub Secrets
API_KEY = os.environ.get('API_KEY', '')

print("=" * 50)
print("FETCH DATA SCRIPT STARTING")
print(f"Current time: {datetime.now().isoformat()}")
print(f"API Key present: {'Yes' if API_KEY else 'No'}")
if API_KEY:
    print(f"API Key starts with: {API_KEY[:8]}...")
print("=" * 50)

# All Football-Data.org competitions
COMPETITIONS = {
    'PL': {'id': 2021, 'name': 'Premier League', 'country': 'England'},
}

def test_api_connection():
    """Test if API key works"""
    if not API_KEY:
        print("ERROR: No API key found in environment!")
        print("Check that FOOTBALL_API_KEY is set in GitHub Secrets")
        return False
    
    print("\nTesting API connection...")
    headers = {'X-Auth-Token': API_KEY}
    
    try:
        # Test with a simple endpoint
        test_url = "https://api.football-data.org/v4/competitions/PL"
        response = requests.get(test_url, headers=headers)
        
        print(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API connection successful!")
            data = response.json()
            print(f"Competition: {data.get('name', 'Unknown')}")
            print(f"Current Season: {data.get('currentSeason', {}).get('startDate', 'Unknown')}")
            return True
        elif response.status_code == 403:
            print("❌ API Key is invalid or doesn't have access")
            print("Please check your API key in GitHub Secrets")
            return False
        elif response.status_code == 429:
            print("⚠️ Rate limit exceeded. Wait a moment and try again.")
            return False
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False

def fetch_with_fallback():
    """Fetch data with multiple fallback options"""
    
    print("\n" + "=" * 50)
    print("ATTEMPTING TO FETCH DATA")
    print("=" * 50)
    
    # First, test API connection
    if not test_api_connection():
        print("\n⚠️ API connection failed, using fallback data")
        create_fallback_data()
        return
    
    headers = {'X-Auth-Token': API_KEY}
    os.makedirs('data', exist_ok=True)
    
    # Try to fetch upcoming matches
    print("\n📅 Fetching upcoming matches...")
    
    upcoming_matches = []
    historical_matches = []
    
    try:
        # Try multiple endpoints to find matches
        endpoints_to_try = [
            ("Scheduled matches", f"https://api.football-data.org/v4/competitions/PL/matches?status=SCHEDULED"),
            ("Timed matches", f"https://api.football-data.org/v4/competitions/PL/matches?status=TIMED"),
            ("All upcoming", f"https://api.football-data.org/v4/competitions/PL/matches?dateFrom={datetime.now().strftime('%Y-%m-%d')}&dateTo={(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')}"),
            ("Current matchday", f"https://api.football-data.org/v4/competitions/PL/matches?matchday={datetime.now().isocalendar()[1]}")
        ]
        
        for endpoint_name, url in endpoints_to_try:
            print(f"\nTrying: {endpoint_name}")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                print(f"  Found {len(matches)} matches")
                
                for match in matches:
                    if match['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED']:
                        upcoming_matches.append({
                            'competition': 'Premier League',
                            'competition_code': 'PL',
                            'country': 'England',
                            'match_id': str(match['id']),
                            'date': match['utcDate'],
                            'matchday': match.get('matchday', ''),
                            'home_team': match['homeTeam']['name'],
                            'away_team': match['awayTeam']['name'],
                            'status': match['status'],
                            'season': '2025/26'
                        })
                
                if upcoming_matches:
                    print(f"  ✅ Successfully found {len(upcoming_matches)} upcoming matches")
                    break
            else:
                print(f"  Status {response.status_code}")
    
    except Exception as e:
        print(f"❌ Error fetching upcoming matches: {e}")
    
    # Also fetch recent finished matches for statistics
    print("\n📊 Fetching historical matches for statistics...")
    
    try:
        hist_url = "https://api.football-data.org/v4/competitions/PL/matches?status=FINISHED&limit=100"
        response = requests.get(hist_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            print(f"  Found {len(matches)} finished matches")
            
            for match in matches:
                if match['score']['fullTime']['home'] is not None:
                    historical_matches.append({
                        'competition': 'Premier League',
                        'competition_code': 'PL',
                        'date': match['utcDate'],
                        'home_team': match['homeTeam']['name'],
                        'away_team': match['awayTeam']['name'],
                        'home_goals': match['score']['fullTime']['home'],
                        'away_goals': match['score']['fullTime']['away']
                    })
    
    except Exception as e:
        print(f"⚠️ Error fetching historical matches: {e}")
    
    # Check if we have data
    print("\n" + "=" * 50)
    print("DATA FETCH SUMMARY")
    print("=" * 50)
    print(f"Upcoming matches found: {len(upcoming_matches)}")
    print(f"Historical matches found: {len(historical_matches)}")
    
    # If no upcoming matches, create some sample ones
    if not upcoming_matches:
        print("\n⚠️ No upcoming matches found from API")
        print("Creating sample upcoming matches for testing...")
        
        # Create sample upcoming matches
        teams = [
            ('Arsenal', 'Chelsea'),
            ('Liverpool', 'Manchester United'),
            ('Manchester City', 'Tottenham Hotspur'),
            ('Newcastle United', 'Brighton & Hove Albion'),
            ('Fulham', 'Brentford')
        ]
        
        for i, (home, away) in enumerate(teams):
            match_date = datetime.now() + timedelta(days=i+1)
            upcoming_matches.append({
                'competition': 'Premier League',
                'competition_code': 'PL',
                'country': 'England',
                'match_id': f'sample_{i+1}',
                'date': match_date.isoformat() + 'Z',
                'matchday': str(20 + i),
                'home_team': home,
                'away_team': away,
                'status': 'SCHEDULED',
                'season': '2025/26'
            })
        
        print(f"✅ Created {len(upcoming_matches)} sample upcoming matches")
    
    # If no historical matches, use the existing matches.csv if it exists
    if not historical_matches and os.path.exists('data/matches.csv'):
        print("\nUsing existing data/matches.csv for historical data...")
        try:
            with open('data/matches.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    historical_matches.append({
                        'competition': 'Premier League',
                        'competition_code': 'PL',
                        'date': row['date'],
                        'home_team': row['home_team'],
                        'away_team': row['away_team'],
                        'home_goals': int(row['home_goals']),
                        'away_goals': int(row['away_goals'])
                    })
            print(f"✅ Loaded {len(historical_matches)} matches from existing CSV")
        except Exception as e:
            print(f"⚠️ Could not load existing matches.csv: {e}")
    
    # Save upcoming matches
    if upcoming_matches:
        csv_path = 'data/upcoming_matches.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['competition', 'competition_code', 'country', 
                                                   'match_id', 'date', 'matchday', 
                                                   'home_team', 'away_team', 'status', 'season'])
            writer.writeheader()
            writer.writerows(upcoming_matches)
        print(f"\n✅ Saved {len(upcoming_matches)} upcoming matches to {csv_path}")
    
    # Save historical matches
    if historical_matches:
        csv_path = 'data/historical_matches.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['competition', 'competition_code', 'date',
                                                   'home_team', 'away_team', 'home_goals', 'away_goals'])
            writer.writeheader()
            writer.writerows(historical_matches)
        print(f"✅ Saved {len(historical_matches)} historical matches to {csv_path}")
    
    print("\n" + "=" * 50)
    print("FETCH DATA SCRIPT COMPLETE")
    print("=" * 50)

def create_fallback_data():
    """Create fallback data when API is not available"""
    print("\nCreating fallback data...")
    
    os.makedirs('data', exist_ok=True)
    
    # Create sample upcoming matches
    upcoming = []
    teams = [
        ('Arsenal', 'Chelsea'),
        ('Liverpool', 'Manchester United'),
        ('Manchester City', 'Tottenham Hotspur'),
        ('Newcastle United', 'Brighton & Hove Albion'),
        ('Fulham', 'Brentford'),
        ('West Ham United', 'Aston Villa'),
        ('Wolverhampton Wanderers', 'Southampton'),
        ('Crystal Palace', 'Nottingham Forest'),
        ('Everton', 'Leicester City'),
        ('Bournemouth', 'Ipswich Town')
    ]
    
    for i, (home, away) in enumerate(teams):
        match_date = datetime.now() + timedelta(days=(i % 7) + 1)
        upcoming.append({
            'competition': 'Premier League',
            'competition_code': 'PL',
            'country': 'England',
            'match_id': f'fallback_{i+1}',
            'date': match_date.isoformat() + 'Z',
            'matchday': str(20 + (i // 10)),
            'home_team': home,
            'away_team': away,
            'status': 'SCHEDULED',
            'season': '2025/26'
        })
    
    # Save upcoming matches
    with open('data/upcoming_matches.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['competition', 'competition_code', 'country', 
                                               'match_id', 'date', 'matchday', 
                                               'home_team', 'away_team', 'status', 'season'])
        writer.writeheader()
        writer.writerows(upcoming)
    
    print(f"✅ Created {len(upcoming)} fallback upcoming matches")
    
    # Try to use existing matches.csv for historical data
    if os.path.exists('data/matches.csv'):
        print("✅ Using existing data/matches.csv for historical data")
        # Convert format
        historical = []
        try:
            with open('data/matches.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    historical.append({
                        'competition': 'Premier League',
                        'competition_code': 'PL',
                        'date': row['date'],
                        'home_team': row['home_team'],
                        'away_team': row['away_team'],
                        'home_goals': row['home_goals'],
                        'away_goals': row['away_goals']
                    })
            
            # Save as historical_matches.csv
            with open('data/historical_matches.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['competition', 'competition_code', 'date',
                                                       'home_team', 'away_team', 'home_goals', 'away_goals'])
                writer.writeheader()
                writer.writerows(historical)
            
            print(f"✅ Converted {len(historical)} historical matches")
        except Exception as e:
            print(f"⚠️ Could not convert matches.csv: {e}")

if __name__ == '__main__':
    fetch_with_fallback()
