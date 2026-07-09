# /memestats: on-demand weekly meme stats digest.

import discord
from discord import app_commands
from discord.ext import commands

from leaguebot.cogs.memestats.stats import build_meme_stats_embed


class MemeStatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="memestats", description="Show this week's meme stats")
    async def memestats(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = await build_meme_stats_embed()
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(MemeStatsCog(bot))