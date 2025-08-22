import os
import json
import csv
import requests
from datetime import datetime, timedelta

RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '')
RAPIDAPI_HOST = os.environ.get('RAPIDAPI_HOST', 'api-football-v1.p.rapidapi.com')

print("=" * 50)
print("SMART API-FOOTBALL FETCHER")
print(f"Current date: {datetime.now().strftime('%Y-%m-%d')}")
print("Strategy: Premier League FIRST, then big games")
print("=" * 50)

class SmartPLFetcher:
    def __init__(self):
        self.headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        self.calls_used = 0
        self.calls_limit = 95  # Keep 5 as safety buffer
        self.remaining_calls = 100  # Will update from API response
        
        # Define big teams for each league
        self.big_teams = {
            'PL': ['Manchester City', 'Liverpool', 'Arsenal', 'Manchester United', 
                   'Chelsea', 'Tottenham Hotspur', 'Newcastle United'],
            'PD': ['Real Madrid', 'Barcelona', 'Atletico Madrid', 'Real Sociedad', 
                   'Villarreal', 'Sevilla FC'],
            'BL1': ['Bayern Munich', 'Borussia Dortmund', 'RB Leipzig', 'Bayer Leverkusen',
                    'Union Berlin', 'Eintracht Frankfurt'],
            'SA': ['Juventus', 'AC Milan', 'Inter', 'Napoli', 'AS Roma', 'Lazio'],
            'FL1': ['Paris Saint-Germain', 'Monaco', 'Marseille', 'Lille', 'Lyon'],
            'CL': 'all'  # All Champions League matches are big
        }
        
    def make_request(self, endpoint, params=None):
        """Make API request with smart tracking"""
        if self.calls_used >= self.calls_limit:
            print(f"⚠️ Call limit reached ({self.calls_used}/{self.calls_limit})")
            return None
            
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        self.calls_used += 1
        
        # Update remaining calls from API
        self.remaining_calls = int(response.headers.get('X-RateLimit-Remaining', 100))
        
        print(f"  📊 Call #{self.calls_used} | Remaining today: {self.remaining_calls}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  ❌ Error {response.status_code}")
            return None
    
    def calculate_match_importance(self, home_team, away_team, league_code):
        """Calculate how important a match is (1-10 scale)"""
        score = 5  # Base score
        
        # Champions League always high priority
        if league_code == 'CL':
            score = 9
        
        # Check if big teams are playing
        if league_code in self.big_teams:
            big_teams_list = self.big_teams[league_code]
            if big_teams_list == 'all':
                score = 9
            else:
                if home_team in big_teams_list:
                    score += 2
                if away_team in big_teams_list:
                    score += 2
                # Derby or rivalry match
                if home_team in big_teams_list and away_team in big_teams_list:
                    score += 2
        
        return min(score, 10)
    
    def fetch_with_pl_priority(self):
        """Fetch with Premier League as absolute priority"""
        os.makedirs('data', exist_ok=True)
        
        # League configuration
        leagues = [
            {'id': 39, 'name': 'Premier League', 'code': 'PL', 'priority': 'MAXIMUM'},
            {'id': 2, 'name': 'Champions League', 'code': 'CL', 'priority': 'HIGH'},
            {'id': 140, 'name': 'La Liga', 'code': 'PD', 'priority': 'MEDIUM'},
            {'id': 78, 'name': 'Bundesliga', 'code': 'BL1', 'priority': 'MEDIUM'},
            {'id': 135, 'name': 'Serie A', 'code': 'SA', 'priority': 'MEDIUM'},
            {'id': 61, 'name': 'Ligue 1', 'code': 'FL1', 'priority': 'LOW'},
        ]
        
        current_year = datetime.now().year
        season = current_year if datetime.now().month >= 8 else current_year - 1
        
        all_fixtures = []
        all_predictions = []
        pl_fixtures = []
        other_fixtures = []
        
        print(f"\n🎯 Season {season}/{season+1}")
        print(f"📅 Next 7 days: {datetime.now().strftime('%Y-%m-%d')} to {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}")
        
        # ========================================
        # PHASE 1: Get ALL Premier League fixtures
        # ========================================
        print("\n" + "="*50)
        print("PHASE 1: PREMIER LEAGUE (FULL COVERAGE)")
        print("="*50)
        
        pl_data = self.make_request("fixtures", {
            "league": 39,  # Premier League
            "season": season,
            "from": datetime.now().strftime('%Y-%m-%d'),
            "to": (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        })
        
        if pl_data and pl_data.get('response'):
            for fixture in pl_data['response']:
                pl_fixture = {
                    'fixture_id': fixture['fixture']['id'],
                    'date': fixture['fixture']['date'],
                    'competition': 'Premier League',
                    'competition_code': 'PL',
                    'home_team': fixture['teams']['home']['name'],
                    'away_team': fixture['teams']['away']['name'],
                    'importance': self.calculate_match_importance(
                        fixture['teams']['home']['name'],
                        fixture['teams']['away']['name'],
                        'PL'
                    )
                }
                pl_fixtures.append(pl_fixture)
                all_fixtures.append(pl_fixture)
            
            print(f"✅ Found {len(pl_fixtures)} Premier League matches")
            
            # Get predictions for ALL PL matches
            print("\n🔮 Getting predictions for ALL Premier League matches...")
            for fixture in pl_fixtures:
                if self.calls_used >= 60:  # Safety limit
                    print("⚠️ Approaching call limit, stopping PL predictions")
                    break
                
                print(f"\n  {fixture['home_team']} vs {fixture['away_team']}")
                pred_data = self.make_request("predictions", {"fixture": fixture['fixture_id']})
                
                if pred_data and pred_data.get('response'):
                    pred = pred_data['response'][0]['predictions']
                    teams = pred_data['response'][0]['teams']
                    
                    prediction = {
                        'fixture_id': fixture['fixture_id'],
                        'date': fixture['date'],
                        'competition': fixture['competition'],
                        'home_team': fixture['home_team'],
                        'away_team': fixture['away_team'],
                        'home_win': pred['percent']['home'],
                        'draw': pred['percent']['draw'],
                        'away_win': pred['percent']['away'],
                        'home_form': teams['home']['league']['form'][-5:] if teams['home']['league']['form'] else 'UNKNOWN',
                        'away_form': teams['away']['league']['form'][-5:] if teams['away']['league']['form'] else 'UNKNOWN',
                        'advice': pred.get('advice', ''),
                        'importance': fixture['importance']
                    }
                    all_predictions.append(prediction)
        
        print(f"\n✅ Premier League complete: {len([p for p in all_predictions if p['competition'] == 'Premier League'])} predictions")
        print(f"📊 Calls used so far: {self.calls_used}")
        print(f"📊 Remaining calls: {self.remaining_calls}")
        
        # ========================================
        # PHASE 2: Get fixtures from other leagues
        # ========================================
        print("\n" + "="*50)
        print("PHASE 2: OTHER LEAGUES (FIXTURES ONLY)")
        print("="*50)
        
        # Calculate how many calls we can use for other leagues
        calls_for_fixtures = min(15, self.remaining_calls - 20)  # Keep 20 for predictions
        
        for league in leagues[1:]:  # Skip PL, already done
            if self.calls_used >= self.calls_limit - 30:  # Keep 30 for predictions
                break
            
            print(f"\n🏆 {league['name']}...")
            
            data = self.make_request("fixtures", {
                "league": league['id'],
                "season": season,
                "from": datetime.now().strftime('%Y-%m-%d'),
                "to": (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            })
            
            if data and data.get('response'):
                for fixture in data['response']:
                    other_fixture = {
                        'fixture_id': fixture['fixture']['id'],
                        'date': fixture['fixture']['date'],
                        'competition': league['name'],
                        'competition_code': league['code'],
                        'home_team': fixture['teams']['home']['name'],
                        'away_team': fixture['teams']['away']['name'],
                        'importance': self.calculate_match_importance(
                            fixture['teams']['home']['name'],
                            fixture['teams']['away']['name'],
                            league['code']
                        )
                    }
                    other_fixtures.append(other_fixture)
                    all_fixtures.append(other_fixture)
                
                print(f"  ✅ Found {len([f for f in other_fixtures if f['competition'] == league['name']])} matches")
        
        # ========================================
        # PHASE 3: Get predictions for BIG games only
        # ========================================
        print("\n" + "="*50)
        print("PHASE 3: PREDICTIONS FOR BIG GAMES")
        print("="*50)
        
        # Sort other fixtures by importance
        other_fixtures.sort(key=lambda x: x['importance'], reverse=True)
        
        # Calculate how many predictions we can get
        remaining_for_predictions = self.remaining_calls - 5  # Keep 5 as buffer
        max_other_predictions = min(remaining_for_predictions, len(other_fixtures))
        
        print(f"\n📊 Can get predictions for {max_other_predictions} more matches")
        print("Selecting highest importance matches:")
        
        # Show which matches we're selecting
        for fixture in other_fixtures[:max_other_predictions]:
            if fixture['importance'] >= 7:  # Only predict big games
                print(f"  ⭐ {fixture['home_team']} vs {fixture['away_team']} ({fixture['competition']}) - Importance: {fixture['importance']}")
        
        # Get predictions for big games
        for fixture in other_fixtures[:max_other_predictions]:
            if self.calls_used >= self.calls_limit - 2:
                break
            
            # Only get predictions for important matches (7+ importance)
            if fixture['importance'] >= 7:
                print(f"\n🔮 {fixture['home_team']} vs {fixture['away_team']} ({fixture['competition']})")
                
                pred_data = self.make_request("predictions", {"fixture": fixture['fixture_id']})
                
                if pred_data and pred_data.get('response'):
                    pred = pred_data['response'][0]['predictions']
                    teams = pred_data['response'][0]['teams']
                    
                    prediction = {
                        'fixture_id': fixture['fixture_id'],
                        'date': fixture['date'],
                        'competition': fixture['competition'],
                        'home_team': fixture['home_team'],
                        'away_team': fixture['away_team'],
                        'home_win': pred['percent']['home'],
                        'draw': pred['percent']['draw'],
                        'away_win': pred['percent']['away'],
                        'home_form': teams['home']['league']['form'][-5:] if teams['home']['league']['form'] else 'UNKNOWN',
                        'away_form': teams['away']['league']['form'][-5:] if teams['away']['league']['form'] else 'UNKNOWN',
                        'advice': pred.get('advice', ''),
                        'importance': fixture['importance']
                    }
                    all_predictions.append(prediction)
        
        # ========================================
        # PHASE 4: Save all data
        # ========================================
        print("\n" + "="*50)
        print("SAVING DATA")
        print("="*50)
        
        self.save_all_data(all_fixtures, all_predictions)
        
        # Final summary
        print("\n" + "="*50)
        print("FINAL SUMMARY")
        print("="*50)
        print(f"✅ Total fixtures fetched: {len(all_fixtures)}")
        print(f"✅ Total predictions obtained: {len(all_predictions)}")
        print(f"  - Premier League: {len([p for p in all_predictions if p['competition'] == 'Premier League'])}")
        print(f"  - Other leagues: {len([p for p in all_predictions if p['competition'] != 'Premier League'])}")
        print(f"📊 Total API calls used: {self.calls_used}/100")
        print(f"📊 Remaining for today: {self.remaining_calls}")
        
        # Show breakdown by league
        print("\nFixtures by league:")
        league_counts = {}
        for f in all_fixtures:
            league_counts[f['competition']] = league_counts.get(f['competition'], 0) + 1
        for league, count in league_counts.items():
            pred_count = len([p for p in all_predictions if p['competition'] == league])
            print(f"  {league}: {count} fixtures, {pred_count} with predictions")
        
        return all_fixtures, all_predictions
    
    def save_all_data(self, fixtures, predictions):
        """Save all fetched data"""
        
        # Save fixtures
        if fixtures:
            with open('data/upcoming_matches.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['competition', 'competition_code',
                                                       'match_id', 'date', 'home_team',
                                                       'away_team', 'status', 'importance'])
                writer.writeheader()
                for fixture in fixtures:
                    writer.writerow({
                        'competition': fixture['competition'],
                        'competition_code': fixture['competition_code'],
                        'match_id': fixture['fixture_id'],
                        'date': fixture['date'],
                        'home_team': fixture['home_team'],
                        'away_team': fixture['away_team'],
                        'status': 'SCHEDULED',
                        'importance': fixture['importance']
                    })
            print(f"✅ Saved {len(fixtures)} fixtures to upcoming_matches.csv")
        
        # Save predictions
        if predictions:
            # Save as JSON for detailed data
            with open('data/api_predictions.json', 'w') as f:
                json.dump(predictions, f, indent=2)
            print(f"✅ Saved {len(predictions)} predictions to api_predictions.json")
            
            # Also save as CSV for easy reading
            with open('data/api_predictions.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['date', 'competition', 'home_team', 
                                                       'away_team', 'home_win', 'draw', 
                                                       'away_win', 'importance'])
                writer.writeheader()
                for pred in predictions:
                    writer.writerow({
                        'date': pred['date'],
                        'competition': pred['competition'],
                        'home_team': pred['home_team'],
                        'away_team': pred['away_team'],
                        'home_win': pred['home_win'],
                        'draw': pred['draw'],
                        'away_win': pred['away_win'],
                        'importance': pred['importance']
                    })
            print(f"✅ Saved predictions to api_predictions.csv")

def main():
    if not RAPIDAPI_KEY:
        print("❌ No API key found in environment!")
        print("Please set RAPIDAPI_KEY in GitHub Secrets")
        return
    
    print(f"✅ API Key found: {RAPIDAPI_KEY[:10]}...")
    
    fetcher = SmartPLFetcher()
    fetcher.fetch_with_pl_priority()

if __name__ == '__main__':
    main()
