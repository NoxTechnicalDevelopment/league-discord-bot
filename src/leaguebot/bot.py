# Bot entrypoint. Run with: python -m leaguebot.bot
import asyncio
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from leaguebot.db import init_db

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
# Optional: syncing commands to a single guild is near-instant, vs. up to an hour for a global sync. Set this in .env while you're testing.
intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    allowed_mentions=discord.AllowedMentions.none(),
)
_commands_synced = False


@bot.event
async def on_ready():
    global _commands_synced
    print(f"Logged in as {bot.user} (id: {bot.user.id})")

    if not _commands_synced:
        synced = await bot.tree.sync()
        _commands_synced = True
        print(f"Synced {len(synced)} command(s) globally (may take up to an hour to appear)")


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.CommandOnCooldown):
        message = f"Try again in {error.retry_after:.0f} seconds."
    elif isinstance(error, app_commands.MissingPermissions):
        message = "You don't have permission to use that command."
    elif isinstance(error, app_commands.NoPrivateMessage):
        message = "This command can only be used in a server."
    else:
        print(f"Application command failed: {error!r}")
        message = "Something went wrong. Please try again later."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)



async def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")
    await init_db()
    async with bot:
        await bot.load_extension("leaguebot.cogs.randomchamp.cog")
        await bot.load_extension("leaguebot.cogs.recap.cog")
        await bot.load_extension("leaguebot.cogs.leaderboard.cog")
        await bot.load_extension("leaguebot.cogs.memestats.cog")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
