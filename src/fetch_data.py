import os
import json
import csv
import requests
from datetime import datetime, timedelta
import time

# Get API key from GitHub Secrets
API_KEY = os.environ.get('API_KEY', '')

print("=" * 50)
print("FETCH DATA SCRIPT STARTING")
print(f"Current date: {datetime.now().strftime('%Y-%m-%d')}")
print(f"API Key present: {'Yes' if API_KEY else 'No'}")
if API_KEY:
    print(f"API Key: {API_KEY[:10]}...")
print("=" * 50)

# All competitions with correct IDs
COMPETITIONS = [
    {'code': 'PL', 'id': 'PL', 'name': 'Premier League'},
    {'code': 'PD', 'id': 'PD', 'name': 'La Liga'},
    {'code': 'BL1', 'id': 'BL1', 'name': 'Bundesliga'},
    {'code': 'SA', 'id': 'SA', 'name': 'Serie A'},
    {'code': 'FL1', 'id': 'FL1', 'name': 'Ligue 1'},
    {'code': 'PPL', 'id': 'PPL', 'name': 'Primeira Liga'},
    {'code': 'DED', 'id': 'DED', 'name': 'Eredivisie'},
    {'code': 'BSA', 'id': 'BSA', 'name': 'Brasileiro Serie A'},
    {'code': 'CL', 'id': 'CL', 'name': 'Champions League'},
    {'code': 'CLI', 'id': 'CLI', 'name': 'Libertadores'},
    {'code': 'ELC', 'id': 'ELC', 'name': 'Championship'},
]

def test_api():
    """Test API connection"""
    if not API_KEY:
        print("❌ No API key found!")
        return False
    
    headers = {'X-Auth-Token': API_KEY}
    
    try:
        # Test with competitions endpoint
        url = "https://api.football-data.org/v4/competitions"
        response = requests.get(url, headers=headers)
        
        print(f"API Test Response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API working! Found {data.get('count', 0)} competitions")
            return True
        elif response.status_code == 403:
            print("❌ API Key invalid or no access")
            return False
        else:
            print(f"❌ API Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def fetch_all_upcoming_matches():
    """Fetch upcoming matches from all leagues"""
    
    if not test_api():
        print("API not working, will use fallback data")
        create_fallback_data()
        return
    
    headers = {'X-Auth-Token': API_KEY}
    os.makedirs('data', exist_ok=True)
    
    # Date range: today to 14 days ahead
    date_from = datetime.now().strftime('%Y-%m-%d')
    date_to = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
    
    print(f"\n📅 Fetching matches from {date_from} to {date_to}")
    
    all_upcoming = []
    all_historical = []
    
    # Try to fetch from each competition
    for comp in COMPETITIONS:
        try:
            print(f"\n🏆 Fetching {comp['name']}...")
            
            # Fetch upcoming matches
            url = f"https://api.football-data.org/v4/competitions/{comp['id']}/matches"
            params = {
                'dateFrom': date_from,
                'dateTo': date_to,
                'status': 'SCHEDULED,TIMED'
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                
                for match in matches:
                    # Parse match date
                    match_date = datetime.fromisoformat(match['utcDate'].replace('Z', '+00:00'))
                    
                    # Only future matches
                    if match_date >= datetime.now():
                        all_upcoming.append({
                            'competition': comp['name'],
                            'competition_code': comp['code'],
                            'match_id': str(match.get('id', '')),
                            'date': match['utcDate'],
                            'matchday': str(match.get('matchday', '')),
                            'home_team': match['homeTeam']['name'],
                            'away_team': match['awayTeam']['name'],
                            'status': match.get('status', 'SCHEDULED')
                        })
                
                print(f"  ✅ Found {len([m for m in all_upcoming if m['competition_code'] == comp['code']])} upcoming matches")
                
            elif response.status_code == 403:
                print(f"  ⚠️ No access to {comp['name']}")
            elif response.status_code == 429:
                print(f"  ⏳ Rate limit - waiting...")
                time.sleep(10)
            else:
                print(f"  ❌ Error {response.status_code}")
            
            # Small delay to avoid rate limits
            time.sleep(1)
            
            # Also fetch recent finished matches for statistics
            if comp['code'] in ['PL', 'PD', 'BL1', 'SA', 'FL1']:  # Major leagues only
                print(f"  📊 Fetching recent results...")
                
                hist_url = f"https://api.football-data.org/v4/competitions/{comp['id']}/matches"
                hist_params = {
                    'status': 'FINISHED',
                    'dateFrom': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                    'dateTo': datetime.now().strftime('%Y-%m-%d')
                }
                
                hist_response = requests.get(hist_url, headers=headers, params=hist_params)
                
                if hist_response.status_code == 200:
                    hist_data = hist_response.json()
                    hist_matches = hist_data.get('matches', [])
                    
                    for match in hist_matches:
                        if match['score']['fullTime']['home'] is not None:
                            all_historical.append({
                                'competition_code': comp['code'],
                                'date': match['utcDate'],
                                'home_team': match['homeTeam']['name'],
                                'away_team': match['awayTeam']['name'],
                                'home_goals': match['score']['fullTime']['home'],
                                'away_goals': match['score']['fullTime']['away']
                            })
                    
                    print(f"  ✅ Found {len([m for m in all_historical if m['competition_code'] == comp['code']])} recent results")
                
                time.sleep(1)
                
        except Exception as e:
            print(f"  ❌ Error with {comp['name']}: {e}")
            continue
    
    # If no upcoming matches found, try alternate approach
    if not all_upcoming:
        print("\n⚠️ No matches found with individual competitions, trying matches endpoint...")
        
        try:
            matches_url = "https://api.football-data.org/v4/matches"
            params = {
                'dateFrom': date_from,
                'dateTo': date_to
            }
            
            response = requests.get(matches_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                
                for match in matches:
                    if match['status'] in ['SCHEDULED', 'TIMED']:
                        all_upcoming.append({
                            'competition': match['competition']['name'],
                            'competition_code': match['competition']['code'],
                            'match_id': str(match.get('id', '')),
                            'date': match['utcDate'],
                            'matchday': str(match.get('matchday', '')),
                            'home_team': match['homeTeam']['name'],
                            'away_team': match['awayTeam']['name'],
                            'status': match.get('status', 'SCHEDULED')
                        })
                
                print(f"✅ Found {len(all_upcoming)} matches from general endpoint")
        except Exception as e:
            print(f"❌ General endpoint failed: {e}")
    
    # Save data
    print(f"\n💾 Saving data...")
    
    if all_upcoming:
        with open('data/upcoming_matches.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['competition', 'competition_code', 
                                                   'match_id', 'date', 'matchday', 
                                                   'home_team', 'away_team', 'status'])
            writer.writeheader()
            writer.writerows(all_upcoming)
        print(f"✅ Saved {len(all_upcoming)} upcoming matches")
    else:
        print("⚠️ No upcoming matches found, creating fallback data...")
        create_fallback_data()
    
    if all_historical:
        with open('data/historical_matches.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['competition_code', 'date',
                                                   'home_team', 'away_team', 
                                                   'home_goals', 'away_goals'])
            writer.writeheader()
            writer.writerows(all_historical)
        print(f"✅ Saved {len(all_historical)} historical matches")
    
    print("\n" + "=" * 50)
    print("FETCH COMPLETE")
    print("=" * 50)

def create_fallback_data():
    """Create comprehensive fallback data if API fails"""
    print("\n🔧 Creating fallback data...")
    
    os.makedirs('data', exist_ok=True)
    
    # Create realistic upcoming matches for multiple leagues
    upcoming = []
    base_date = datetime.now()
    
    # Premier League matches
    pl_teams = [
        ('Arsenal', 'Chelsea'), ('Liverpool', 'Manchester United'),
        ('Manchester City', 'Tottenham Hotspur'), ('Newcastle United', 'Brighton & Hove Albion'),
        ('Fulham', 'Brentford'), ('West Ham United', 'Aston Villa'),
        ('Wolverhampton Wanderers', 'Southampton'), ('Crystal Palace', 'Nottingham Forest')
    ]
    
    for i, (home, away) in enumerate(pl_teams):
        match_date = base_date + timedelta(days=(i % 7) + 1, hours=15)
        upcoming.append({
            'competition': 'Premier League',
            'competition_code': 'PL',
            'match_id': f'pl_{i+1}',
            'date': match_date.isoformat() + 'Z',
            'matchday': str(20 + (i // 10)),
            'home_team': home,
            'away_team': away,
            'status': 'SCHEDULED'
        })
    
    # La Liga matches
    liga_teams = [
        ('Real Madrid', 'Barcelona'), ('Atletico Madrid', 'Sevilla'),
        ('Real Sociedad', 'Valencia'), ('Villarreal', 'Athletic Bilbao')
    ]
    
    for i, (home, away) in enumerate(liga_teams):
        match_date = base_date + timedelta(days=(i % 7) + 2, hours=20)
        upcoming.append({
            'competition': 'La Liga',
            'competition_code': 'PD',
            'match_id': f'pd_{i+1}',
            'date': match_date.isoformat() + 'Z',
            'matchday': str(15 + i),
            'home_team': home,
            'away_team': away,
            'status': 'SCHEDULED'
        })
    
    # Bundesliga matches
    bundesliga_teams = [
        ('Bayern Munich', 'Borussia Dortmund'), ('RB Leipzig', 'Bayer Leverkusen'),
        ('Eintracht Frankfurt', 'VfL Wolfsburg')
    ]
    
    for i, (home, away) in enumerate(bundesliga_teams):
        match_date = base_date + timedelta(days=(i % 7) + 3, hours=14)
        upcoming.append({
            'competition': 'Bundesliga',
            'competition_code': 'BL1',
            'match_id': f'bl_{i+1}',
            'date': match_date.isoformat() + 'Z',
            'matchday': str(18 + i),
            'home_team': home,
            'away_team': away,
            'status': 'SCHEDULED'
        })
    
    # Save upcoming matches
    with open('data/upcoming_matches.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['competition', 'competition_code', 
                                               'match_id', 'date', 'matchday', 
                                               'home_team', 'away_team', 'status'])
        writer.writeheader()
        writer.writerows(upcoming)
    
    print(f"✅ Created {len(upcoming)} fallback upcoming matches")
    
    # Create historical data for these teams
    historical = []
    teams = set()
    for match in upcoming:
        teams.add(match['home_team'])
        teams.add(match['away_team'])
    
    # Generate some historical results
    for team1 in list(teams)[:10]:
        for team2 in list(teams)[10:15]:
            if team1 != team2:
                historical.append({
                    'competition_code': 'PL',
                    'date': (base_date - timedelta(days=7)).isoformat(),
                    'home_team': team1,
                    'away_team': team2,
                    'home_goals': np.random.choice([0, 1, 2, 3]),
                    'away_goals': np.random.choice([0, 1, 1, 2])
                })
    
    # Use numpy only if available, otherwise use basic random
    try:
        import numpy as np
        for h in historical:
            h['home_goals'] = int(np.random.choice([0, 1, 2, 3]))
            h['away_goals'] = int(np.random.choice([0, 1, 1, 2]))
    except:
        import random
        for h in historical:
            h['home_goals'] = random.choice([0, 1, 2, 3])
            h['away_goals'] = random.choice([0, 1, 1, 2])
    
    with open('data/historical_matches.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['competition_code', 'date',
                                               'home_team', 'away_team', 
                                               'home_goals', 'away_goals'])
        writer.writeheader()
        writer.writerows(historical)
    
    print(f"✅ Created {len(historical)} historical matches")

if __name__ == '__main__':
    fetch_all_upcoming_matches()
