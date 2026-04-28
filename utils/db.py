import json
import os
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo  # <--- Add this line here

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "deadlines.json")

# ── Tag definitions with colors and emojis ────────────────────────────────────
TAGS = {
    "thesis":       {"label": "Thesis",         "emoji": "📝", "color": 0x5865F2},  # Blurple
    "lab_exam":     {"label": "Lab Exam",        "emoji": "🔬", "color": 0xED4245},  # Red
    "quiz":         {"label": "Quiz",            "emoji": "📋", "color": 0xFEE75C},  # Yellow
    "project":      {"label": "Project",         "emoji": "🛠️", "color": 0x57F287},  # Green
    "assignment":   {"label": "Assignment",      "emoji": "📌", "color": 0xEB459E},  # Pink
    "finals":       {"label": "Finals",          "emoji": "🎓", "color": 0xFF8C00},  # Orange
    "midterms":     {"label": "Midterms",        "emoji": "📚", "color": 0x00CED1},  # Teal
    "other":        {"label": "Other",           "emoji": "🗓️", "color": 0x99AAB5},  # Grey
}

# ── Urgency thresholds (days) for ping intervals ──────────────────────────────
REMINDER_DAYS = [5, 3, 2, 1]  # ping at these many days before due

def _load() -> dict:
    """Load the deadlines database from disk."""
    if not os.path.exists(DB_PATH):
        return {}
    with open(DB_PATH, "r") as f:
        return json.load(f)

def _save(data: dict):
    """Persist the deadlines database to disk."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)

# ── CRUD Operations ───────────────────────────────────────────────────────────

def add_deadline(guild_id: str, title: str, tag: str, due_date: datetime,
                 description: str = "", set_by: str = "") -> dict:
    """Add a new deadline entry."""
    data = _load()
    guild_data = data.setdefault(str(guild_id), [])

    # Generate a simple incremental ID per guild
    existing_ids = [d.get("id", 0) for d in guild_data]
    new_id = max(existing_ids, default=0) + 1

    entry = {
        "id":          new_id,
        "title":       title,
        "tag":         tag,
        "due_date":    due_date.isoformat(),
        "description": description,
        "set_by":      set_by,
        "created_at":  datetime.utcnow().isoformat(),
        "pinged_days": [],   # tracks which reminder intervals have been sent
    }
    guild_data.append(entry)
    _save(data)
    return entry

def get_deadlines(guild_id: str, tag: Optional[str] = None) -> list[dict]:
    """Return all deadlines for a guild, optionally filtered by tag."""
    data = _load()
    entries = data.get(str(guild_id), [])
    if tag:
        entries = [e for e in entries if e["tag"] == tag]
    # Sort by due date ascending
    return sorted(entries, key=lambda e: e["due_date"])

def delete_deadline(guild_id: str, deadline_id: int) -> bool:
    """Delete a deadline by ID. Returns True if found and deleted."""
    data = _load()
    guild_data = data.get(str(guild_id), [])
    new_list = [d for d in guild_data if d["id"] != deadline_id]
    if len(new_list) == len(guild_data):
        return False  # Not found
    data[str(guild_id)] = new_list
    _save(data)
    return True

def mark_pinged(guild_id: str, deadline_id: int, days: int):
    """Record that a reminder was sent for N days before due."""
    data = _load()
    for entry in data.get(str(guild_id), []):
        if entry["id"] == deadline_id:
            if days not in entry.get("pinged_days", []):
                entry.setdefault("pinged_days", []).append(days)
            break
    _save(data)

def get_all_guilds() -> list[str]:
    """Return all guild IDs in the database."""
    return list(_load().keys())

def purge_past_deadlines(guild_id: str) -> int:
    """Remove deadlines that are more than 1 day past their due date."""
    data = _load()
    guild_data = data.get(str(guild_id), [])
    
    # Grab current Philippine Time
    now = datetime.now(ZoneInfo("Asia/Manila"))
    cleaned = []
    
    for d in guild_data:
        due = datetime.fromisoformat(d["due_date"])
        
        # FIX: Ensure older database entries are treated as Philippine Time
        if due.tzinfo is None:
            due = due.replace(tzinfo=ZoneInfo("Asia/Manila"))
            
        # Keep it if it's in the future OR less than 24 hours (86400 seconds) in the past
        if (due - now).total_seconds() > -86400:
            cleaned.append(d)
            
    removed = len(guild_data) - len(cleaned)
    data[str(guild_id)] = cleaned
    _save(data)
    return removed

def _load() -> dict:
    """Load the deadlines database from disk."""
    if not os.path.exists(DB_PATH):
        return {}
    
    try:
        with open(DB_PATH, "r") as f:
            content = f.read().strip()
            # If the file exists but is completely empty, return an empty dict
            if not content:
                return {}
            return json.loads(content)
    except json.JSONDecodeError:
        # If the file contains invalid JSON, catch the error so the bot doesn't crash
        print(f"⚠️ Warning: {DB_PATH} was corrupted or empty. Starting fresh.")
        return {}
    
# ── SCORING SYSTEM ────────────────────────────────────────────────────────────

SCORES_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "scores.json")

def _load_scores() -> dict:
    if not os.path.exists(SCORES_DB_PATH):
        return {}
    try:
        with open(SCORES_DB_PATH, "r") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except json.JSONDecodeError:
        return {}

def _save_scores(data: dict):
    os.makedirs(os.path.dirname(SCORES_DB_PATH), exist_ok=True)
    with open(SCORES_DB_PATH, "w") as f:
        json.dump(data, f, indent=2)

def update_score(guild_id: str, user_id: str, display_name: str, delta: int) -> int:
    """Adds or removes points for a user. Floors at 0."""
    data = _load_scores()
    guild_data = data.setdefault(str(guild_id), {})
    
    # Auto-enroll the user if they don't exist yet
    current = guild_data.get(str(user_id), {"points": 0, "name": display_name})
    
    # Calculate new points (prevent negative points)
    new_points = max(0, current["points"] + delta)
    current["points"] = new_points
    current["name"] = display_name 
    
    guild_data[str(user_id)] = current
    _save_scores(data)
    return new_points

def get_all_scores(guild_id: str) -> list[dict]:
    """Returns a list of all users and their scores, sorted highest to lowest."""
    data = _load_scores()
    guild_data = data.get(str(guild_id), {})
    
    scores = [{"user_id": k, **v} for k, v in guild_data.items()]
    return sorted(scores, key=lambda x: x["points"], reverse=True)