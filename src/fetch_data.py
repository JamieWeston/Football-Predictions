import os
import json
import requests
import csv
from datetime import datetime, timedelta

# Get API key from environment
API_KEY = os.environ.get('API_KEY', '')

def fetch_premier_league_data():
    """Fetch Premier League data from API"""
    
    # If no API key, use fallback data
    if not API_KEY:
        print("No API key found, using sample data")
        create_sample_data()
        return
    
    headers = {'X-Auth-Token': API_KEY}
    
    # Fetch recent matches
    url = "https://api.football-data.org/v4/competitions/2021/matches"
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # Save matches to CSV
        save_matches_to_csv(data.get('matches', []))
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        create_sample_data()

def save_matches_to_csv(matches):
    """Save matches to CSV file"""
    
    os.makedirs('data', exist_ok=True)
    
    with open('data/matches.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'home_team', 'away_team', 'home_goals', 'away_goals', 'status'])
        
        for match in matches:
            if match['status'] == 'FINISHED':
                writer.writerow([
                    match['utcDate'],
                    match['homeTeam']['name'],
                    match['awayTeam']['name'],
                    match['score']['fullTime']['home'],
                    match['score']['fullTime']['away'],
                    match['status']
                ])

def create_sample_data():
    """Create sample data for testing"""
    
    os.makedirs('data', exist_ok=True)
    
    sample_matches = [
        ['2024-08-01', 'Arsenal', 'Chelsea', 2, 1, 'FINISHED'],
        ['2024-08-02', 'Liverpool', 'Manchester United', 3, 2, 'FINISHED'],
        ['2024-08-03', 'Manchester City', 'Tottenham', 4, 1, 'FINISHED'],
        ['2024-08-04', 'Fulham', 'Brentford', 1, 1, 'FINISHED'],
        ['2024-08-05', 'Newcastle', 'Brighton', 2, 0, 'FINISHED'],
    ]
    
    with open('data/matches.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'home_team', 'away_team', 'home_goals', 'away_goals', 'status'])
        writer.writerows(sample_matches)

if __name__ == '__main__':
    fetch_premier_league_data()
