import os
import json
import csv
import requests
from datetime import datetime, timedelta
import time
import re

print("=" * 50)
print("COMPLETE PREDICTION SYSTEM")
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 50)

class CompleteFetcher:
    def __init__(self):
        # API Keys
        self.rapidapi_key = os.environ.get('RAPIDAPI_KEY', '')
        self.rapidapi_host = os.environ.get('RAPIDAPI_HOST', 'api-football-v1.p.rapidapi.com')
        self.odds_api_key = os.environ.get('ODDS_API_KEY', '')
        self.news_api_key = os.environ.get('NEWS_API_KEY', '')
        
        # Create data directory
        os.makedirs('data', exist_ok=True)
        
        # API call tracking
        self.api_calls = {
            'api-football': 0,
            'odds': 0,
            'news': 0,
            'understat': 0
        }
        
    def fetch_pl_fixtures_with_h2h(self):
        """Fetch Premier League fixtures with H2H data"""
        print("\n[1/5] Fetching Premier League fixtures...")
        
        if not self.rapidapi_key:
            print("❌ No RapidAPI key")
            return []
        
        headers = {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": self.rapidapi_host
        }
        
        # Get current season
        current_year = datetime.now().year
        season = current_year if datetime.now().month >= 8 else current_year - 1
        
        # Fetch fixtures
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
        params = {
            "league": 39,  # Premier League
            "season": season,
            "from": datetime.now().strftime('%Y-%m-%d'),
            "to": (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            self.api_calls['api-football'] += 1
            
            if response.status_code != 200:
                print(f"❌ API Error: {response.status_code}")
                return []
            
            data = response.json()
            fixtures = data.get('response', [])
            
            print(f"✅ Found {len(fixtures)} fixtures")
            
            enhanced_fixtures = []
            
            # Process each fixture
            for fixture in fixtures[:10]:  # Limit to 10
                if fixture['fixture']['status']['short'] in ['FT', 'AET', 'PEN']:
                    continue  # Skip finished matches
                
                match_data = {
                    'match_id': str(fixture['fixture']['id']),
                    'date': fixture['fixture']['date'],
                    'home_team': fixture['teams']['home']['name'],
                    'away_team': fixture['teams']['away']['name'],
                    'home_team_id': fixture['teams']['home']['id'],
                    'away_team_id': fixture['teams']['away']['id'],
                    'competition': 'Premier League',
                    'venue': fixture['fixture']['venue']['name'] if fixture['fixture'].get('venue') else ''
                }
                
                # Get H2H data
                print(f"  Getting H2H for {match_data['home_team']} vs {match_data['away_team']}...")
                h2h_url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/headtohead"
                h2h_params = {
                    "h2h": f"{match_data['home_team_id']}-{match_data['away_team_id']}",
                    "last": 10
                }
                
                try:
                    h2h_response = requests.get(h2h_url, headers=headers, params=h2h_params)
                    self.api_calls['api-football'] += 1
                    
                    if h2h_response.status_code == 200:
                        h2h_data = h2h_response.json()
                        h2h_matches = h2h_data.get('response', [])
                        
                        # Analyze H2H
                        h2h_stats = self.analyze_h2h(h2h_matches, match_data['home_team_id'])
                        match_data['h2h'] = h2h_stats
                        print(f"    ✅ H2H: {h2h_stats['summary']}")
                    else:
                        match_data['h2h'] = {'summary': 'No H2H data', 'home_wins': 0, 'draws': 0, 'away_wins': 0}
                        
                except:
                    match_data['h2h'] = {'summary': 'No H2H data', 'home_wins': 0, 'draws': 0, 'away_wins': 0}
                
                # Get predictions
                print(f"  Getting prediction...")
                pred_url = "https://api-football-v1.p.rapidapi.com/v3/predictions"
                pred_params = {"fixture": match_data['match_id']}
                
                try:
                    pred_response = requests.get(pred_url, headers=headers, params=pred_params)
                    self.api_calls['api-football'] += 1
                    
                    if pred_response.status_code == 200:
                        pred_data = pred_response.json()
                        if pred_data.get('response'):
                            prediction = pred_data['response'][0]['predictions']
                            teams = pred_data['response'][0]['teams']
                            
                            match_data['prediction'] = {
                                'home_win': prediction['percent']['home'],
                                'draw': prediction['percent']['draw'],
                                'away_win': prediction['percent']['away'],
                                'goals_home': prediction['goals'].get('home', '-'),
                                'goals_away': prediction['goals'].get('away', '-'),
                                'advice': prediction.get('advice', ''),
                                'home_form': teams['home'].get('league', {}).get('form', '')[-5:],
                                'away_form': teams['away'].get('league', {}).get('form', '')[-5:]
                            }
                            print(f"    ✅ Prediction: H{prediction['percent']['home']} D{prediction['percent']['draw']} A{prediction['percent']['away']}")
                    
                except:
                    pass
                
                enhanced_fixtures.append(match_data)
                
                # Small delay to avoid rate limits
                time.sleep(0.5)
            
            return enhanced_fixtures
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def analyze_h2h(self, h2h_matches, home_team_id):
        """Analyze head-to-head matches"""
        if not h2h_matches:
            return {'summary': 'No H2H data', 'home_wins': 0, 'draws': 0, 'away_wins': 0}
        
        stats = {'home_wins': 0, 'draws': 0, 'away_wins': 0, 'total_goals': 0}
        
        for match in h2h_matches[:10]:  # Last 10 matches
            home_goals = match['goals']['home']
            away_goals = match['goals']['away']
            
            if home_goals is None or away_goals is None:
                continue
                
            stats['total_goals'] += home_goals + away_goals
            
            # Check who was home in this H2H match
            if match['teams']['home']['id'] == home_team_id:
                if home_goals > away_goals:
                    stats['home_wins'] += 1
                elif home_goals < away_goals:
                    stats['away_wins'] += 1
                else:
                    stats['draws'] += 1
            else:
                if away_goals > home_goals:
                    stats['home_wins'] += 1
                elif away_goals < home_goals:
                    stats['away_wins'] += 1
                else:
                    stats['draws'] += 1
        
        total = stats['home_wins'] + stats['draws'] + stats['away_wins']
        if total > 0:
            avg_goals = stats['total_goals'] / total
            stats['avg_goals'] = round(avg_goals, 1)
            stats['summary'] = f"H{stats['home_wins']}-D{stats['draws']}-A{stats['away_wins']} ({avg_goals:.1f} goals/match)"
        else:
            stats['summary'] = 'No previous matches'
            
        return stats
    
    def fetch_odds_data(self, fixtures):
        """Fetch odds from The Odds API"""
        print("\n[2/5] Fetching betting odds...")
        
        if not self.odds_api_key:
            print("❌ No Odds API key")
            return fixtures
        
        # The Odds API endpoint
        url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"
        params = {
            'apiKey': self.odds_api_key,
            'regions': 'uk',
            'markets': 'h2h,totals',
            'oddsFormat': 'decimal'
        }
        
        try:
            response = requests.get(url, params=params)
            self.api_calls['odds'] += 1
            
            if response.status_code != 200:
                print(f"❌ Odds API Error: {response.status_code}")
                return fixtures
            
            odds_data = response.json()
            print(f"✅ Found odds for {len(odds_data)} matches")
            
            # Match odds to fixtures
            for fixture in fixtures:
                home_team = fixture['home_team'].lower()
                away_team = fixture['away_team'].lower()
                
                for odds_match in odds_data:
                    # Fuzzy match team names
                    if (self.fuzzy_match(home_team, odds_match['home_team'].lower()) and 
                        self.fuzzy_match(away_team, odds_match['away_team'].lower())):
                        
                        # Get best odds from all bookmakers
                        best_odds = self.get_best_odds(odds_match)
                        fixture['odds'] = best_odds
                        
                        # Convert odds to implied probabilities
                        if best_odds:
                            total = 1/best_odds['home'] + 1/best_odds['draw'] + 1/best_odds['away']
                            fixture['market_probs'] = {
                                'home': round((1/best_odds['home'])/total, 3),
                                'draw': round((1/best_odds['draw'])/total, 3),
                                'away': round((1/best_odds['away'])/total, 3)
                            }
                            print(f"  ✅ Odds for {fixture['home_team']}: {fixture['market_probs']}")
                        break
            
            # Show API usage
            remaining = response.headers.get('x-requests-remaining', 'Unknown')
            print(f"  Odds API calls remaining: {remaining}")
            
        except Exception as e:
            print(f"❌ Odds error: {e}")
        
        return fixtures
    
    def fuzzy_match(self, str1, str2):
        """Simple fuzzy string matching"""
        # Remove common suffixes
        for suffix in [' fc', ' united', ' city', ' town', ' hotspur', ' wanderers']:
            str1 = str1.replace(suffix, '')
            str2 = str2.replace(suffix, '')
        
        # Check if main part matches
        return str1 in str2 or str2 in str1
    
    def get_best_odds(self, odds_match):
        """Extract best odds from bookmakers"""
        if not odds_match.get('bookmakers'):
            return None
        
        best = {'home': 0, 'draw': 0, 'away': 0, 'over_25': 0, 'under_25': 0}
        
        for bookmaker in odds_match['bookmakers']:
            for market in bookmaker['markets']:
                if market['key'] == 'h2h':
                    for outcome in market['outcomes']:
                        if outcome['name'] == odds_match['home_team']:
                            best['home'] = max(best['home'], outcome['price'])
                        elif outcome['name'] == odds_match['away_team']:
                            best['away'] = max(best['away'], outcome['price'])
                        else:  # Draw
                            best['draw'] = max(best['draw'], outcome['price'])
                            
                elif market['key'] == 'totals' and 'over_under' in market:
                    for outcome in market['outcomes']:
                        if outcome['name'] == 'Over' and outcome['point'] == 2.5:
                            best['over_25'] = max(best['over_25'], outcome['price'])
                        elif outcome['name'] == 'Under' and outcome['point'] == 2.5:
                            best['under_25'] = max(best['under_25'], outcome['price'])
        
        return best if best['home'] > 0 else None
    
    def fetch_xg_data(self, fixtures):
        """Fetch xG data from Understat"""
        print("\n[3/5] Fetching xG data...")
        
        # Map team names to Understat format
        team_map = {
            'Manchester City': 'Manchester_City',
            'Manchester United': 'Manchester_United', 
            'Liverpool': 'Liverpool',
            'Chelsea': 'Chelsea',
            'Arsenal': 'Arsenal',
            'Tottenham Hotspur': 'Tottenham',
            'Newcastle United': 'Newcastle_United',
            'Brighton & Hove Albion': 'Brighton',
            'Aston Villa': 'Aston_Villa',
            'West Ham United': 'West_Ham',
            'Wolverhampton Wanderers': 'Wolverhampton_Wanderers',
            'Fulham': 'Fulham',
            'Brentford': 'Brentford',
            'Crystal Palace': 'Crystal_Palace',
            'Nottingham Forest': 'Nottingham_Forest',
            'Everton': 'Everton',
            'Leicester City': 'Leicester',
            'Southampton': 'Southampton',
            'Ipswich Town': 'Ipswich',
            'Bournemouth': 'Bournemouth'
        }
        
        season = datetime.now().year if datetime.now().month >= 8 else datetime.now().year - 1
        
        for fixture in fixtures:
            home_understat = team_map.get(fixture['home_team'])
            away_understat = team_map.get(fixture['away_team'])
            
            if home_understat:
                xg_url = f"https://understat.com/team/{home_understat}/{season}"
                print(f"  Fetching xG for {fixture['home_team']}...")
                
                try:
                    response = requests.get(xg_url)
                    self.api_calls['understat'] += 1
                    
                    if response.status_code == 200:
                        # Extract JSON data from HTML
                        import re
                        json_pattern = r"var datesData\s*=\s*JSON\.parse\('(.+?)'\)"
                        match = re.search(json_pattern, response.text)
                        
                        if match:
                            json_str = match.group(1).replace("\\'", "'")
                            xg_data = json.loads(json_str)
                            
                            # Get last 5 matches xG
                            recent_xg = []
                            for match_data in list(xg_data)[-5:]:
                                recent_xg.append({
                                    'xG': float(match_data.get('xG', 0)),
                                    'xGA': float(match_data.get('xGA', 0)),
                                    'scored': int(match_data.get('scored', 0)),
                                    'missed': int(match_data.get('missed', 0))
                                })
                            
                            if recent_xg:
                                avg_xg = sum(m['xG'] for m in recent_xg) / len(recent_xg)
                                avg_xga = sum(m['xGA'] for m in recent_xg) / len(recent_xg)
                                
                                if 'xg_data' not in fixture:
                                    fixture['xg_data'] = {}
                                    
                                fixture['xg_data'][f'{fixture["home_team"]}_xG'] = round(avg_xg, 2)
                                fixture['xg_data'][f'{fixture["home_team"]}_xGA'] = round(avg_xga, 2)
                                
                                print(f"    ✅ {fixture['home_team']} xG: {avg_xg:.2f}, xGA: {avg_xga:.2f}")
                
                except Exception as e:
                    print(f"    ⚠️ Could not get xG: {e}")
                
                time.sleep(1)  # Be respectful to Understat
        
        return fixtures
    
    def fetch_team_news(self, fixtures):
        """Fetch injury and team news"""
        print("\n[4/5] Fetching team news...")
        
        if not self.news_api_key:
            print("❌ No News API key")
            return fixtures
        
        url = "https://newsapi.org/v2/everything"
        
        for fixture in fixtures[:5]:  # Limit to save API calls
            query = f"{fixture['home_team']} {fixture['away_team']} injury team news"
            params = {
                'q': query,
                'domains': 'bbc.co.uk,skysports.com,theguardian.com',
                'sortBy': 'publishedAt',
                'pageSize': 5,
                'apiKey': self.news_api_key,
                'from': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
            }
            
            try:
                response = requests.get(url, params=params)
                self.api_calls['news'] += 1
                
                if response.status_code == 200:
                    news_data = response.json()
                    articles = news_data.get('articles', [])
                    
                    injuries = []
                    for article in articles:
                        title = article.get('title', '').lower()
                        desc = article.get('description', '').lower()
                        
                        # Look for injury keywords
                        if any(word in title + desc for word in ['injury', 'injured', 'out', 'doubt', 'return']):
                            injuries.append({
                                'title': article.get('title', ''),
                                'source': article.get('source', {}).get('name', ''),
                                'url': article.get('url', '')
                            })
                    
                    if injuries:
                        fixture['team_news'] = injuries[:3]  # Top 3 relevant articles
                        print(f"  ✅ Found {len(injuries)} injury updates for {fixture['home_team']} vs {fixture['away_team']}")
                    
            except Exception as e:
                print(f"  ⚠️ News error: {e}")
            
            time.sleep(0.5)
        
        return fixtures
    
    def save_all_data(self, fixtures):
        """Save all collected data"""
        print("\n[5/5] Saving data...")
        
        # Save enhanced fixtures
        with open('data/enhanced_fixtures.json', 'w') as f:
            json.dump(fixtures, f, indent=2)
        print(f"✅ Saved {len(fixtures)} enhanced fixtures")
        
        # Save for predict.py
        simple_fixtures = []
        for f in fixtures:
            simple_fixtures.append({
                'match_id': f['match_id'],
                'date': f['date'],
                'home_team': f['home_team'],
                'away_team': f['away_team'],
                'competition': 'Premier League',
                'competition_code': 'PL',
                'status': 'SCHEDULED'
            })
        
        with open('data/upcoming_matches.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['match_id', 'date', 'home_team', 
                                                   'away_team', 'competition', 
                                                   'competition_code', 'status'])
            writer.writeheader()
            writer.writerows(simple_fixtures)
        
        # Show API usage summary
        print("\n📊 API Usage Summary:")
        for api, calls in self.api_calls.items():
            print(f"  {api}: {calls} calls")
    
    def run(self):
        """Run complete data collection"""
        print("\n🚀 Starting complete data collection...")
        
        # Step 1: Get fixtures with H2H
        fixtures = self.fetch_pl_fixtures_with_h2h()
        
        if not fixtures:
            print("❌ No fixtures found")
            return
        
        # Step 2: Add odds data
        fixtures = self.fetch_odds_data(fixtures)
        
        # Step 3: Add xG data
        fixtures = self.fetch_xg_data(fixtures)
        
        # Step 4: Add team news
        fixtures = self.fetch_team_news(fixtures)
        
        # Step 5: Save everything
        self.save_all_data(fixtures)
        
        print("\n✅ Complete data collection finished!")
        print(f"📊 Total API calls: {sum(self.api_calls.values())}")

if __name__ == '__main__':
    fetcher = CompleteFetcher()
    fetcher.run()
