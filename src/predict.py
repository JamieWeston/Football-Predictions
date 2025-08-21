import json
import csv
import os
from datetime import datetime
from collections import defaultdict

def load_upcoming_matches():
    """Load upcoming matches from CSV"""
    matches = []
    try:
        with open('data/upcoming_matches.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                matches.append(row)
        print(f"Loaded {len(matches)} upcoming matches")
    except Exception as e:
        print(f"Error loading upcoming matches: {e}")
    return matches

def load_historical_matches():
    """Load historical matches for statistics"""
    matches = []
    try:
        with open('data/historical_matches.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                matches.append(row)
        print(f"Loaded {len(matches)} historical matches")
    except Exception as e:
        print(f"Error loading historical matches: {e}")
    return matches

def calculate_team_stats(historical_matches, competition_code=None):
    """Calculate team statistics from historical matches"""
    stats = defaultdict(lambda: {
        'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
        'goals_for': 0, 'goals_against': 0, 'points': 0,
        'home_wins': 0, 'home_games': 0,
        'away_wins': 0, 'away_games': 0,
        'recent_form': []  # Last 5 matches
    })
    
    # Filter by competition if specified
    if competition_code:
        historical_matches = [m for m in historical_matches if m.get('competition_code') == competition_code]
    
    for match in historical_matches:
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
                stats[home]['recent_form'].append('W')
                stats[away]['recent_form'].append('L')
            elif home_goals < away_goals:
                stats[away]['won'] += 1
                stats[away]['away_wins'] += 1
                stats[away]['points'] += 3
                stats[home]['lost'] += 1
                stats[home]['recent_form'].append('L')
                stats[away]['recent_form'].append('W')
            else:
                stats[home]['drawn'] += 1
                stats[away]['drawn'] += 1
                stats[home]['points'] += 1
                stats[away]['points'] += 1
                stats[home]['recent_form'].append('D')
                stats[away]['recent_form'].append('D')
                
            # Keep only last 5 for form
            stats[home]['recent_form'] = stats[home]['recent_form'][-5:]
            stats[away]['recent_form'] = stats[away]['recent_form'][-5:]
            
        except (KeyError, ValueError) as e:
            continue
    
    return stats

def predict_match(home_team, away_team, stats, league_averages):
    """Calculate match probabilities based on statistics"""
    
    # Get team statistics
    home_stats = stats.get(home_team, None)
    away_stats = stats.get(away_team, None)
    
    # Use league averages as base
    home_prob = league_averages['home_win_rate']
    draw_prob = league_averages['draw_rate']
    away_prob = league_averages['away_win_rate']
    
    # If we have stats for both teams, calculate based on form
    if home_stats and away_stats and home_stats['played'] > 0 and away_stats['played'] > 0:
        
        # Home team strength
        if home_stats['home_games'] > 0:
            home_home_rate = home_stats['home_wins'] / home_stats['home_games']
            home_prob = 0.4 * league_averages['home_win_rate'] + 0.6 * home_home_rate
        
        # Away team strength
        if away_stats['away_games'] > 0:
            away_away_rate = away_stats['away_wins'] / away_stats['away_games']
            away_prob = 0.4 * league_averages['away_win_rate'] + 0.6 * away_away_rate
        
        # Overall strength difference
        home_ppg = home_stats['points'] / home_stats['played']
        away_ppg = away_stats['points'] / away_stats['played']
        strength_diff = (home_ppg - away_ppg) / 3.0  # Normalize to 0-1 range
        
        # Adjust probabilities based on strength
        home_prob += strength_diff * 0.15
        away_prob -= strength_diff * 0.15
        
        # Recent form adjustment
        if home_stats['recent_form']:
            home_form_score = home_stats['recent_form'].count('W') * 3 + home_stats['recent_form'].count('D')
            home_form_rate = home_form_score / (len(home_stats['recent_form']) * 3)
            home_prob = 0.7 * home_prob + 0.3 * home_form_rate
        
        if away_stats['recent_form']:
            away_form_score = away_stats['recent_form'].count('W') * 3 + away_stats['recent_form'].count('D')
            away_form_rate = away_form_score / (len(away_stats['recent_form']) * 3)
            away_prob = 0.7 * away_prob + 0.3 * away_form_rate
    
    # Ensure valid probabilities
    home_prob = max(0.05, min(0.85, home_prob))
    away_prob = max(0.05, min(0.85, away_prob))
    draw_prob = 1.0 - home_prob - away_prob
    draw_prob = max(0.10, min(0.40, draw_prob))
    
    # Normalize
    total = home_prob + draw_prob + away_prob
    home_prob /= total
    draw_prob /= total
    away_prob /= total
    
    # Calculate goal-based markets
    if home_stats and away_stats and home_stats['played'] > 0 and away_stats['played'] > 0:
        home_goals_avg = home_stats['goals_for'] / home_stats['played']
        away_goals_avg = away_stats['goals_for'] / away_stats['played']
        total_goals_avg = home_goals_avg + away_goals_avg
        
        over_25 = 0.65 if total_goals_avg > 2.8 else (0.50 if total_goals_avg > 2.3 else 0.35)
        btts = 0.60 if (home_goals_avg > 1.0 and away_goals_avg > 1.0) else 0.40
    else:
        over_25 = league_averages['over_25_rate']
        btts = league_averages['btts_rate']
    
    return {
        'home': round(home_prob, 3),
        'draw': round(draw_prob, 3),
        'away': round(away_prob, 3),
        'over_25': round(over_25, 3),
        'btts': round(btts, 3)
    }

def get_league_averages(competition_code):
    """Get typical averages for each league"""
    # Based on historical data
    league_defaults = {
        'PL': {'home_win_rate': 0.46, 'draw_rate': 0.25, 'away_win_rate': 0.29, 'over_25_rate': 0.55, 'btts_rate': 0.53},
        'BL1': {'home_win_rate': 0.45, 'draw_rate': 0.24, 'away_win_rate': 0.31, 'over_25_rate': 0.58, 'btts_rate': 0.56},
        'SA': {'home_win_rate': 0.48, 'draw_rate': 0.26, 'away_win_rate': 0.26, 'over_25_rate': 0.52, 'btts_rate': 0.50},
        'PD': {'home_win_rate': 0.47, 'draw_rate': 0.25, 'away_win_rate': 0.28, 'over_25_rate': 0.51, 'btts_rate': 0.49},
        'FL1': {'home_win_rate': 0.46, 'draw_rate': 0.27, 'away_win_rate': 0.27, 'over_25_rate': 0.48, 'btts_rate': 0.47},
        'DED': {'home_win_rate': 0.45, 'draw_rate': 0.23, 'away_win_rate': 0.32, 'over_25_rate': 0.62, 'btts_rate': 0.58},
        'PPL': {'home_win_rate': 0.48, 'draw_rate': 0.26, 'away_win_rate': 0.26, 'over_25_rate': 0.49, 'btts_rate': 0.46},
        'ELC': {'home_win_rate': 0.45, 'draw_rate': 0.27, 'away_win_rate': 0.28, 'over_25_rate': 0.53, 'btts_rate': 0.51},
        'BSA': {'home_win_rate': 0.49, 'draw_rate': 0.27, 'away_win_rate': 0.24, 'over_25_rate': 0.50, 'btts_rate': 0.48},
        'DEFAULT': {'home_win_rate': 0.46, 'draw_rate': 0.26, 'away_win_rate': 0.28, 'over_25_rate': 0.52, 'btts_rate': 0.50}
    }
    
    return league_defaults.get(competition_code, league_defaults['DEFAULT'])

def main():
    """Main prediction function"""
    
    print("Starting prediction generation for 2025/26 season...")
    
    # Load data
    upcoming_matches = load_upcoming_matches()
    historical_matches = load_historical_matches()
    
    if not upcoming_matches:
        print("No upcoming matches found!")
        return
    
    # Group predictions by competition
    predictions_by_league = defaultdict(list)
    
    # Process each competition
    competitions_processed = set()
    
    for match in upcoming_matches:
        comp_code = match['competition_code']
        competitions_processed.add(comp_code)
        
        # Calculate stats for this competition
        stats = calculate_team_stats(historical_matches, comp_code)
        
        # Get league averages
        league_averages = get_league_averages(comp_code)
        
        # Generate prediction
        probs = predict_match(
            match['home_team'],
            match['away_team'],
            stats,
            league_averages
        )
        
        prediction = {
            'match_id': match['match_id'],
            'date': match['date'],
            'matchday': match.get('matchday'),
            'home_team': match['home_team'],
            'away_team': match['away_team'],
            'probabilities': probs,
            'competition': match['competition'],
            'country': match['country'],
            'season': match['season']
        }
        
        predictions_by_league[comp_code].append(prediction)
    
    # Create output
    all_predictions = []
    for comp_code, preds in predictions_by_league.items():
        all_predictions.extend(preds)
    
    # Sort by date
    all_predictions.sort(key=lambda x: x['date'])
    
    # Save predictions
    output = {
        'generated': datetime.now().isoformat(),
        'season': '2025/26',
        'total_matches': len(all_predictions),
        'competitions': list(competitions_processed),
        'predictions': all_predictions,
        'metadata': {
            'model_version': '2.0',
            'historical_matches_analyzed': len(historical_matches),
            'leagues_covered': len(competitions_processed)
        }
    }
    
    # Save to file
    with open('predictions.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nGenerated predictions for {len(all_predictions)} matches")
    print(f"Leagues covered: {', '.join(competitions_processed)}")
    print("Saved to predictions.json")
    
    # Print summary
    for comp_code, preds in predictions_by_league.items():
        if preds:
            print(f"\n{preds[0]['competition']}: {len(preds)} matches")

if __name__ == '__main__':
    main()
