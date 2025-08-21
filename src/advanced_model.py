import json
import csv
import math
import os
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics

class AdvancedFootballPredictor:
    """
    Advanced prediction model incorporating:
    - ELO ratings
    - Poisson distribution for goals
    - Form analysis with momentum
    - Head-to-head weighted history
    - Home advantage factors
    - Fatigue and rest days
    - Seasonal patterns
    - Bayesian probability adjustments
    """
    
    def __init__(self):
        self.elo_ratings = {}
        self.k_factor = 32  # ELO K-factor
        self.home_advantage = 65  # ELO points for home advantage
        self.initial_elo = 1500
        
    def calculate_elo_rating(self, team_stats, matches):
        """Calculate ELO ratings for all teams"""
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
                
                # Goal difference multiplier (increases K for big wins)
                goal_diff = abs(home_goals - away_goals)
                multiplier = math.log(goal_diff + 1) if goal_diff > 0 else 1
                
                # Update ELO
                elo[home] += self.k_factor * multiplier * (home_actual - home_expected)
                elo[away] += self.k_factor * multiplier * (away_actual - away_expected)
                
            except (KeyError, ValueError):
                continue
                
        return dict(elo)
    
    def calculate_poisson_probabilities(self, home_attack, home_defense, away_attack, away_defense, league_avg):
        """Calculate match probabilities using Poisson distribution"""
        
        # Calculate expected goals
        home_expected = home_attack * away_defense * league_avg
        away_expected = away_attack * home_defense * league_avg
        
        # Apply home advantage boost
        home_expected *= 1.15
        away_expected *= 0.92
        
        # Calculate probabilities for different scorelines
        max_goals = 6
        home_win_prob = 0
        draw_prob = 0
        away_win_prob = 0
        
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                prob = self.poisson_pmf(h, home_expected) * self.poisson_pmf(a, away_expected)
                
                if h > a:
                    home_win_prob += prob
                elif h == a:
                    draw_prob += prob
                else:
                    away_win_prob += prob
        
        # Calculate over/under and BTTS
        over_25_prob = 0
        btts_prob = 0
        
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                prob = self.poisson_pmf(h, home_expected) * self.poisson_pmf(a, away_expected)
                
                if h + a > 2.5:
                    over_25_prob += prob
                if h > 0 and a > 0:
                    btts_prob += prob
        
        return {
            'home': home_win_prob,
            'draw': draw_prob,
            'away': away_win_prob,
            'over_25': over_25_prob,
            'btts': btts_prob,
            'home_expected': home_expected,
            'away_expected': away_expected
        }
    
    def poisson_pmf(self, k, lambda_val):
        """Poisson probability mass function"""
        return (lambda_val ** k) * math.exp(-lambda_val) / math.factorial(k)
    
    def calculate_form_momentum(self, recent_matches, team, is_home):
        """Calculate team form with momentum weighting"""
        if not recent_matches:
            return 0.5
        
        form_score = 0
        weights = [1.0, 0.9, 0.8, 0.6, 0.4]  # Recent matches weighted more
        total_weight = 0
        
        for i, match in enumerate(recent_matches[-5:]):
            weight = weights[min(i, 4)]
            
            if match['result'] == 'W':
                form_score += 3 * weight
            elif match['result'] == 'D':
                form_score += 1 * weight
            
            # Extra weight for matching venue
            if (is_home and match['venue'] == 'H') or (not is_home and match['venue'] == 'A'):
                form_score += 0.5 * weight
                
            total_weight += weight * 3
        
        return form_score / total_weight if total_weight > 0 else 0.5
    
    def calculate_head_to_head(self, h2h_matches, home_team, away_team):
        """Calculate head-to-head statistics with time decay"""
        if not h2h_matches:
            return {'home_advantage': 0, 'avg_goals': 2.5}
        
        home_wins = 0
        away_wins = 0
        total_goals = []
        weights_sum = 0
        
        for i, match in enumerate(h2h_matches[-10:]):  # Last 10 H2H matches
            # Time decay weight
            weight = 0.9 ** i
            
            if match['home_team'] == home_team:
                if match['home_goals'] > match['away_goals']:
                    home_wins += weight
                elif match['away_goals'] > match['home_goals']:
                    away_wins += weight
            else:
                if match['away_goals'] > match['home_goals']:
                    home_wins += weight
                elif match['home_goals'] > match['away_goals']:
                    away_wins += weight
            
            total_goals.append(match['home_goals'] + match['away_goals'])
            weights_sum += weight
        
        h2h_advantage = (home_wins - away_wins) / weights_sum if weights_sum > 0 else 0
        avg_goals = sum(total_goals) / len(total_goals) if total_goals else 2.5
        
        return {
            'home_advantage': h2h_advantage,
            'avg_goals': avg_goals
        }
    
    def calculate_fatigue_factor(self, last_match_date, current_date):
        """Calculate fatigue based on rest days"""
        if not last_match_date:
            return 1.0
        
        try:
            last = datetime.fromisoformat(last_match_date.replace('Z', '+00:00'))
            current = datetime.fromisoformat(current_date.replace('Z', '+00:00'))
            days_rest = (current - last).days
            
            if days_rest < 3:
                return 0.85  # Very fatigued
            elif days_rest < 5:
                return 0.92  # Somewhat fatigued
            elif days_rest > 10:
                return 0.95  # Might be rusty
            else:
                return 1.0  # Optimal rest
        except:
            return 1.0
    
    def apply_bayesian_adjustment(self, raw_probs, prior_probs, confidence_weight=0.15):
        """Apply Bayesian adjustment with league priors"""
        adjusted = {}
        for key in raw_probs:
            if key in prior_probs:
                adjusted[key] = (1 - confidence_weight) * raw_probs[key] + confidence_weight * prior_probs[key]
            else:
                adjusted[key] = raw_probs[key]
        return adjusted
    
    def predict_match_advanced(self, home_team, away_team, home_stats, away_stats, 
                              league_stats, h2h_data, match_date):
        """Generate advanced prediction combining all factors"""
        
        # 1. ELO-based probabilities
        if home_team in self.elo_ratings and away_team in self.elo_ratings:
            elo_diff = self.elo_ratings[home_team] - self.elo_ratings[away_team] + self.home_advantage
            elo_home_prob = 1 / (1 + 10**(-elo_diff / 400))
            elo_away_prob = 1 / (1 + 10**(elo_diff / 400))
            
            # Distribute remaining probability to draw
            elo_draw_prob = max(0, 1 - elo_home_prob - elo_away_prob)
            
            # Adjust for realistic draw probability
            elo_probs = {
                'home': elo_home_prob * 0.73,  # Scale down to leave room for draws
                'draw': 0.27,  # Typical draw rate
                'away': elo_away_prob * 0.73
            }
            
            # Normalize
            total = sum(elo_probs.values())
            elo_probs = {k: v/total for k, v in elo_probs.items()}
        else:
            elo_probs = {'home': 0.45, 'draw': 0.27, 'away': 0.28}
        
        # 2. Poisson-based probabilities
        if home_stats and away_stats and home_stats['played'] > 5 and away_stats['played'] > 5:
            # Calculate attack/defense strengths
            home_attack = (home_stats['goals_for'] / home_stats['played']) / league_stats['avg_goals_per_team']
            home_defense = (home_stats['goals_against'] / home_stats['played']) / league_stats['avg_goals_per_team']
            away_attack = (away_stats['goals_for'] / away_stats['played']) / league_stats['avg_goals_per_team']
            away_defense = (away_stats['goals_against'] / away_stats['played']) / league_stats['avg_goals_per_team']
            
            poisson_probs = self.calculate_poisson_probabilities(
                home_attack, home_defense, away_attack, away_defense, 
                league_stats['avg_goals_per_team']
            )
        else:
            poisson_probs = elo_probs.copy()
            poisson_probs['over_25'] = 0.52
            poisson_probs['btts'] = 0.50
        
        # 3. Form-based adjustments
        if home_stats and away_stats:
            home_form = self.calculate_form_momentum(home_stats.get('recent_matches', []), home_team, True)
            away_form = self.calculate_form_momentum(away_stats.get('recent_matches', []), away_team, False)
            
            form_adjustment = (home_form - away_form) * 0.15
            form_probs = {
                'home': elo_probs['home'] + form_adjustment,
                'draw': elo_probs['draw'],
                'away': elo_probs['away'] - form_adjustment
            }
            
            # Normalize
            total = sum(form_probs.values())
            form_probs = {k: max(0.05, min(0.85, v/total)) for k, v in form_probs.items()}
        else:
            form_probs = elo_probs
        
        # 4. Head-to-head adjustments
        h2h_factor = self.calculate_head_to_head(h2h_data, home_team, away_team)
        h2h_adjustment = h2h_factor['home_advantage'] * 0.08
        
        # 5. Combine all factors
        combined_probs = {
            'home': 0.35 * elo_probs['home'] + 0.35 * poisson_probs['home'] + 0.20 * form_probs['home'] + 0.10 * (elo_probs['home'] + h2h_adjustment),
            'draw': 0.35 * elo_probs['draw'] + 0.35 * poisson_probs['draw'] + 0.20 * form_probs['draw'] + 0.10 * elo_probs['draw'],
            'away': 0.35 * elo_probs['away'] + 0.35 * poisson_probs['away'] + 0.20 * form_probs['away'] + 0.10 * (elo_probs['away'] - h2h_adjustment),
            'over_25': poisson_probs.get('over_25', 0.52),
            'btts': poisson_probs.get('btts', 0.50)
        }
        
        # 6. Apply Bayesian adjustment with league priors
        league_priors = {
            'home': league_stats.get('home_win_rate', 0.46),
            'draw': league_stats.get('draw_rate', 0.26),
            'away': league_stats.get('away_win_rate', 0.28),
            'over_25': league_stats.get('over_25_rate', 0.52),
            'btts': league_stats.get('btts_rate', 0.50)
        }
        
        final_probs = self.apply_bayesian_adjustment(combined_probs, league_priors)
        
        # 7. Apply fatigue factors if we have match dates
        if home_stats and away_stats:
            home_fatigue = self.calculate_fatigue_factor(
                home_stats.get('last_match_date'), match_date
            )
            away_fatigue = self.calculate_fatigue_factor(
                away_stats.get('last_match_date'), match_date
            )
            
            fatigue_adjustment = (home_fatigue - away_fatigue) * 0.05
            final_probs['home'] += fatigue_adjustment
            final_probs['away'] -= fatigue_adjustment
        
        # 8. Final normalization and sanity checks
        # Ensure probabilities are within reasonable bounds
        final_probs['home'] = max(0.05, min(0.85, final_probs['home']))
        final_probs['away'] = max(0.05, min(0.85, final_probs['away']))
        final_probs['draw'] = max(0.10, min(0.40, final_probs['draw']))
        
        # Normalize W/D/L to sum to 1
        total_wdl = final_probs['home'] + final_probs['draw'] + final_probs['away']
        final_probs['home'] /= total_wdl
        final_probs['draw'] /= total_wdl
        final_probs['away'] /= total_wdl
        
        # Round for output
        return {k: round(v, 3) for k, v in final_probs.items()}
