# Bot entrypoint. Run with: python -m leaguebot.bot
import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv
from leaguebot.db import init_db

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
# Optional: syncing commands to a single guild is near-instant, vs. up to an hour for a global sync. Set this in .env while you're testing.
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id: {bot.user.id})")

    # This bypasses the guild lock and forces a global sync
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} command(s) globally (may take up to an hour to appear)")



async def main():
    await init_db()
    async with bot:
        await bot.load_extension("leaguebot.cogs.randomchamp.cog")
        await bot.load_extension("leaguebot.cogs.recap.cog")
        await bot.load_extension("leaguebot.cogs.leaderboard.cog")
        await bot.load_extension("leaguebot.cogs.memestats.cog")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())