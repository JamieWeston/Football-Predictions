import math
import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict, deque

class RollingFormPredictor:
    """
    Advanced predictor with:
    - Rolling form with exponential decay
    - xG (expected goals) integration
    - Dynamic ELO updates
    - Recent transfer/injury adjustments
    - Time-aware predictions
    """
    
    def __init__(self):
        self.elo_ratings = {}
        self.k_factor = 32
        self.home_advantage = 65
        self.initial_elo = 1500
        self.xg_weight = 0.3  # How much to weight xG vs actual goals
        
    def calculate_time_weighted_form(self, recent_matches, decay_rate=0.9):
        """Calculate form with exponential decay for recency"""
        if not recent_matches:
            return 0.5
        
        total_weight = 0
        weighted_points = 0
        
        # Sort by date, most recent first
        sorted_matches = sorted(recent_matches, 
                               key=lambda x: datetime.fromisoformat(x['date'].replace('Z', '+00:00')), 
                               reverse=True)
        
        for i, match in enumerate(sorted_matches[:10]):  # Last 10 matches
            weight = decay_rate ** i
            
            # Points from result
            if match['result'] == 'W':
                points = 3
            elif match['result'] == 'D':
                points = 1
            else:
                points = 0
            
            # Adjust for xG if available
            if match.get('xg_for') is not None and match.get('xg_against') is not None:
                xg_diff = match['xg_for'] - match['xg_against']
                actual_diff = match['goals_for'] - match['goals_against']
                
                # Team overperformed or underperformed?
                performance_factor = 1.0
                if xg_diff > 0 and actual_diff > xg_diff:
                    performance_factor = 1.1  # Lucky win
                elif xg_diff > 0 and actual_diff < xg_diff:
                    performance_factor = 0.9  # Should have won by more
                elif xg_diff < 0 and actual_diff > xg_diff:
                    performance_factor = 1.2  # Great performance
                
                points *= performance_factor
            
            weighted_points += points * weight
            total_weight += weight * 3  # Max 3 points per match
        
        return weighted_points / total_weight if total_weight > 0 else 0.5
    
    def calculate_rolling_xg(self, recent_matches, window=5):
        """Calculate rolling xG averages"""
        if not recent_matches:
            return 1.3, 1.3  # League average defaults
        
        sorted_matches = sorted(recent_matches, 
                               key=lambda x: datetime.fromisoformat(x['date'].replace('Z', '+00:00')), 
                               reverse=True)
        
        xg_for = []
        xg_against = []
        goals_for = []
        goals_against = []
        
        for match in sorted_matches[:window]:
            if match.get('xg_for') is not None:
                xg_for.append(match['xg_for'])
                xg_against.append(match['xg_against'])
            goals_for.append(match['goals_for'])
            goals_against.append(match['goals_against'])
        
        # Blend xG with actual goals
        if xg_for:
            avg_xg_for = sum(xg_for) / len(xg_for)
            avg_xg_against = sum(xg_against) / len(xg_against)
        else:
            avg_xg_for = sum(goals_for) / len(goals_for) if goals_for else 1.3
            avg_xg_against = sum(goals_against) / len(goals_against) if goals_against else 1.3
        
        avg_goals_for = sum(goals_for) / len(goals_for) if goals_for else 1.3
        avg_goals_against = sum(goals_against) / len(goals_against) if goals_against else 1.3
        
        # Weighted average of xG and actual
        final_attack = (self.xg_weight * avg_xg_for + (1 - self.xg_weight) * avg_goals_for)
        final_defense = (self.xg_weight * avg_xg_against + (1 - self.xg_weight) * avg_goals_against)
        
        return final_attack, final_defense
    
    def update_elo_ratings(self, matches):
        """Update ELO ratings based on recent matches"""
        elo = defaultdict(lambda: self.initial_elo)
        
        for match in sorted(matches, key=lambda x: x.get('date', '')):
            try:
                home = match['home_team']
                away = match['away_team']
                home_goals = int(match['home_goals'])
                away_goals = int(match['away_goals'])
                
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
                
                # Goal difference multiplier
                goal_diff = abs(home_goals - away_goals)
                multiplier = 1 + (goal_diff - 1) * 0.5 if goal_diff > 1 else 1
                
                # Update with xG consideration if available
                if match.get('home_xg') and match.get('away_xg'):
                    xg_diff = match['home_xg'] - match['away_xg']
                    actual_diff = home_goals - away_goals
                    
                    # If result doesn't match xG, reduce the impact
                    if (xg_diff > 0.5 and actual_diff < 0) or (xg_diff < -0.5 and actual_diff > 0):
                        multiplier *= 0.7  # Lucky result, less ELO change
                
                # Update ELO
                elo[home] += self.k_factor * multiplier * (home_actual - home_expected)
                elo[away] += self.k_factor * multiplier * (away_actual - away_expected)
                
            except (KeyError, ValueError):
                continue
        
        self.elo_ratings = dict(elo)
        return self.elo_ratings
    
    def predict_match(self, home_team, away_team, home_matches, away_matches, 
                     match_date, league_stats):
        """Generate prediction with all factors"""
        
        # 1. Calculate rolling form
        home_form = self.calculate_time_weighted_form(home_matches)
        away_form = self.calculate_time_weighted_form(away_matches)
        
        # 2. Calculate rolling xG
        home_attack, home_defense = self.calculate_rolling_xg(home_matches)
        away_attack, away_defense = self.calculate_rolling_xg(away_matches)
        
        # 3. Get ELO ratings
        home_elo = self.elo_ratings.get(home_team, self.initial_elo)
        away_elo = self.elo_ratings.get(away_team, self.initial_elo)
        
        # 4. Calculate base probabilities from ELO
        elo_diff = home_elo - away_elo + self.home_advantage
        home_win_elo = 1 / (1 + 10**(-elo_diff / 400))
        away_win_elo = 1 / (1 + 10**(elo_diff / 400))
        
        # 5. Calculate Poisson probabilities from xG
        league_avg = league_stats.get('avg_goals_per_team', 1.35)
        home_expected = (home_attack / league_avg) * (away_defense / league_avg) * league_avg * 1.1
        away_expected = (away_attack / league_avg) * (home_defense / league_avg) * league_avg * 0.9
        
        poisson_probs = self.calculate_poisson_probs(home_expected, away_expected)
        
        # 6. Combine all factors
        # Weights: ELO 35%, Poisson 35%, Form 30%
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
        home_prob /= total
        draw_prob /= total
        away_prob /= total
        
        # 7. Calculate other markets
        total_expected = home_expected + away_expected
        over_25 = self.calculate_over_probability(total_expected, 2.5)
        btts = (1 - self.poisson_pmf(0, home_expected)) * (1 - self.poisson_pmf(0, away_expected))
        
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
    
    def calculate_poisson_probs(self, home_lambda, away_lambda):
        """Calculate match outcome probabilities using Poisson"""
        home_win = 0
        draw = 0
        away_win = 0
        
        for h in range(7):  # Goals up to 6
            for a in range(7):
                prob = self.poisson_pmf(h, home_lambda) * self.poisson_pmf(a, away_lambda)
                if h > a:
                    home_win += prob
                elif h == a:
                    draw += prob
                else:
                    away_win += prob
        
        return {'home': home_win, 'draw': draw, 'away': away_win}
    
    def calculate_over_probability(self, total_lambda, threshold):
        """Calculate probability of over X goals"""
        under_prob = 0
        for i in range(int(threshold) + 1):
            under_prob += self.poisson_pmf(i, total_lambda)
        return 1 - under_prob
    
    def poisson_pmf(self, k, lambda_val):
        """Poisson probability mass function"""
        return (lambda_val ** k) * math.exp(-lambda_val) / math.factorial(min(k, 20))
