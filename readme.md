# 📅 Discord Deadline Bot

A Discord bot for tracking academic deadlines — thesis, lab exams, quizzes, and more — with automatic reminders and beautiful embeds.

---

## 🗂️ Project Structure

```
discord-deadline-bot/
├── main.py               ← Bot entry point
├── .env.example          ← Copy to .env and fill in your token
├── requirements.txt
├── data/
│   └── deadlines.json    ← Auto-created, stores all deadlines
├── cogs/
│   ├── deadlines.py      ← /set, /list, /delete, /help commands
│   └── reminders.py      ← Background reminder loop
└── utils/
    ├── db.py             ← Database read/write helpers
    └── embeds.py         ← All embed builders (aesthetic layer)
```

---

## ⚡ Quick Start

```bash
# 1. Clone / copy project files
# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up your token
cp .env.example .env
# Edit .env and paste your bot token

# 4. Run
python main.py
```

---

## 🤖 Commands

| Command | Description |
|---|---|
| `/set [tag]` | Opens a form to add a deadline |
| `/list` | Shows all upcoming deadlines |
| `/list [tag]` | Filter by category |
| `/delete [id]` | Delete a deadline by its ID |
| `/help` | Show command reference |

---

## 🏷️ Available Tags

| Emoji | Tag | Use For |
|---|---|---|
| 📝 | Thesis | Thesis submissions |
| 🔬 | Lab Exam | Laboratory exams |
| 📋 | Quiz | Quizzes |
| 🛠️ | Project | Group/individual projects |
| 📌 | Assignment | Homework & assignments |
| 🎓 | Finals | Final exams |
| 📚 | Midterms | Midterm exams |
| 🗓️ | Other | Everything else |

---

## 🔔 Reminder Schedule

The bot automatically pings `@everyone` in the reminder channel at:
- **5 days** before the deadline
- **3 days** before
- **2 days** before
- **1 day** before (tomorrow!)
- **On the due day**

To customize reminder intervals, edit `REMINDER_DAYS` in `utils/db.py`.

---

## 🛠️ Customization

### Change reminder channel
Set `REMINDER_CHANNEL_ID` in your `.env` to pin reminders to a specific channel.
Otherwise the bot auto-detects a channel named `deadlines`, `announcements`, or `general`.

### Add new tags
Edit the `TAGS` dict in `utils/db.py`:
```python
"hackathon": {"label": "Hackathon", "emoji": "💻", "color": 0x00FF00},
```
Then add it to `TAG_CHOICES` in `cogs/deadlines.py`.

### Change reminder frequency
Edit `REMINDER_DAYS` in `utils/db.py`:
```python
REMINDER_DAYS = [7, 5, 3, 2, 1]  # now also pings 7 days before
```

### Change check interval
In `cogs/reminders.py`, change `@tasks.loop(minutes=30)` to your preferred interval.