import discord
from datetime import datetime
from utils.db import TAGS, REMINDER_DAYS
from zoneinfo import ZoneInfo

# ── Brand Colors ───────────────────────────────────────────────────────────────
COLOR_SUCCESS = 0x57F287   # Green
COLOR_ERROR   = 0xED4245   # Red
COLOR_INFO    = 0x5865F2   # Blurple
COLOR_WARNING = 0xFEE75C   # Yellow

FOOTER_TEXT = "📅 Deadline Tracker • Stay on top of your schedule"

def _get_urgency(due_date_iso: str) -> tuple[str, int]:
    """Returns a formatted string for time left and the raw days difference."""
    due = datetime.fromisoformat(due_date_iso)
    
    if due.tzinfo is None:
        due = due.replace(tzinfo=ZoneInfo("Asia/Manila"))
        
    now = datetime.now(ZoneInfo("Asia/Manila"))
    
    diff = due - now
    days = diff.days
    
    # If the exact time has passed
    if diff.total_seconds() <= 0:
        return "🔴🔴🔴🔴🔴 OVERDUE", days
    
    # If it is due today (less than 24 hours but still in the future)
    if days == 0:
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        if hours > 0:
            return f"🟠🟠🟠🟠⬛ Due in {hours}h {minutes}m", days
        else:
            return f"🔴🔴🔴🔴⬛ Due in {minutes} mins!", days

    if days == 1:
        return "🟠🟠🟠⬛⬛ 1 day left", days
    elif days <= 3:
        return f"🟡🟡🟡⬛⬛ {days} days left", days
    elif days <= 5:
        return f"🟢🟢🟡⬛⬛ {days} days left", days
    else:
        return f"🟢🟢🟢🟢⬛ {days} days left", days

def embed_deadline_added(entry: dict, author: discord.Member) -> discord.Embed:
    tag_info = TAGS.get(entry["tag"], TAGS["other"])
    due = datetime.fromisoformat(entry["due_date"])
    urgency_str, _ = _get_urgency(entry["due_date"])

    embed = discord.Embed(
        title=f"{tag_info['emoji']}  Deadline Set!",
        description=f"### {entry['title']}",
        color=tag_info["color"],
        timestamp=datetime.now(ZoneInfo("Asia/Manila")),
    )
    embed.add_field(name="📂 Category",    value=f"`{tag_info['label']}`",                   inline=True)
    embed.add_field(name="📅 Due Date",    value=f"<t:{int(due.timestamp())}:F>",            inline=True)
    embed.add_field(name="⏳ Time Left",   value=urgency_str,                                inline=False)

    if entry.get("description"):
        embed.add_field(name="📝 Notes", value=entry["description"], inline=False)

    embed.add_field(
        name="🔔 Reminders",
        value="\n".join([f"• {d} days before" for d in sorted(REMINDER_DAYS)]),
        inline=True,
    )
    embed.add_field(name="🆔 ID", value=f"`#{entry['id']}`", inline=True)

    embed.set_footer(text=FOOTER_TEXT)
    if author.display_avatar:
        embed.set_thumbnail(url=author.display_avatar.url)
    return embed

def embed_deadline_list(deadlines: list[dict], guild: discord.Guild, tag_filter: str = None) -> discord.Embed:
    if tag_filter:
        tag_info = TAGS.get(tag_filter, TAGS["other"])
        title = f"{tag_info['emoji']}  {tag_info['label']} Deadlines"
        color = tag_info["color"]
    else:
        title = "📋  All Upcoming Deadlines"
        color = COLOR_INFO

    embed = discord.Embed(title=title, color=color, timestamp=datetime.now(ZoneInfo("Asia/Manila")))

    if not deadlines:
        embed.description = "✅ No deadlines found! You're all caught up."
        embed.set_footer(text=FOOTER_TEXT)
        return embed

    # 1. Group the deadlines into sections
    now = datetime.now(ZoneInfo("Asia/Manila"))
    missed = []
    near = []
    grace = []

    for entry in deadlines:
        due = datetime.fromisoformat(entry["due_date"])
        if due.tzinfo is None:
            due = due.replace(tzinfo=ZoneInfo("Asia/Manila"))
        
        diff = due - now
        
        # Sort based on exact time left
        if diff.total_seconds() <= 0:
            missed.append(entry)
        elif diff.days <= 3:
            near.append(entry)
        else:
            grace.append(entry)

    # 2. Helper function to create visual headers and add the fields
    def add_section(entries: list, section_title: str):
        if not entries:
            return # Skip if there are no deadlines in this category
        
        # Add a visual divider/header for the category
        embed.add_field(name=section_title, value="────────────────────", inline=False)
        
        for entry in entries:
            tag_info = TAGS.get(entry["tag"], TAGS["other"])
            due = datetime.fromisoformat(entry["due_date"])
            urgency_str, _ = _get_urgency(entry["due_date"])

            field_name = f"{tag_info['emoji']} {entry['title']}  ·  `#{entry['id']}`"
            field_val = (
                f"**Due:** <t:{int(due.timestamp())}:F>\n"
                f"**Status:** {urgency_str}\n"
                f"**Tag:** `{tag_info['label']}`"
            )
            if entry.get("description"):
                field_val += f"\n**Notes:** {entry['description']}"

            embed.add_field(name=field_name, value=field_val, inline=False)

    # 3. Add the categories to the embed in order of urgency
    add_section(missed, "🚨 **MISSED DEADLINES**")
    add_section(near, "⚠️ **NEAR DEADLINES (<= 3 Days)**")
    add_section(grace, "🟢 **PLENTY OF TIME (> 3 Days)**")

    embed.set_footer(text=f"{FOOTER_TEXT}  •  {len(deadlines)} deadline(s)")
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    return embed

def embed_deadline_deleted(entry: dict) -> discord.Embed:
    tag_info = TAGS.get(entry["tag"], TAGS["other"])
    embed = discord.Embed(
        title="🗑️  Deadline Removed",
        description=f"**{entry['title']}** has been deleted.",
        color=COLOR_ERROR,
        timestamp=datetime.now(ZoneInfo("Asia/Manila")),
    )
    embed.add_field(name="Category", value=tag_info["label"], inline=True)
    embed.add_field(name="ID",       value=f"#{entry['id']}",  inline=True)
    embed.set_footer(text=FOOTER_TEXT)
    return embed

def embed_reminder(entry: dict, days_left: int, guild: discord.Guild) -> discord.Embed:
    tag_info = TAGS.get(entry["tag"], TAGS["other"])
    due = datetime.fromisoformat(entry["due_date"])
    urgency_str, _ = _get_urgency(entry["due_date"])

    if days_left <= 1:
        color = COLOR_ERROR
        urgency_title = "🚨 DUE TOMORROW!" if days_left == 1 else "💀 DUE TODAY!"
    elif days_left <= 3:
        color = 0xFF8C00  # Orange
        urgency_title = f"⚠️ {days_left} Days Remaining"
    else:
        color = COLOR_WARNING
        urgency_title = f"🔔 {days_left} Days Remaining"

    embed = discord.Embed(
        title=f"{tag_info['emoji']}  Deadline Reminder",
        description=f"### {urgency_title}\n**{entry['title']}** is coming up!",
        color=color,
        timestamp=datetime.now(ZoneInfo("Asia/Manila")),
    )
    embed.add_field(name="📂 Category", value=f"`{tag_info['label']}`",        inline=True)
    embed.add_field(name="📅 Due Date", value=f"<t:{int(due.timestamp())}:F>", inline=True)
    embed.add_field(name="⏳ Time Left", value=urgency_str,                    inline=False)

    if entry.get("description"):
        embed.add_field(name="📝 Notes", value=entry["description"], inline=False)

    embed.set_footer(text=FOOTER_TEXT)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    return embed

def embed_deadline_missed(entry: dict, guild: discord.Guild) -> discord.Embed:
    """Special embed that triggers the exact minute a deadline hits."""
    tag_info = TAGS.get(entry["tag"], TAGS["other"])
    due = datetime.fromisoformat(entry["due_date"])

    embed = discord.Embed(
        title=f"🚨 DEADLINE REACHED",
        description=f"### **{entry['title']}** is due right now!",
        color=COLOR_ERROR,
        timestamp=datetime.now(ZoneInfo("Asia/Manila")),
    )
    embed.add_field(name="📂 Category", value=f"`{tag_info['label']}`", inline=True)
    embed.add_field(name="📅 Due Date", value=f"<t:{int(due.timestamp())}:F>", inline=True)
    embed.set_footer(text=FOOTER_TEXT)
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    return embed

def embed_error(message: str) -> discord.Embed:
    return discord.Embed(title="❌ Error", description=message, color=COLOR_ERROR)

def embed_success(message: str) -> discord.Embed:
    return discord.Embed(title="✅ Success", description=message, color=COLOR_SUCCESS)

def embed_score_update(member: discord.Member, delta: int, new_total: int, reason: str, action: str) -> discord.Embed:
    """Embed for when points are added or deducted."""
    color = COLOR_ERROR if action == "add" else COLOR_SUCCESS
    title = "⚠️ Penalty Added!" if action == "add" else "✅ Penalty Deducted!"
    php_total = new_total * 50

    embed = discord.Embed(title=title, color=color, timestamp=datetime.now(ZoneInfo("Asia/Manila")))
    embed.add_field(name="User", value=member.mention, inline=True)
    embed.add_field(name="Points Adjusted", value=f"{'+' if delta > 0 else ''}{delta}", inline=True)
    embed.add_field(name="New Total", value=f"**{new_total} Points** (₱{php_total})", inline=False)
    
    if reason:
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=FOOTER_TEXT)
    return embed

def embed_score_leaderboard(scores: list, guild: discord.Guild) -> discord.Embed:
    """Embed showing everyone's current penalties and PHP debt."""
    embed = discord.Embed(
        title="📊 Penalty Leaderboard", 
        description="**Conversion:** 1 Point = ₱50", 
        color=COLOR_WARNING, 
        timestamp=datetime.now(ZoneInfo("Asia/Manila"))
    )
    
    if not scores or all(s['points'] == 0 for s in scores):
        embed.description = "✅ No active penalties! Everyone is safe... for now."
        embed.set_footer(text=FOOTER_TEXT)
        return embed

    leaderboard_text = ""
    rank = 1
    for s in scores:
        if s['points'] > 0:
            php_val = s['points'] * 50
            leaderboard_text += f"**{rank}.** <@{s['user_id']}> — **{s['points']} pts** (₱{php_val})\n"
            rank += 1

    embed.add_field(name="Current Standings", value=leaderboard_text, inline=False)
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text=FOOTER_TEXT)
    return embed