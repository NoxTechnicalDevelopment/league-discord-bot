# Builds a weekly meme stats embed: fun superlatives pulled from every registered user's matches this week (most deaths, longest game, etc).
import time

import discord

from leaguebot.db import get_all_recent_matches

SECONDS_PER_WEEK = 7 * 24 * 60 * 60


def _label(match: dict) -> str:
    return f"{match['game_name']}#{match['tag_line']}"


async def build_meme_stats_embed(guild: discord.Guild) -> discord.Embed:
    since = int(time.time()) - SECONDS_PER_WEEK
    all_matches = await get_all_recent_matches(since)
    matches = [m for m in all_matches if guild.get_member(m["discord_id"]) is not None]

    embed = discord.Embed(title="🎭 Weekly Meme Stats", color=discord.Color.purple())

    if not matches:
        embed.description = "No games played this week — get out of here!"
        return embed

    most_deaths = max(matches, key=lambda m: m["deaths"])
    embed.add_field(
        name="💀 Most Deaths",
        value=f"{_label(most_deaths)} — {most_deaths['deaths']} deaths on {most_deaths['champion']}",
        inline=False,
    )

    best_kda = max(matches, key=lambda m: (m["kills"] + m["assists"]) / max(m["deaths"], 1))
    kda_ratio = (best_kda["kills"] + best_kda["assists"]) / max(best_kda["deaths"], 1)
    embed.add_field(
        name="⭐ Best KDA Game",
        value=f"{_label(best_kda)} — {best_kda['kills']}/{best_kda['deaths']}/{best_kda['assists']} "
              f"({kda_ratio:.1f} KDA) on {best_kda['champion']}",
        inline=False,
    )

    worst_kda = min(matches, key=lambda m: (m["kills"] + m["assists"]) / max(m["deaths"], 1))
    worst_kda_ratio = (worst_kda["kills"] + worst_kda["assists"]) / max(worst_kda["deaths"], 1)
    embed.add_field(
        name="🍗Inter of the Week",
        value=f"{_label(worst_kda)} - {worst_kda['kills']}/{worst_kda['deaths']}/{worst_kda['assists']}"
              f"({worst_kda_ratio:.1f} KDA) on {worst_kda['champion']}",
        inline=False,
    )

    longest_game = max(matches, key=lambda m: m["duration"])
    embed.add_field(
        name="⏱️ Longest Game",
        value=f"{_label(longest_game)} — {longest_game['duration'] // 60}m on {longest_game['champion']}",
        inline=False,
    )

    biggest_carry = max(matches, key=lambda m: m["damage"])
    embed.add_field(
        name="🗡️ Most Damage Dealt",
        value=f"{_label(biggest_carry)} — {biggest_carry['damage']:,} damage on {biggest_carry['champion']}",
        inline=False,
    )

    richest = max(matches, key=lambda m: m["gold"])
    embed.add_field(
        name="💰 Most Gold Earned",
        value=f"{_label(richest)} — {richest['gold']:,} gold on {richest['champion']}",
        inline=False,
    )

    hardest_farmer = max(matches, key=lambda m: m["cs"])
    embed.add_field(
        name="🌾 Most CS",
        value=f"{_label(hardest_farmer)} — {hardest_farmer['cs']} CS on {hardest_farmer['champion']}",
        inline=False,
    )

    embed.set_footer(text=f"Based on {len(matches)} game(s) played this week")
    return embed