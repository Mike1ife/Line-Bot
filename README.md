# NBA Prediction Line Bot 🏀🤖

A **LINE messaging bot** that provides NBA game predictions, player stats, and team insights.  
Built with **Python**, deployed on **Vercel**, and backed by **Neon (Postgres)**.

---

## 🚀 Features
- 🏀 NBA team and player prediction engine.  
- 📊 Stores and manages data using Postgres (Neon).  
- ☁️ Cloud-deployed via Vercel for seamless performance.  
- 💬 Interactive LINE Bot interface.  

---

## 📦 Installation & Deployment

### 1. Create a LINE Bot
1. Register and login at [LINE Developers Console](https://developers.line.biz/console/).  
2. Create a **Provider**.  
3. Create a **Channel** under the Provider (choose **Messaging API**).  
4. Go to **LINE Official Account Manager** to manage your Bot Account.  

🔗 Reference Guide: [Oxxo Studio - LINE Developer Setup](https://steam.oxxostudio.tw/category/python/example/line-developer.html)  

---

### 2. Clone Repository
```bash
git clone https://github.com/MikeTai1218/NBA-Prediction-Line-Bot.git
cd NBA-Prediction-Line-Bot
# You need to push it onto your own repository
git remote set-url origin <your-repo-url>
git push -u origin main
```

### 3. Set up Vercel Project

1. [Sign up / Log in to Vercel](https://vercel.com/).  
2. Create a new **Project** by importing your GitHub repository.  
3. Add environment variables under  
   **Project Settings → Environment Variables**  
   (see `config.py` for the required keys).  

### 4. Database & Storage Setup

- **Neon DB (Postgres)**: used for NBA data storage.  

Initialize the database:
```bash
python tools/CREATE_DATABASE.py
```

## ⚙️ Configuration

Update `config.py` with your credentials:

```python
LINE_BOT_API = "your_line_access_token"
HANDLER = "your_line_channel_secret"
GITHUB_NAME = "your_github_username"
DATABASE_URL = "your_neon_postgres_url"
```

## 💬 Usage

Once the bot is deployed and connected to LINE, you can interact with it using the following commands:  

---

### 🏀 Game & Prediction

- **`nba`** → Show NBA daily schedule.  
- **`NBA每日預測`** → Get NBA prediction panels. *(Recommended: schedule at 11:00 UTC every day with cron job)*  
- **`結算`** → Settle daily prediction results and calculate weekly points.  
- **`檢查`** → Check your prediction status.  
- **`跟盤`** → View another user's prediction.  
- **`比較`** → Compare predictions between two users.
- **`傷病`** → Get injury report of the team.

📂 Screenshots: [assets/game_prediction](./assets/game_prediction)  

---

### 📊 User Information & Ranking

#### 👤 User Setup
- **`註冊`** → Register to the leaderboard. *(Required before joining predictions)*  

#### 📈 Personal Stats
- **`信仰 ({TEAM NAME})`** → Show the team you predicted correctly the most.  
- **`傻鳥 ({TEAM NAME})`** → Show the team you predicted wrongly the most.  
- **`結算傻鳥`** → Summarize your most-correct and most-wrong teams for the season.  

#### 🏆 Leaderboard & Rankings
- **`週排行` / `月排行` / `季排行` / `總排行`** → Show rankings for Week, Month, Season, or All-Time.  
- **`NBA預測週最佳` / `NBA預測月最佳` / `NBA預測季最佳`** → Announce the "Best Predictor" for Week, Month, or Season.  

📂 Screenshots: [assets/user_ranking](./assets/user_ranking)  

---

### 🛠️ Others

- **`NBA猜一猜`** → Play a game where you guess a player from career stats.  
- **`news`** → Show top 5 NBA news articles from Hupu.  
- **`yt {KEYWORD}`** → Get a YouTube link for the most relevant video.  
- **`gg {KEYWORD}`** → Get a Google Image search result for the keyword.  

📂 Screenshots: [assets/others](./assets/others)  


## ⚠️ Disclaimer

This project is created **solely for fun and educational purposes**.  
It has **no commercial intent** and is **not affiliated with, endorsed, or sponsored by the NBA, LINE, or any related organization**.
