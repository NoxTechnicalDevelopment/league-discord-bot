# Builds leaderboard embeds from stored match/rank data. Shared by the on-demand /leaderboard command and the weekly auto-post task.

import time

import discord

from leaguebot.db import get_all_registered_users, get_recent_matches, get_rank

SECONDS_PER_WEEK = 7 * 24 * 60 * 60

TIER_ORDER = [
    "IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM",
    "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER",
]
DIVISION_ORDER = {"IV": 0, "III": 1, "II": 2, "I": 3}


def _rank_sort_key(rank: dict) -> tuple:
    tier_index = TIER_ORDER.index(rank["tier"]) if rank["tier"] in TIER_ORDER else -1
    division_index = DIVISION_ORDER.get(rank["rank"], 0)
    return (tier_index, division_index, rank["league_points"] or 0)


async def _weekly_stats_for_user(discord_id: int) -> dict | None:
    since = int(time.time()) - SECONDS_PER_WEEK
    matches = await get_recent_matches(discord_id, since)
    if not matches:
        return None

    games = len(matches)
    wins = sum(m["win"] for m in matches)
    total_kills = sum(m["kills"] for m in matches)
    total_deaths = sum(m["deaths"] for m in matches)
    total_assists = sum(m["assists"] for m in matches)
    total_doubleKills = sum(m["doubleKills"] for m in matches)
    total_tripleKills = sum(m["tripleKills"] for m in matches)
    total_quadraKills = sum(m["quadraKills"] for m in matches)
    total_pentaKills = sum(m["pentaKills"] for m in matches)

    return {
        "games": games,
        "wins": wins,
        "win_rate": wins / games,
        "avg_kda": (total_kills + total_assists) / max(total_deaths, 1),
        "double_kills": total_doubleKills,
        "triple_kills": total_tripleKills,
        "quadra_kills": total_quadraKills,
        "penta_kills": total_pentaKills,
    }


async def build_leaderboard_embed(stat: str) -> discord.Embed:
    users = await get_all_registered_users()
    rows = []

    for user in users:
        label = f"{user['game_name']}#{user['tag_line']}"

        if stat == "rank":
            rank = await get_rank(user["discord_id"])
            if rank and rank["tier"]:
                rows.append((label, rank, _rank_sort_key(rank)))
        else:
            stats = await _weekly_stats_for_user(user["discord_id"])
            if stats:
                rows.append((label, stats, None))


    STAT_DISPLAY_NAMES = {
    "win_rate": "Win Rate",
    "kda": "KDA",
    "wins": "Total Wins",
    "rank": "Solo Queue Rank",
    "double_kills": "Double Kills",
    "triple_kills": "Triple Kills",
    "quadra_kills": "Quadra Kills",
    "penta_kills": "Penta Kills"
    }
    
    embed = discord.Embed(
        title=f"🏆 Leaderboard — {STAT_DISPLAY_NAMES.get(stat, stat.title())}",
        color=discord.Color.gold(),
    )

    if not rows:
        embed.description = "No data yet — play some games and run `/leaderboard` again after the next sync."
        return embed

    if stat == "rank":
        rows.sort(key=lambda r: r[2], reverse=True)
        lines = [
            f"**{i+1}.** {label} — {data['tier'].title()} {data['rank']} ({data['league_points']} LP)"
            for i, (label, data, _) in enumerate(rows)
        ]
    elif stat == "win_rate":
        rows.sort(key=lambda r: r[1]["win_rate"], reverse=True)
        lines = [
            f"**{i+1}.** {label} — {data['win_rate']*100:.0f}% ({data['wins']}/{data['games']})"
            for i, (label, data, _) in enumerate(rows)
        ]
    elif stat == "kda":
        rows.sort(key=lambda r: r[1]["avg_kda"], reverse=True)
        lines = [
            f"**{i+1}.** {label} — {data['avg_kda']:.2f} KDA ({data['games']} games)"
            for i, (label, data, _) in enumerate(rows)
        ]
    elif stat == "wins":
        rows.sort(key=lambda r: r[1]["wins"], reverse=True)
        lines = [
            f"**{i+1}.** {label} — {data['wins']} wins ({data['games']} games)"
            for i, (label, data, _) in enumerate(rows)
        ]
    elif stat == "double_kills":
        rows.sort(key=lambda r: r[1]["double_kills"], reverse=True)
        lines = [
            f"**{i+1}.** {label} — {data['double_kills']} Double Kill{'s' if data['double_kills'] != 1 else ''} ({data['games']} games)"
            for i, (label, data, _) in enumerate(rows)
        ]
    elif stat == "triple_kills":
        rows.sort(key=lambda r: r[1]["triple_kills"], reverse=True)
        lines = [
            f"**{i+1}.** {label} — {data['triple_kills']} Triple Kill{'s' if data['triple_kills'] != 1 else ''} ({data['games']} games)"
            for i, (label, data, _) in enumerate(rows)
        ]
    elif stat == "quadra_kills":
        rows.sort(key=lambda r: r[1]["quadra_kills"], reverse=True)
        lines = [
            f"**{i+1}.** {label} — {data['quadra_kills']} Quadra Kill{'s' if data['quadra_kills'] != 1 else ''} ({data['games']} games)"
            for i, (label, data, _) in enumerate(rows)
        ]
    elif stat == "penta_kills":
        rows.sort(key=lambda r: r[1]["penta_kills"], reverse=True)
        lines = [
            f"**{i+1}.** {label} — {data['penta_kills']} Penta Kill{'s' if data['penta_kills'] != 1 else ''} ({data['games']} games)"
            for i, (label, data, _) in enumerate(rows)
        ]
    else:
        lines = [f"Unknown stat: {stat}"]

    embed.description = "\n".join(lines)
    return embed