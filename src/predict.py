import json
import csv
import os
import math
from datetime import datetime, timedelta
from collections import defaultdict

class RollingFormPredictor:
    """Advanced predictor with rolling form and ELO"""
    
    def __init__(self):
        self.elo_ratings = {}
        self.k_factor = 32
        self.home_advantage = 65
        self.initial_elo = 1500
        
    def calculate_time_weighted_form(self, recent_matches, decay_rate=0.9):
        """Calculate form with exponential decay for recency"""
        if not recent_matches:
            return 0.5
        
        total_weight = 0
        weighted_points = 0
        
        for i, match in enumerate(recent_matches[:10]):
            weight = decay_rate ** i
            
            if match['result'] == 'W':
                points = 3
            elif match['result'] == 'D':
                points = 1
            else:
                points = 0
            
            weighted_points += points * weight
            total_weight += weight * 3
        
        return weighted_points / total_weight if total_weight > 0 else 0.5
    
    def update_elo_ratings(self, matches):
        """Update ELO ratings based on recent matches"""
        elo = defaultdict(lambda: self.initial_elo)
        
        for match in sorted(matches, key=lambda x: x.get('date', '')):
            try:
                home = match['home_team']
                away = match['away_team']
                home_goals = int(match.get('home_goals', 0))
                away_goals = int(match.get('away_goals', 0))
                
                # Expected scores
                home_expected = 1 / (1 + 10**((elo[away] - elo[home] - self.home_advantage) / 400))
                away_expected = 1 - home_expected
                
                # Actual scores
                if home_goals > away_goals:
                    home_actual, away_actual = 1, 0
                elif away_goals > home_goals:
                    home_actual, away_actual = 0, 1
                else:
                    home_actual, away_actual = 0.5, 0.5
                
                # Update ELO
                elo[home] += self.k_factor * (home_actual - home_expected)
                elo[away] += self.k_factor * (away_actual - away_expected)
                
            except (KeyError, ValueError):
                continue
        
        self.elo_ratings = dict(elo)
        return self.elo_ratings
    
    def poisson_pmf(self, k, lambda_val):
        """Poisson probability mass function"""
        try:
            return (lambda_val ** k) * math.exp(-lambda_val) / math.factorial(min(k, 20))
        except:
            return 0
    
    def calculate_poisson_probs(self, home_lambda, away_lambda):
        """Calculate match outcome probabilities using Poisson"""
        home_win = 0
        draw = 0
        away_win = 0
        
        for h in range(7):
            for a in range(7):
                prob = self.poisson_pmf(h, home_lambda) * self.poisson_pmf(a, away_lambda)
                if h > a:
                    home_win += prob
                elif h == a:
                    draw += prob
                else:
                    away_win += prob
        
        return {'home': home_win, 'draw': draw, 'away': away_win}
    
    def predict_match(self, home_team, away_team, home_matches, away_matches, league_stats):
        """Generate prediction with all factors"""
        
        # 1. Calculate rolling form
        home_form = self.calculate_time_weighted_form(home_matches)
        away_form = self.calculate_time_weighted_form(away_matches)
        
        # 2. Get ELO ratings
        home_elo = self.elo_ratings.get(home_team, self.initial_elo)
        away_elo = self.elo_ratings.get(away_team, self.initial_elo)
        
        # 3. Calculate base probabilities from ELO
        elo_diff = home_elo - away_elo + self.home_advantage
        home_win_elo = 1 / (1 + 10**(-elo_diff / 400))
        away_win_elo = 1 / (1 + 10**(elo_diff / 400))
        
        # 4. Calculate expected goals
        league_avg = league_stats.get('avg_goals_per_team', 1.35)
        
        # Base expected goals on form and recent scoring
        home_recent_goals = sum(m['goals_for'] for m in home_matches[:5]) / 5 if len(home_matches) >= 5 else league_avg
        away_recent_goals = sum(m['goals_for'] for m in away_matches[:5]) / 5 if len(away_matches) >= 5 else league_avg
        
        home_expected = home_recent_goals * 1.1  # Home advantage
        away_expected = away_recent_goals * 0.9
        
        # 5. Calculate Poisson probabilities
        poisson_probs = self.calculate_poisson_probs(home_expected, away_expected)
        
        # 6. Combine all factors
        home_prob = (0.35 * home_win_elo + 
                    0.35 * poisson_probs['home'] + 
                    0.30 * (home_form * 0.6 + (1 - away_form) * 0.4))
        
        away_prob = (0.35 * away_win_elo + 
                    0.35 * poisson_probs['away'] + 
                    0.30 * (away_form * 0.6 + (1 - home_form) * 0.4))
        
        # Draw probability
        draw_prob = 1 - home_prob - away_prob
        draw_prob = max(0.15, min(0.35, draw_prob + poisson_probs['draw'] * 0.3))
        
        # Normalize
        total = home_prob + draw_prob + away_prob
        if total > 0:
            home_prob /= total
            draw_prob /= total
            away_prob /= total
        
        # 7. Calculate other markets
        total_expected = home_expected + away_expected
        over_25 = 0.55 if total_expected > 2.5 else 0.45
        btts = 0.52 if (home_expected > 0.8 and away_expected > 0.8) else 0.40
        
        return {
            'home': round(home_prob, 3),
            'draw': round(draw_prob, 3),
            'away': round(away_prob, 3),
            'over_25': round(over_25, 3),
            'btts': round(btts, 3),
            'expected_goals': round(total_expected, 2),
            'home_form': round(home_form, 2),
            'away_form': round(away_form, 2),
            'home_elo': round(home_elo),
            'away_elo': round(away_elo)
        }

def load_upcoming_matches():
    """Load only future matches"""
    matches = []
    today = datetime.now()
    
    print("\n📅 Loading upcoming matches...")
    
    try:
        with open('data/upcoming_matches.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Parse match date
                    date_str = row['date'].replace('Z', '+00:00')
                    match_date = datetime.fromisoformat(date_str)
                    
                    # Only include if match is in the future
                    if match_date >= today:
                        matches.append(row)
                except:
                    # If date parsing fails, include the match anyway
                    matches.append(row)
        
        print(f"✅ Loaded {len(matches)} upcoming matches")
        
        # Sort by date
        matches.sort(key=lambda x: x.get('date', ''))
        
    except Exception as e:
        print(f"❌ Error loading upcoming matches: {e}")
        
        # Create sample data if file doesn't exist
        print("Creating sample upcoming matches...")
        teams = [
            ('Arsenal', 'Chelsea'),
            ('Liverpool', 'Manchester United'),
            ('Manchester City', 'Tottenham Hotspur'),
            ('Real Madrid', 'Barcelona'),
            ('Bayern Munich', 'Borussia Dortmund')
        ]
        
        for i, (home, away) in enumerate(teams):
            match_date = today + timedelta(days=(i % 7) + 1)
            matches.append({
                'competition': 'Premier League' if i < 3 else 'Various',
                'competition_code': 'PL',
                'match_id': f'sample_{i+1}',
                'date': match_date.isoformat() + 'Z',
                'home_team': home,
                'away_team': away,
                'status': 'SCHEDULED'
            })
    
    return matches

def load_all_historical_data():
    """Load all available historical data"""
    all_results = []
    
    # Try to load recent_results.csv
    if os.path.exists('data/recent_results.csv'):
        print("📊 Loading recent results...")
        try:
            with open('data/recent_results.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        row['home_goals'] = int(row.get('home_goals', 0))
                        row['away_goals'] = int(row.get('away_goals', 0))
                        all_results.append(row)
                    except:
                        continue
            print(f"  Loaded {len(all_results)} recent results")
        except Exception as e:
            print(f"  Warning: Could not load recent results: {e}")
    
    # Try to load historical_matches.csv
    if os.path.exists('data/historical_matches.csv'):
        print("📊 Loading historical matches...")
        try:
            with open('data/historical_matches.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    try:
                        row['home_goals'] = int(row.get('home_goals', 0))
                        row['away_goals'] = int(row.get('away_goals', 0))
                        all_results.append(row)
                        count += 1
                    except:
                        continue
                print(f"  Loaded {count} historical matches")
        except Exception as e:
            print(f"  Warning: Could not load historical matches: {e}")
    
    # Also try to load matches.csv
    if os.path.exists('data/matches.csv'):
        print("📊 Loading matches.csv...")
        try:
            with open('data/matches.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    try:
                        all_results.append({
                            'competition_code': 'PL',
                            'date': row.get('date', ''),
                            'home_team': row.get('home_team', ''),
                            'away_team': row.get('away_team', ''),
                            'home_goals': int(row.get('home_goals', 0)),
                            'away_goals': int(row.get('away_goals', 0))
                        })
                        count += 1
                    except:
                        continue
                print(f"  Loaded {count} matches from matches.csv")
        except Exception as e:
            print(f"  Warning: Could not load matches.csv: {e}")
    
    if not all_results:
        print("⚠️ No historical data found, using defaults")
    
    return all_results

def get_team_recent_matches(results, team, max_matches=10):
    """Get recent matches for a team"""
    team_matches = []
    
    for match in sorted(results, key=lambda x: x.get('date', ''), reverse=True):
        if len(team_matches) >= max_matches:
            break
        
        try:
            if match.get('home_team') == team:
                team_matches.append({
                    'date': match.get('date', ''),
                    'opponent': match.get('away_team', ''),
                    'venue': 'H',
                    'goals_for': int(match.get('home_goals', 0)),
                    'goals_against': int(match.get('away_goals', 0)),
                    'result': 'W' if int(match.get('home_goals', 0)) > int(match.get('away_goals', 0)) else 
                             ('D' if int(match.get('home_goals', 0)) == int(match.get('away_goals', 0)) else 'L')
                })
            elif match.get('away_team') == team:
                team_matches.append({
                    'date': match.get('date', ''),
                    'opponent': match.get('home_team', ''),
                    'venue': 'A',
                    'goals_for': int(match.get('away_goals', 0)),
                    'goals_against': int(match.get('home_goals', 0)),
                    'result': 'W' if int(match.get('away_goals', 0)) > int(match.get('home_goals', 0)) else 
                             ('D' if int(match.get('away_goals', 0)) == int(match.get('home_goals', 0)) else 'L')
                })
        except:
            continue
    
    return team_matches

def calculate_league_stats(results):
    """Calculate league statistics"""
    if not results:
        return {
            'avg_goals_per_team': 1.35,
            'avg_goals_per_match': 2.70,
            'home_win_rate': 0.46,
            'away_win_rate': 0.28,
            'draw_rate': 0.26
        }
    
    # Use recent matches
    recent = results[-100:] if len(results) > 100 else results
    
    total = 0
    home_wins = 0
    away_wins = 0
    total_goals = 0
    
    for m in recent:
        try:
            hg = int(m.get('home_goals', 0))
            ag = int(m.get('away_goals', 0))
            
            total += 1
            total_goals += hg + ag
            
            if hg > ag:
                home_wins += 1
            elif ag > hg:
                away_wins += 1
        except:
            continue
    
    if total == 0:
        return {
            'avg_goals_per_team': 1.35,
            'avg_goals_per_match': 2.70,
            'home_win_rate': 0.46,
            'away_win_rate': 0.28,
            'draw_rate': 0.26
        }
    
    draws = total - home_wins - away_wins
    
    return {
        'avg_goals_per_team': total_goals / (total * 2) if total > 0 else 1.35,
        'avg_goals_per_match': total_goals / total if total > 0 else 2.70,
        'home_win_rate': home_wins / total,
        'away_win_rate': away_wins / total,
        'draw_rate': draws / total
    }

def main():
    """Main prediction function"""
    
    print("\n" + "=" * 60)
    print("GENERATING FOOTBALL PREDICTIONS")
    print(f"Current date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # Load data
    upcoming_matches = load_upcoming_matches()
    
    if not upcoming_matches:
        print("❌ No upcoming matches to predict!")
        # Create empty JSON
        output = {
            'generated': datetime.now().isoformat(),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'predictions_count': 0,
            'predictions': []
        }
        with open('predictions.json', 'w') as f:
            json.dump(output, f, indent=2)
        return
    
    # Load historical data
    all_results = load_all_historical_data()
    
    # Initialize predictor
    predictor = RollingFormPredictor()
    
    # Update ELO ratings
    if all_results:
        predictor.update_elo_ratings(all_results)
        print(f"✅ Updated ELO ratings for {len(predictor.elo_ratings)} teams")
    
    # Calculate league stats
    league_stats = calculate_league_stats(all_results)
    
    # Generate predictions
    predictions = []
    
    print(f"\n🔮 Generating predictions for {len(upcoming_matches)} matches...")
    
    for match in upcoming_matches:
        try:
            # Get team recent matches
            home_matches = get_team_recent_matches(all_results, match.get('home_team', ''))
            away_matches = get_team_recent_matches(all_results, match.get('away_team', ''))
            
            # Generate prediction
            prediction = predictor.predict_match(
                match.get('home_team', 'Unknown'),
                match.get('away_team', 'Unknown'),
                home_matches,
                away_matches,
                league_stats
            )
            
            # Determine confidence
            confidence = 'high' if (len(home_matches) >= 5 and len(away_matches) >= 5) else \
                        ('medium' if (len(home_matches) >= 3 and len(away_matches) >= 3) else 'low')
            
            # Build prediction object
            pred_obj = {
                'match_id': match.get('match_id', 'unknown'),
                'date': match.get('date', ''),
                'competition': match.get('competition', 'Unknown'),
                'home_team': match.get('home_team', 'Unknown'),
                'away_team': match.get('away_team', 'Unknown'),
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
            
        except Exception as e:
            print(f"  Warning: Could not predict {match.get('home_team')} vs {match.get('away_team')}: {e}")
            continue
    
    # Sort by date
    predictions.sort(key=lambda x: x.get('date', ''))
    
    # Create output
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
            'version': '4.1-Integrated',
            'features': [
                'Rolling form with exponential decay',
                'Dynamic ELO ratings',
                'Poisson goal distribution',
                'Time-weighted performance',
                'Home advantage calibration'
            ]
        }
    }
    
    # Save to file
    with open('predictions.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Generated {len(predictions)} predictions")
    print(f"💾 Saved to predictions.json")
    print("=" * 60)

if __name__ == '__main__':
    main()
