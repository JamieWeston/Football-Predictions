import json
import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict
import random

def load_matches():
    """Load historical matches"""
    matches = []
    csv_path = os.path.join('data', 'matches.csv')
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                matches.append(row)
        print(f"Loaded {len(matches)} matches from {csv_path}")
    except Exception as e:
        print(f"Error loading matches: {e}")
        print("Using empty match list")
    
    return matches

def calculate_team_stats(matches):
    """Calculate basic team statistics"""
    stats = defaultdict(lambda: {
        'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
        'goals_for': 0, 'goals_against': 0, 'points': 0,
        'home_wins': 0, 'home_games': 0,
        'away_wins': 0, 'away_games': 0
    })
    
    for match in matches:
        try:
            home = match['home_team']
            away = match['away_team']
            home_goals = int(match['home_goals'])
            away_goals = int(match['away_goals'])
            
            # Update home team
            stats[home]['played'] += 1
            stats[home]['home_games'] += 1
            stats[home]['goals_for'] += home_goals
            stats[home]['goals_against'] += away_goals
            
            # Update away team
            stats[away]['played'] += 1
            stats[away]['away_games'] += 1
            stats[away]['goals_for'] += away_goals
            stats[away]['goals_against'] += home_goals
            
            # Results
            if home_goals > away_goals:
                stats[home]['won'] += 1
                stats[home]['home_wins'] += 1
                stats[home]['points'] += 3
                stats[away]['lost'] += 1
            elif home_goals < away_goals:
                stats[away]['won'] += 1
                stats[away]['away_wins'] += 1
                stats[away]['points'] += 3
                stats[home]['lost'] += 1
            else:
                stats[home]['drawn'] += 1
                stats[away]['drawn'] += 1
                stats[home]['points'] += 1
                stats[away]['points'] += 1
        except (KeyError, ValueError) as e:
            print(f"Skipping match due to error: {e}")
            continue
    
    return stats

def predict_match(home_team, away_team, stats):
    """Simple prediction based on form and stats"""
    
    # Get team statistics
    home_stats = stats.get(home_team, stats['default'])
    away_stats = stats.get(away_team, stats['default'])
    
    # Base probabilities (Premier League averages)
    home_prob = 0.46
    draw_prob = 0.27
    away_prob = 0.27
    
    # Adjust based on home record
    if home_stats['home_games'] > 0:
        home_form = home_stats['home_wins'] / home_stats['home_games']
        home_prob = 0.3 + (home_form * 0.4)
    
    # Adjust based on away record
    if away_stats['away_games'] > 0:
        away_form = away_stats['away_wins'] / away_stats['away_games']
        away_prob = 0.2 + (away_form * 0.3)
    
    # Adjust based on overall strength
    if home_stats['played'] > 0 and away_stats['played'] > 0:
        home_strength = home_stats['points'] / (home_stats['played'] * 3)
        away_strength = away_stats['points'] / (away_stats['played'] * 3)
        
        strength_diff = home_strength - away_strength
        home_prob += strength_diff * 0.2
        away_prob -= strength_diff * 0.2
    
    # Ensure probabilities are valid
    home_prob = max(0.10, min(0.75, home_prob))
    away_prob = max(0.10, min(0.75, away_prob))
    
    # Adjust draw probability
    draw_prob = 1.0 - home_prob - away_prob
    draw_prob = max(0.15, min(0.35, draw_prob))
    
    # Normalize
    total = home_prob + draw_prob + away_prob
    if total > 0:
        home_prob /= total
        draw_prob /= total
        away_prob /= total
    
    # Calculate other markets
    avg_goals = 2.7  # Premier League average
    if home_stats['played'] > 0 and away_stats['played'] > 0:
        home_avg = home_stats['goals_for'] / home_stats['played']
        away_avg = away_stats['goals_for'] / away_stats['played']
        avg_goals = (home_avg + away_avg) * 0.9  # Slight under adjustment
    
    over_25 = 0.55 if avg_goals > 2.5 else 0.45
    btts = 0.52  # Default Premier League average
    
    return {
        'home': round(home_prob, 3),
        'draw': round(draw_prob, 3),
        'away': round(away_prob, 3),
        'over_25': round(over_25, 3),
        'btts': round(btts, 3),
        'avg_goals': round(avg_goals, 2)
    }

def generate_upcoming_fixtures():
    """Generate next week's fixtures"""
    
    teams = [
        'Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton & Hove Albion',
        'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Ipswich Town',
        'Leicester City', 'Liverpool', 'Manchester City', 'Manchester United',
        'Newcastle United', 'Nottingham Forest', 'Southampton', 'Tottenham Hotspur',
        'West Ham United', 'Wolverhampton Wanderers'
    ]
    
    # Create realistic fixtures
    fixtures = [
        {'home': 'Arsenal', 'away': 'Manchester United'},
        {'home': 'Liverpool', 'away': 'Chelsea'},
        {'home': 'Manchester City', 'away': 'Tottenham Hotspur'},
        {'home': 'Newcastle United', 'away': 'Aston Villa'},
        {'home': 'Brighton & Hove Albion', 'away': 'Fulham'},
        {'home': 'Brentford', 'away': 'Wolverhampton Wanderers'},
        {'home': 'Crystal Palace', 'away': 'Southampton'},
        {'home': 'Everton', 'away': 'Nottingham Forest'},
        {'home': 'West Ham United', 'away': 'Leicester City'},
        {'home': 'Bournemouth', 'away': 'Ipswich Town'},
    ]
    
    # Add dates
    result = []
    for i, fixture in enumerate(fixtures):
        match_date = datetime.now() + timedelta(days=(i % 4) + 1, hours=i*2)
        result.append({
            'date': match_date.isoformat(),
            'home_team': fixture['home'],
            'away_team': fixture['away']
        })
    
    return result

def main():
    """Main prediction function"""
    
    print("Starting prediction generation...")
    
    # Load historical data
    matches = load_matches()
    
    # Calculate team statistics
    stats = calculate_team_stats(matches)
    print(f"Calculated stats for {len(stats)} teams")
    
    # Add default stats for new teams
    stats['default'] = {
        'played': 10, 'won': 3, 'drawn': 3, 'lost': 4,
        'goals_for': 12, 'goals_against': 13, 'points': 12,
        'home_wins': 2, 'home_games': 5,
        'away_wins': 1, 'away_games': 5
    }
    
    # Get upcoming fixtures
    fixtures = generate_upcoming_fixtures()
    print(f"Generated {len(fixtures)} fixtures")
    
    # Generate predictions
    predictions = []
    
    for fixture in fixtures:
        probs = predict_match(
            fixture['home_team'],
            fixture['away_team'],
            stats
        )
        
        prediction = {
            'match_id': f"{fixture['home_team'][:3].upper()}_{fixture['away_team'][:3].upper()}_{datetime.now().strftime('%Y%m%d')}",
            'date': fixture['date'],
            'home_team': fixture['home_team'],
            'away_team': fixture['away_team'],
            'probabilities': probs,
            'confidence': 'medium',
            'last_updated': datetime.now().isoformat()
        }
        
        predictions.append(prediction)
    
    # Save predictions
    output = {
        'generated': datetime.now().isoformat(),
        'league': 'Premier League',
        'season': '2024/25',
        'predictions': predictions,
        'metadata': {
            'model_version': '1.0',
            'matches_analyzed': len(matches),
            'teams_tracked': len(stats) - 1  # Exclude 'default'
        }
    }
    
    # Save to file
    output_path = 'predictions.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Generated {len(predictions)} predictions")
    print(f"Saved to {output_path}")
    
    # Print sample prediction for verification
    if predictions:
        sample = predictions[0]
        print(f"\nSample prediction:")
        print(f"  {sample['home_team']} vs {sample['away_team']}")
        print(f"  Home: {sample['probabilities']['home']:.1%}")
        print(f"  Draw: {sample['probabilities']['draw']:.1%}")
        print(f"  Away: {sample['probabilities']['away']:.1%}")

if __name__ == '__main__':
    main()
