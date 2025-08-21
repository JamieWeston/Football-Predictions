import json
import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict
import sys

# Import the advanced predictor
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from advanced_predictor import RollingFormPredictor

def load_upcoming_matches():
    """Load only future matches"""
    matches = []
    today = datetime.now()
    
    try:
        with open('data/upcoming_matches.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse match date
                match_date = datetime.fromisoformat(row['date'].replace('Z', '+00:00'))
                
                # Only include if match is in the future
                if match_date >= today:
                    matches.append(row)
        
        print(f"✅ Loaded {len(matches)} upcoming matches")
        
        # Sort by date
        matches.sort(key=lambda x: x['date'])
        
    except Exception as e:
        print(f"❌ Error loading upcoming matches: {e}")
    
    return matches

def load_recent_results():
    """Load recent match results for form calculation"""
    results = []
    
    # Try to load recent results with xG
    if os.path.exists('data/recent_results.csv'):
        try:
            with open('data/recent_results.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row['home_goals'] = int(row.get('home_goals', 0))
                    row['away_goals'] = int(row.get('away_goals', 0))
                    if row.get('home_xg'):
                        row['home_xg'] = float(row['home_xg'])
                    if row.get('away_xg'):
                        row['away_xg'] = float(row['away_xg'])
                    results.append(row)
            print(f"✅ Loaded {len(results)} recent results")
        except Exception as e:
            print(f"⚠️ Error loading recent results: {e}")
    
    # Also load historical data if available
    if os.path.exists('data/matches.csv'):
        try:
            with open('data/matches.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    results.append({
                        'competition_code': 'PL',
                        'date': row['date'],
                        'home_team': row['home_team'],
                        'away_team': row['away_team'],
                        'home_goals': int(row['home_goals']),
                        'away_goals': int(row['away_goals']),
                        'home_xg': None,
                        'away_xg': None
                    })
            print(f"✅ Added historical data for long-term stats")
        except Exception as e:
            print(f"⚠️ Error loading historical data: {e}")
    
    return results

def get_team_recent_matches(results, team, max_matches=10):
    """Get recent matches for a team with calculated metrics"""
    team_matches = []
    
    for match in sorted(results, key=lambda x: x['date'], reverse=True):
        if len(team_matches) >= max_matches:
            break
            
        if match['home_team'] == team:
            team_matches.append({
                'date': match['date'],
                'opponent': match['away_team'],
                'venue': 'H',
                'goals_for': match['home_goals'],
                'goals_against': match['away_goals'],
                'xg_for': match.get('home_xg'),
                'xg_against': match.get('away_xg'),
                'result': 'W' if match['home_goals'] > match['away_goals'] else 
                         ('D' if match['home_goals'] == match['away_goals'] else 'L')
            })
        elif match['away_team'] == team:
            team_matches.append({
                'date': match['date'],
                'opponent': match['home_team'],
                'venue': 'A',
                'goals_for': match['away_goals'],
                'goals_against': match['home_goals'],
                'xg_for': match.get('away_xg'),
                'xg_against': match.get('home_xg'),
                'result': 'W' if match['away_goals'] > match['home_goals'] else 
                         ('D' if match['away_goals'] == match['home_goals'] else 'L')
            })
    
    return team_matches

def calculate_league_stats(results, competition_code='PL'):
    """Calculate current league statistics"""
    comp_matches = [m for m in results if m.get('competition_code') == competition_code]
    
    if not comp_matches:
        # Default stats
        return {
            'avg_goals_per_team': 1.35,
            'avg_goals_per_match': 2.70,
            'home_win_rate': 0.46,
            'away_win_rate': 0.28,
            'draw_rate': 0.26,
            'over_25_rate': 0.52,
            'btts_rate': 0.50
        }
    
    # Calculate from recent matches (last 100)
    recent = comp_matches[-100:] if len(comp_matches) > 100 else comp_matches
    
    total = len(recent)
    home_wins = sum(1 for m in recent if m['home_goals'] > m['away_goals'])
    away_wins = sum(1 for m in recent if m['away_goals'] > m['home_goals'])
    draws = total - home_wins - away_wins
    
    total_goals = sum(m['home_goals'] + m['away_goals'] for m in recent)
    over_25 = sum(1 for m in recent if m['home_goals'] + m['away_goals'] > 2.5)
    btts = sum(1 for m in recent if m['home_goals'] > 0 and m['away_goals'] > 0)
    
    return {
        'avg_goals_per_team': total_goals / (total * 2) if total > 0 else 1.35,
        'avg_goals_per_match': total_goals / total if total > 0 else 2.70,
        'home_win_rate': home_wins / total if total > 0 else 0.46,
        'away_win_rate': away_wins / total if total > 0 else 0.28,
        'draw_rate': draws / total if total > 0 else 0.26,
        'over_25_rate': over_25 / total if total > 0 else 0.52,
        'btts_rate': btts / total if total > 0 else 0.50
    }

def main():
    """Main prediction function"""
    
    print("\n" + "=" * 60)
    print("GENERATING PREDICTIONS WITH ROLLING UPDATES")
    print(f"Current date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # Load data
    upcoming_matches = load_upcoming_matches()
    recent_results = load_recent_results()
    
    if not upcoming_matches:
        print("❌ No upcoming matches found!")
        return
    
    # Initialize predictor
    predictor = RollingFormPredictor()
    
    # Update ELO ratings with recent results
    predictor.update_elo_ratings(recent_results)
    
    # Generate predictions
    predictions = []
    
    for match in upcoming_matches:
        # Get team recent matches
        home_matches = get_team_recent_matches(recent_results, match['home_team'])
        away_matches = get_team_recent_matches(recent_results, match['away_team'])
        
        # Calculate league stats
        league_stats = calculate_league_stats(recent_results, match.get('competition_code', 'PL'))
        
        # Generate prediction
        prediction = predictor.predict_match(
            match['home_team'],
            match['away_team'],
            home_matches,
            away_matches,
            match['date'],
            league_stats
        )
        
        # Determine confidence based on data availability
        confidence = 'high' if (len(home_matches) >= 5 and len(away_matches) >= 5) else \
                    ('medium' if (len(home_matches) >= 3 and len(away_matches) >= 3) else 'low')
        
        # Build prediction object
        pred_obj = {
            'match_id': match['match_id'],
            'date': match['date'],
            'competition': match['competition'],
            'home_team': match['home_team'],
            'away_team': match['away_team'],
            'probabilities': {
                'home': prediction['home'],
                'draw': prediction['draw'],
                'away': prediction['away'],
                'over_25': prediction['over_25'],
                'btts': prediction['btts']
            },
            'confidence': confidence,
            'metrics': {
                'expected_goals': prediction['expected_goals'],
                'home_form': prediction['home_form'],
                'away_form': prediction['away_form'],
                'home_elo': prediction['home_elo'],
                'away_elo': prediction['away_elo']
            }
        }
        
        predictions.append(pred_obj)
    
    # Sort predictions by date
    predictions.sort(key=lambda x: x['date'])
    
    # Create output JSON
    output = {
        'generated': datetime.now().isoformat(),
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'predictions_count': len(predictions),
        'date_range': {
            'from': datetime.now().strftime('%Y-%m-%d'),
            'to': (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
        },
        'predictions': predictions,
        'model_info': {
            'version': '4.0-Rolling',
            'features': [
                'Rolling form with exponential decay',
                'xG (expected goals) integration',
                'Dynamic ELO ratings',
                'Time-weighted recent performance',
                'League-specific calibration'
            ],
            'update_frequency': 'Daily',
            'prediction_window': '14 days'
        }
    }
    
    # Save to file
    with open('predictions.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Generated {len(predictions)} predictions")
    print(f"📅 Date range: {output['date_range']['from']} to {output['date_range']['to']}")
    
    # Print summary by competition
    comp_counts = defaultdict(int)
    for pred in predictions:
        comp_counts[pred['competition']] += 1
    
    print("\n📊 Predictions by competition:")
    for comp, count in comp_counts.items():
        print(f"  - {comp}: {count} matches")
    
    print(f"\n💾 Saved to predictions.json")
    print("=" * 60)

if __name__ == '__main__':
    main()
