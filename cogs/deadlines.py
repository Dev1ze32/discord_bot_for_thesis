import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from utils import db, embeds
from utils.db import TAGS

# ── Tag choices for slash command autocomplete ────────────────────────────────
TAG_CHOICES = [
    app_commands.Choice(name=f"{info['emoji']} {info['label']}", value=key)
    for key, info in TAGS.items()
]

class DeadlineModal(discord.ui.Modal, title="📅 Set a New Deadline"):
    """Modal form that appears when user runs /set."""

    deadline_title = discord.ui.TextInput(
        label="Title",
        placeholder="e.g. Chapter 3 Thesis Submission",
        max_length=80,
        required=True,
    )
    due_date = discord.ui.TextInput(
        label="Due Date (YYYY-MM-DD)",
        placeholder="e.g. 2026-06-15",
        max_length=10,
        required=True,
    )
    due_time = discord.ui.TextInput(
        label="Time (HH:MM) [Optional]",
        placeholder="e.g. 23:59 (Defaults to end of day)",
        max_length=5,
        required=False, # Made optional for better UX
    )
    description = discord.ui.TextInput(
        label="Notes (optional)",
        placeholder="Any extra details...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=200,
    )

    def __init__(self, tag: str):
        super().__init__()
        self.tag = tag

    async def on_submit(self, interaction: discord.Interaction):
        # ── Parse the due date and time ────────────────────────────────────────
        raw_date = self.due_date.value.strip()
        raw_time = self.due_time.value.strip()
        
        # Default to 23:59 if the user leaves the time field blank
        if not raw_time:
            raw_time = "23:59"

        # 1. Define Philippine Time
        PHT = ZoneInfo("Asia/Manila")

        try:
            # 2. Parse the date and explicitly tag it as Philippine Time
            due = datetime.strptime(f"{raw_date} {raw_time}", "%Y-%m-%d %H:%M").replace(tzinfo=PHT)
        except ValueError:
            await interaction.response.send_message(
                embed=embeds.embed_error("Invalid date or time format. Please use `YYYY-MM-DD` and `HH:MM`."),
                ephemeral=True,
            )
            return

        # 3. Compare against current Philippine Time
        if due < datetime.now(PHT):
            await interaction.response.send_message(
                embed=embeds.embed_error("That date is already in the past!"),
                ephemeral=True,
            )
            return

        # ── Save to DB ─────────────────────────────────────────────────────────
        entry = db.add_deadline(
            guild_id=str(interaction.guild_id),
            title=self.deadline_title.value.strip(),
            tag=self.tag,
            due_date=due,
            description=self.description.value.strip(),
            set_by=str(interaction.user),
        )

        embed = embeds.embed_deadline_added(entry, interaction.user)
        await interaction.response.send_message(embed=embed)
        
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        import traceback
        
        # 1. Print the full error to your Ubuntu terminal
        print("\n--- MODAL CRASH ---")
        traceback.print_exception(type(error), error, error.__traceback__)
        print("-------------------\n")

        # 2. Show the error directly in Discord so you don't have to switch windows
        error_message = f"❌ **Bot Crashed!**\n```py\n{error}\n```"
        try:
            if interaction.response.is_done():
                await interaction.followup.send(error_message, ephemeral=True)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)
        except Exception as e:
            print(f"Failed to send error to Discord: {e}")


class Deadlines(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /set ──────────────────────────────────────────────────────────────────
    @app_commands.command(name="set", description="📅 Set a new deadline or due date")
    @app_commands.describe(tag="What kind of deadline is this?")
    @app_commands.choices(tag=TAG_CHOICES)
    async def set_deadline(self, interaction: discord.Interaction, tag: str):
        modal = DeadlineModal(tag=tag)
        await interaction.response.send_modal(modal)

    # ── /list ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="list", description="📋 View all upcoming deadlines")
    @app_commands.describe(tag="Filter by category (optional)")
    @app_commands.choices(tag=TAG_CHOICES)
    async def list_deadlines(self, interaction: discord.Interaction,
                              tag: Optional[str] = None):
        await interaction.response.defer()
        deadlines = db.get_deadlines(str(interaction.guild_id), tag=tag)
        embed = embeds.embed_deadline_list(deadlines, interaction.guild, tag_filter=tag)
        await interaction.followup.send(embed=embed)

    # ── /delete ───────────────────────────────────────────────────────────────
    @app_commands.command(name="delete", description="🗑️ Delete a deadline by its ID")
    @app_commands.describe(deadline_id="The ID number shown next to the deadline (e.g. 3)")
    async def delete_deadline(self, interaction: discord.Interaction, deadline_id: int):
        # Find entry before deleting (so we can show its info in the embed)
        deadlines = db.get_deadlines(str(interaction.guild_id))
        entry = next((d for d in deadlines if d["id"] == deadline_id), None)

        if not entry:
            await interaction.response.send_message(
                embed=embeds.embed_error(f"No deadline found with ID `#{deadline_id}`."),
                ephemeral=True,
            )
            return

        db.delete_deadline(str(interaction.guild_id), deadline_id)
        embed = embeds.embed_deadline_deleted(entry)
        await interaction.response.send_message(embed=embed)

    # ── /help ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="help", description="❓ How to use the Deadline Bot")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📅  Deadline Bot — Help",
            description="Stay on top of every due date, exam, and submission!",
            color=embeds.COLOR_INFO,
        )
        embed.add_field(
            name="`/set [tag]`",
            value="Open a form to add a new deadline with a title, due date, and notes.",
            inline=False,
        )
        embed.add_field(
            name="`/list [tag?]`",
            value="Show all upcoming deadlines. Optionally filter by category.",
            inline=False,
        )
        embed.add_field(
            name="`/delete [id]`",
            value="Remove a deadline using its ID (visible in `/list`).",
            inline=False,
        )
        embed.add_field(
            name="🔔 Auto Reminders",
            value="The bot pings **5, 3, 2, and 1 day(s)** before each deadline automatically.",
            inline=False,
        )

        tag_lines = "\n".join(
            [f"{info['emoji']} **{info['label']}**" for info in TAGS.values()]
        )
        embed.add_field(name="📂 Available Tags", value=tag_lines, inline=True)
        embed.set_footer(text=embeds.FOOTER_TEXT)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Deadlines(bot))