import discord
from discord import app_commands
from discord.ext import commands

from utils import db, embeds

class ScoreModal(discord.ui.Modal):
    """The popup form for adding/deducting points."""
    points = discord.ui.TextInput(
        label="Number of Points",
        placeholder="e.g. 1 (Equals 50 PHP)",
        default="1",
        max_length=3,
        required=True
    )
    reason = discord.ui.TextInput(
        label="Reason (Optional)",
        placeholder="e.g. Missed the Chapter 3 deadline",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=150
    )

    def __init__(self, target_user: discord.Member, action: str):
        # action is either "add" or "deduct"
        title_verb = "Add Penalty for" if action == "add" else "Deduct Penalty for"
        full_title = f"{title_verb} {target_user.display_name}"
        
        # PREVENTS CRASHES: Force the title to be 45 characters or less
        super().__init__(title=full_title[:45]) 
        
        self.target_user = target_user
        self.action = action

    async def on_submit(self, interaction: discord.Interaction):
        try:
            pts = int(self.points.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ Points must be a valid number.", ephemeral=True)
            return

        if pts <= 0:
            await interaction.response.send_message("❌ Points must be greater than 0.", ephemeral=True)
            return

        # If deducting, make the number negative
        delta = pts if self.action == "add" else -pts
        
        # Save to DB
        new_total = db.update_score(
            guild_id=str(interaction.guild_id), 
            user_id=str(self.target_user.id), 
            display_name=self.target_user.display_name, 
            delta=delta
        )
        
        # Send confirmation
        embed = embeds.embed_score_update(self.target_user, delta, new_total, self.reason.value.strip(), self.action)
        await interaction.response.send_message(embed=embed)


class Scores(commands.GroupCog, group_name="penalty"):
    """Grouping commands under /penalty"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add", description="Add penalty points to a user")
    @app_commands.describe(user="The group member who missed a task")
    async def penalty_add(self, interaction: discord.Interaction, user: discord.Member):
        # Open the modal
        await interaction.response.send_modal(ScoreModal(target_user=user, action="add"))

    @app_commands.command(name="deduct", description="Remove penalty points from a user (e.g. they paid)")
    @app_commands.describe(user="The group member to deduct points from")
    async def penalty_deduct(self, interaction: discord.Interaction, user: discord.Member):
        # Open the modal
        await interaction.response.send_modal(ScoreModal(target_user=user, action="deduct"))

    @app_commands.command(name="list", description="View the current penalty leaderboard and debts")
    async def penalty_list(self, interaction: discord.Interaction):
        scores = db.get_all_scores(str(interaction.guild_id))
        embed = embeds.embed_score_leaderboard(scores, interaction.guild)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Scores(bot))