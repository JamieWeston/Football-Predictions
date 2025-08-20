import os
import json
import csv
from datetime import datetime, timedelta

# Get API key from environment (optional)
API_KEY = os.environ.get('API_KEY', '')

def fetch_premier_league_data():
    """Fetch Premier League data from API"""
    
    # For now, always use sample data to ensure it works
    print("Creating sample data for predictions")
    create_sample_data()
    return

def create_sample_data():
    """Create sample data for testing"""
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Sample match data for predictions
    sample_matches = [
        ['2024-08-01', 'Arsenal', 'Chelsea', '2', '1', 'FINISHED'],
        ['2024-08-02', 'Liverpool', 'Manchester United', '3', '2', 'FINISHED'],
        ['2024-08-03', 'Manchester City', 'Tottenham Hotspur', '4', '1', 'FINISHED'],
        ['2024-08-04', 'Fulham', 'Brentford', '1', '1', 'FINISHED'],
        ['2024-08-05', 'Newcastle United', 'Brighton & Hove Albion', '2', '0', 'FINISHED'],
        ['2024-08-06', 'West Ham United', 'Aston Villa', '1', '2', 'FINISHED'],
        ['2024-08-07', 'Wolverhampton Wanderers', 'Southampton', '2', '1', 'FINISHED'],
        ['2024-08-08', 'Crystal Palace', 'Nottingham Forest', '0', '0', 'FINISHED'],
        ['2024-08-09', 'Everton', 'Leicester City', '1', '1', 'FINISHED'],
        ['2024-08-10', 'Bournemouth', 'Ipswich Town', '3', '0', 'FINISHED'],
        ['2024-08-11', 'Chelsea', 'Manchester City', '0', '2', 'FINISHED'],
        ['2024-08-12', 'Manchester United', 'Arsenal', '1', '3', 'FINISHED'],
        ['2024-08-13', 'Tottenham Hotspur', 'Liverpool', '2', '2', 'FINISHED'],
        ['2024-08-14', 'Brentford', 'Newcastle United', '1', '3', 'FINISHED'],
        ['2024-08-15', 'Brighton & Hove Albion', 'Fulham', '2', '1', 'FINISHED'],
    ]
    
    # Write to CSV file
    csv_path = os.path.join('data', 'matches.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'home_team', 'away_team', 'home_goals', 'away_goals', 'status'])
        writer.writerows(sample_matches)
    
    print(f"Sample data created successfully at {csv_path}")
    print(f"Created {len(sample_matches)} sample matches")

if __name__ == '__main__':
    fetch_premier_league_data()
