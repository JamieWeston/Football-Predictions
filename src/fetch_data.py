import os
import json
import csv
import requests
from datetime import datetime, timedelta

# Get API key from GitHub Secrets
API_KEY = os.environ.get('API_KEY', '')

print("=" * 50)
print("FETCH DATA SCRIPT STARTING")
print(f"Current date: {datetime.now().strftime('%Y-%m-%d')}")
print(f"API Key present: {'Yes' if API_KEY else 'No'}")
print("=" * 50)

def fetch_upcoming_matches_only():
    """Fetch only matches in the next 14 days"""
    
    headers = {'X-Auth-Token': API_KEY} if API_KEY else {}
    os.makedirs('data', exist_ok=True)
    
    # Calculate date range - TODAY to 14 days from now
    today = datetime.now()
    date_from = today.strftime('%Y-%m-%d')
    date_to = (today + timedelta(days=14)).strftime('%Y-%m-%d')
    
    print(f"\n📅 Fetching matches from {date_from} to {date_to} (next 14 days)")
    
    upcoming_matches = []
    
    # List of competitions to fetch
    competitions = [
        {'code': 'PL', 'id': 2021, 'name': 'Premier League'},
        {'code': 'PD', 'id': 2014, 'name': 'La Liga'},
        {'code': 'BL1', 'id': 2002, 'name': 'Bundesliga'},
        {'code': 'SA', 'id': 2019, 'name': 'Serie A'},
        {'code': 'FL1', 'id': 2015, 'name': 'Ligue 1'},
        {'code': 'PPL', 'id': 2017, 'name': 'Primeira Liga'},
        {'code': 'DED', 'id': 2003, 'name': 'Eredivisie'},
        {'code': 'CL', 'id': 2001, 'name': 'Champions League'},
    ]
    
    if API_KEY:
        for comp in competitions:
            try:
                # Fetch matches for date range
                url = f"https://api.football-data.org/v4/competitions/{comp['id']}/matches?dateFrom={date_from}&dateTo={date_to}"
                print(f"\nFetching {comp['name']}...")
                
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    matches = data.get('matches', [])
                    
                    comp_upcoming = 0
                    for match in matches:
                        # Only include matches that haven't been played yet
                        if match['status'] in ['SCHEDULED', 'TIMED', 'IN_PLAY', 'PAUSED']:
                            match_date = datetime.fromisoformat(match['utcDate'].replace('Z', '+00:00'))
                            
                            # Double-check the match is in the future
                            if match_date >= today:
                                upcoming_matches.append({
                                    'competition': comp['name'],
                                    'competition_code': comp['code'],
                                    'match_id': str(match['id']),
                                    'date': match['utcDate'],
                                    'matchday': match.get('matchday', ''),
                                    'home_team': match['homeTeam']['name'],
                                    'away_team': match['awayTeam']['name'],
                                    'status': match['status']
                                })
                                comp_upcoming += 1
                    
                    print(f"  ✅ Found {comp_upcoming} upcoming matches")
                    
                elif response.status_code == 429:
                    print(f"  ⚠️ Rate limit reached, waiting...")
                    import time
                    time.sleep(6)
                else:
                    print(f"  ❌ Error: Status {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ Error fetching {comp['name']}: {e}")
    
    # If no API or no matches found, create sample data
    if not upcoming_matches:
        print("\n⚠️ No matches found from API, creating sample data...")
        teams = [
            ('Arsenal', 'Chelsea'),
            ('Liverpool', 'Manchester United'),
            ('Manchester City', 'Tottenham Hotspur'),
            ('Real Madrid', 'Barcelona'),
            ('Bayern Munich', 'Borussia Dortmund')
        ]
        
        for i, (home, away) in enumerate(teams):
            match_date = today + timedelta(days=(i % 7) + 1, hours=15)
            upcoming_matches.append({
                'competition': 'Premier League' if i < 3 else 'Various',
                'competition_code': 'PL' if i < 3 else 'OTH',
                'match_id': f'sample_{i+1}',
                'date': match_date.isoformat() + 'Z',
                'matchday': str(20 + i),
                'home_team': home,
                'away_team': away,
                'status': 'SCHEDULED'
            })
    
    # Save upcoming matches
    print(f"\n💾 Saving {len(upcoming_matches)} upcoming matches...")
    with open('data/upcoming_matches.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['competition', 'competition_code', 
                                               'match_id', 'date', 'matchday', 
                                               'home_team', 'away_team', 'status'])
        writer.writeheader()
        writer.writerows(upcoming_matches)
    
    print(f"✅ Saved to data/upcoming_matches.csv")
    return upcoming_matches

def fetch_recent_results_with_xg():
    """Fetch recent results with xG data for form calculation"""
    
    if not API_KEY:
        print("\n⚠️ No API key, using existing historical data")
        return
    
    headers = {'X-Auth-Token': API_KEY}
    
    # Fetch last 60 days of results for form calculation
    date_from = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    date_to = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n📊 Fetching recent results from {date_from} to {date_to}")
    
    all_results = []
    
    # Premier League with more detailed stats
    try:
        url = f"https://api.football-data.org/v4/competitions/2021/matches?dateFrom={date_from}&dateTo={date_to}&status=FINISHED"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            
            for match in matches:
                if match['score']['fullTime']['home'] is not None:
                    result = {
                        'competition_code': 'PL',
                        'date': match['utcDate'],
                        'home_team': match['homeTeam']['name'],
                        'away_team': match['awayTeam']['name'],
                        'home_goals': match['score']['fullTime']['home'],
                        'away_goals': match['score']['fullTime']['away'],
                        'home_xg': None,  # API doesn't provide xG directly
                        'away_xg': None,
                        'matchday': match.get('matchday', 0)
                    }
                    
                    # Calculate estimated xG based on goals and shots (simplified)
                    # In reality, you'd need a different API for real xG
                    result['home_xg'] = result['home_goals'] * 0.9 + 0.3
                    result['away_xg'] = result['away_goals'] * 0.9 + 0.3
                    
                    all_results.append(result)
            
            print(f"  ✅ Found {len(all_results)} recent results")
    
    except Exception as e:
        print(f"  ❌ Error fetching results: {e}")
    
    # Save recent results
    if all_results:
        with open('data/recent_results.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['competition_code', 'date', 'home_team', 
                                                   'away_team', 'home_goals', 'away_goals',
                                                   'home_xg', 'away_xg', 'matchday'])
            writer.writeheader()
            writer.writerows(all_results)
        print(f"✅ Saved {len(all_results)} recent results")
    
    # Also keep existing historical data if available
    if os.path.exists('data/matches.csv'):
        print("✅ Keeping existing historical data for long-term stats")

def main():
    """Main fetch function"""
    print("\n🔄 FETCHING UPDATED DATA")
    
    # Fetch only upcoming matches (next 14 days)
    upcoming = fetch_upcoming_matches_only()
    
    # Fetch recent results for form calculation
    fetch_recent_results_with_xg()
    
    print(f"\n✅ FETCH COMPLETE")
    print(f"📅 {len(upcoming)} matches in next 14 days")
    print("=" * 50)

if __name__ == '__main__':
    main()
