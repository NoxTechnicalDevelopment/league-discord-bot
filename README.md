# ScuttleBuddy

A League of Legends companion bot for Discord — post-game recaps, weekly leaderboards, random champion/rune rolls, and weekly meme stats for your server.

## Features

- **`/register`** — Link your Discord account to your Riot ID
- **`/lastgame [user] [riot_id]`** — Detailed recap of the most recent match: KDA, CS, gold, damage, full item build, and role quest item (e.g. lane-quest boots). Works for any registered server member or a raw Riot ID.
- **`/leaderboard [stat]`** — Server leaderboard ranked by win rate, average KDA, total wins, or current Solo Queue rank
- **`/randomchamp`** — Random champion with a fully legal random rune page (correct keystone/row rules) and splash art
- **`/memestats`** — Weekly superlatives: most deaths, best KDA game, longest game, most damage, most gold, most CS
- **`/setleaderboardchannel`** — Configure where the weekly leaderboard + meme stats auto-post
- **`/syncnow`** — Manually trigger the weekly data sync + post (admin only)

Every Monday, the bot automatically syncs fresh match/rank data for all registered users and posts the leaderboard (all four stat categories) plus meme stats to the configured channel.

## Setup

**1. Clone and install**
```bash
git clone https://github.com/DingVersion3/league-discord-bot.git
cd league-discord-bot
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

**2. Configure environment variables**

Copy `.env.example` to `.env` and fill in:
DISCORD_BOT_TOKEN=       # From the Discord Developer Portal
DISCORD_GUILD_ID=        # Your server ID, for fast command sync during development
RIOT_API_KEY=            # From developer.riotgames.com — dev keys expire every 24h

**3. Pull champion/rune/item data from Data Dragon**
```bash
python -m leaguebot.cogs.randomchamp.fetch_ddragon
```
Re-run this after each League patch to keep champion/rune/item data current.

**4. Run the bot**
```bash
python -m leaguebot.bot
```

Or, to keep it running persistently in the background:
```bash
./run_bot.sh
```
(intended to be run inside a `tmux` session so it survives closing the terminal — see project notes)

## Tech stack

- Python 3.11+, `discord.py` (slash commands via `app_commands`)
- Riot Games API (`account-v1`, `match-v5`, `league-v4`) for live match/rank data
- Riot Data Dragon CDN for static champion/rune/item data
- SQLite (`aiosqlite`) for caching registered users, weekly match history, and rank snapshots

## Known limitations

- Riot development API keys expire every 24 hours and must be manually regenerated at [developer.riotgames.com](https://developer.riotgames.com) — a production key would remove this, but requires Riot's app approval process.
- Currently hardcoded to NA (`americas` regional routing, `na1` platform routing).