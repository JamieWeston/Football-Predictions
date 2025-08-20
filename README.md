# Football Predictions

Automated Premier League match predictions updated daily.

## 📊 Latest Predictions

View the latest predictions: [predictions.json](predictions.json)

## 🔗 API Endpoint for Your Frontend

Use this URL in your Lovable frontend:
https://raw.githubusercontent.com/YOUR_USERNAME/football-predictions/main/predictions.json

## 📅 Update Schedule

- Predictions update daily at 8 AM UTC
- Manual update: Go to Actions tab → Click "Football Predictions" → Click "Run workflow"

## 📈 Prediction Model

The system analyzes:
- Recent team form
- Home/away performance
- Head-to-head history
- Goals scored/conceded
- League position

## 🎯 Probability Outputs

Each match includes:
- Home win probability
- Draw probability
- Away win probability
- Over 2.5 goals probability
- Both teams to score probability

## 📱 Frontend Integration

In your Lovable app, fetch data using:

```javascript
fetch('https://raw.githubusercontent.com/YOUR_USERNAME/football-predictions/main/predictions.json')
  .then(response => response.json())
  .then(data => {
    console.log(data.predictions);
  });
📝 License
MIT

Automated predictions for entertainment purposes only. Please gamble responsibly.

---

### File 5: `.gitignore`
**Path:** In root folder → Create file `.gitignore`
Python
pycache/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env
Data files
*.csv
!data/sample.csv
OS
.DS_Store
Thumbs.db
IDE
.vscode/
.idea/
*.swp
*.swo

---

### File 6: `data/sample.csv`
**Path:** Create folder `data` → Create file `sample.csv`

```csv
date,home_team,away_team,home_goals,away_goals,status
2024-08-01,Arsenal,Chelsea,2,1,FINISHED
2024-08-02,Liverpool,Manchester United,3,2,FINISHED
2024-08-03,Manchester City,Tottenham,4,1,FINISHED
2024-08-04,Fulham,Brentford,1,1,FINISHED
2024-08-05,Newcastle,Brighton,2,0,FINISHED
