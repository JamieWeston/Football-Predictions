import os
import json
import csv
import requests
from datetime import datetime, timedelta

# Get API key from GitHub Secrets
API_KEY = os.environ.get('API_KEY', '')

# All Football-Data.org competitions
COMPETITIONS = {
    'PL': {'id': 2021, 'name': 'Premier League', 'country': 'England'},
    'ELC': {'id': 2016, 'name': 'Championship', 'country': 'England'},
    'BL1': {'id': 2002, 'name': 'Bundesliga', 'country': 'Germany'},
    'BL2': {'id': 2003, 'name': '2. Bundesliga', 'country': 'Germany'},
    'SA': {'id': 2019, 'name': 'Serie A', 'country': 'Italy'},
    'PD': {'id': 2014, 'name': 'La Liga', 'country': 'Spain'},
    'SD': {'id': 2077, 'name': 'Segunda Division', 'country': 'Spain'},
    'FL1': {'id': 2015, 'name': 'Ligue 1', 'country': 'France'},
    'FL2': {'id': 2142, 'name': 'Ligue 2', 'country': 'France'},
    'PPL': {'id': 2017, 'name': 'Primeira Liga', 'country': 'Portugal'},
    'DED': {'id': 2003, 'name': 'Eredivisie', 'country': 'Netherlands'},
    'BSA': {'id': 2013, 'name': 'Serie A', 'country': 'Brazil'},
    'CL': {'id': 2001, 'name': 'Champions League', 'country': 'Europe'},
    'EL': {'id': 2146, 'name': 'Europa League', 'country': 'Europe'},
    'EC': {'id': 2018, 'name': 'European Championship', 'country': 'Europe'},
    'WC': {'id': 2000, 'name': 'World Cup', 'country': 'World'},
}

def fetch_all_upcoming_matches():
    """Fetch upcoming matches for ALL leagues from Football-Data.org"""
    
    if not API_KEY:
        print("ERROR: No API key found!")
        print("Make sure FOOTBALL_API_KEY is set in GitHub Secrets")
        return None
    
    print(f"Using API key: {API_KEY[:8]}...")
    
    headers = {
        'X-Auth-Token': API_KEY
    }
    
    os.makedirs('data', exist_ok=True)
    
    all_upcoming_matches = []
    all_historical_matches = []
    
    # Fetch data for each competition
    for comp_code, comp_info in COMPETITIONS.items():
        try:
            print(f"\nFetching {comp_info['name']} ({comp_info['country']})...")
            
            # Fetch UPCOMING matches (SCHEDULED, TIMED, IN_PLAY)
            upcoming_url = f"https://api.football-data.org/v4/competitions/{comp_info['id']}/matches?status=SCHEDULED"
            response = requests.get(upcoming_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                
                for match in matches:
                    # Only include matches from 2025/26 season onwards
                    match_date = datetime.fromisoformat(match['utcDate'].replace('Z', '+00:00'))
                    
                    # Check if match is in 2025/26 season or later (after July 2025)
                    if match_date >= datetime(2025, 7, 1):
                        all_upcoming_matches.append({
                            'competition': comp_info['name'],
                            'competition_code': comp_code,
                            'country': comp_info['country'],
                            'match_id': match['id'],
                            'date': match['utcDate'],
                            'matchday': match.get('matchday'),
                            'home_team': match['homeTeam']['name'],
                            'away_team': match['awayTeam']['name'],
                            'status': match['status'],
                            'season': '2025/26'
                        })
                
                print(f"  Found {len([m for m in all_upcoming_matches if m['competition_code'] == comp_code])} upcoming matches")
            
            # Also fetch recent FINISHED matches for statistics (last 100 matches)
            finished_url = f"https://api.football-data.org/v4/competitions/{comp_info['id']}/matches?status=FINISHED&limit=100"
            response = requests.get(finished_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                
                for match in matches:
                    if match['score']['fullTime']['home'] is not None:
                        all_historical_matches.append({
                            'competition': comp_info['name'],
                            'competition_code': comp_code,
                            'date': match['utcDate'],
                            'home_team': match['homeTeam']['name'],
                            'away_team': match['awayTeam']['name'],
                            'home_goals': match['score']['fullTime']['home'],
                            'away_goals': match['score']['fullTime']['away']
                        })
                
                print(f"  Found {len([m for m in all_historical_matches if m['competition_code'] == comp_code])} historical matches")
                
        except Exception as e:
            print(f"  Error fetching {comp_info['name']}: {e}")
            continue
    
    # Save upcoming matches
    if all_upcoming_matches:
        with open('data/upcoming_matches.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['competition', 'competition_code', 'country', 
                                                   'match_id', 'date', 'matchday', 
                                                   'home_team', 'away_team', 'status', 'season'])
            writer.writeheader()
            writer.writerows(all_upcoming_matches)
        print(f"\nTotal upcoming matches (2025/26+): {len(all_upcoming_matches)}")
    
    # Save historical matches for statistics
    if all_historical_matches:
        with open('data/historical_matches.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['competition', 'competition_code', 'date',
                                                   'home_team', 'away_team', 'home_goals', 'away_goals'])
            writer.writeheader()
            writer.writerows(all_historical_matches)
        print(f"Total historical matches: {len(all_historical_matches)}")
    
    return all_upcoming_matches

if __name__ == '__main__':
    fetch_all_upcoming_matches()
