import discord
from discord.ext import commands, tasks
from datetime import datetime
import os
from zoneinfo import ZoneInfo

from utils import db, embeds
from utils.db import REMINDER_DAYS

REMINDER_CHANNEL_ENV = os.getenv("REMINDER_CHANNEL_ID")

async def _find_reminder_channel(guild: discord.Guild) -> discord.TextChannel | None:
    if REMINDER_CHANNEL_ENV:
        ch = guild.get_channel(int(REMINDER_CHANNEL_ENV))
        if ch and ch.permissions_for(guild.me).send_messages:
            return ch

    preferred_names = ["deadlines", "due-dates", "announcements", "general"]
    for name in preferred_names:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch and ch.permissions_for(guild.me).send_messages:
            return ch

    for ch in guild.text_channels:
        if ch.permissions_for(guild.me).send_messages:
            return ch
    return None

class Reminders(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminder_loop.start()

    def cog_unload(self):
        self.reminder_loop.cancel()

    # Changed from 30 minutes to 1 minute so it catches exact deadlines!
    @tasks.loop(minutes=1)
    async def reminder_loop(self):
        now = datetime.now(ZoneInfo("Asia/Manila"))

        for guild_id in db.get_all_guilds():
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue

            channel = await _find_reminder_channel(guild)
            if not channel:
                continue

            deadlines = db.get_deadlines(guild_id)
            for entry in deadlines:
                due = datetime.fromisoformat(entry["due_date"])
                
                if due.tzinfo is None:
                    due = due.replace(tzinfo=ZoneInfo("Asia/Manila"))
                    
                days_left = (due - now).days
                total_seconds_left = (due - now).total_seconds()
                already_pinged = entry.get("pinged_days", [])

                # 1. Check for standard daily reminders (5, 3, 2, 1 days)
                for threshold in REMINDER_DAYS:
                    if days_left == threshold and threshold not in already_pinged and total_seconds_left > 0:
                        embed = embeds.embed_reminder(entry, days_left, guild)
                        try:
                            await channel.send(content=f"@everyone", embed=embed)
                            db.mark_pinged(guild_id, entry["id"], threshold)
                        except discord.Forbidden:
                            pass

                # 2. Early morning "Due Today" ping
                if days_left == 0 and 0 not in already_pinged and total_seconds_left > 0:
                    embed = embeds.embed_reminder(entry, 0, guild)
                    try:
                        await channel.send(content="@everyone", embed=embed)
                        db.mark_pinged(guild_id, entry["id"], 0)
                    except discord.Forbidden:
                        pass

                # 3. EXACT MOMENT the deadline is hit or missed!
                if total_seconds_left <= 0 and "missed" not in already_pinged:
                    embed = embeds.embed_deadline_missed(entry, guild)
                    try:
                        await channel.send(content="@everyone 🚨 **DEADLINE REACHED!**", embed=embed)
                        # Use a string flag so it never pings this specific deadline again
                        db.mark_pinged(guild_id, entry["id"], "missed")
                    except discord.Forbidden:
                        pass

            # Housekeeping: remove deadlines >1 day past due
            db.purge_past_deadlines(guild_id)

    @reminder_loop.before_loop
    async def before_reminder_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Reminders(bot))