import sys
import os
import logging

# ── Fix import paths FIRST before anything else ────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

load_dotenv()

# ── Bot Configuration ──────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ── Cogs to Load ───────────────────────────────────────────────────────────────
# ── Cogs to Load ───────────────────────────────────────────────────────────────
COGS = [
    "cogs.deadlines",   # /set, /list, /delete commands
    "cogs.reminders",   # background reminder pinger
    "cogs.scores",      # /penalty add, deduct, list
]

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

async def main():
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"📦 Loaded cog: {cog}")
            except Exception as e:
                print(f"❌ Failed to load cog {cog}: {e}")
                raise   # show full traceback so errors are visible
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())