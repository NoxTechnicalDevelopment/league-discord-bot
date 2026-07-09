#/register: link a Discord account to a Riot ID. 
# /lastgame: post a detailed recap of a player's most recent match, accepting either a registered @user or a raw riotID#tag.
import discord
from discord import app_commands
from discord.ext import commands

from leaguebot.db import register_user, get_registered_user
from leaguebot.riot_api import get_puuid, get_match_ids, get_match, RiotAPIError
from leaguebot.items import item_name


class RecapCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="register", description="Link your Discord account to your Riot ID")
    @app_commands.describe(riot_id="Your Riot ID in the form Name#Tag, e.g. Rat King Ding#4269")
    async def register(self, interaction: discord.Interaction, riot_id: str):
        if "#" not in riot_id:
            await interaction.response.send_message(
                "Riot ID must be in the form `Name#Tag`, e.g. `Rat King Ding#4269`.",
                ephemeral=True,
            )
            return

        game_name, tag_line = riot_id.rsplit("#", 1)
        await interaction.response.defer(ephemeral=True)

        try:
            puuid = await get_puuid(game_name, tag_line)
        except RiotAPIError as e:
            await interaction.followup.send(f"Couldn't find that Riot ID: {e.message}")
            return

        await register_user(interaction.user.id, game_name, tag_line, puuid)
        await interaction.followup.send(f"Registered as **{game_name}#{tag_line}**.")

    @app_commands.command(name="lastgame", description="Get a recap of the most recent match")
    @app_commands.describe(
        user="A registered Discord member to look up",
        riot_id="Or, a raw Riot ID (Name#Tag) if they haven't registered",
    )
    async def lastgame(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
        riot_id: str | None = None,
    ):
        await interaction.response.defer()

        if riot_id:
            if "#" not in riot_id:
                await interaction.followup.send("Riot ID must be in the form `Name#Tag`.")
                return
            game_name, tag_line = riot_id.rsplit("#", 1)
            try:
                puuid = await get_puuid(game_name, tag_line)
            except RiotAPIError as e:
                await interaction.followup.send(f"Couldn't find that Riot ID: {e.message}")
                return
        else:
            target = user or interaction.user
            record = await get_registered_user(target.id)
            if not record:
                await interaction.followup.send(
                    f"{target.mention} hasn't registered yet — use `/register` first, "
                    "or pass a `riot_id` directly."
                )
                return
            puuid = record["puuid"]
            game_name, tag_line = record["game_name"], record["tag_line"]

        try:
            match_ids = await get_match_ids(puuid, count=1)
            match = await get_match(match_ids[0])
        except RiotAPIError as e:
            await interaction.followup.send(f"Riot API error: {e.message}")
            return

        participant = next(p for p in match["info"]["participants"] if p["puuid"] == puuid)

        embed = discord.Embed(
            title=f"{game_name}#{tag_line} — {participant['championName']}",
            description="Victory" if participant["win"] else "Defeat",
            color=discord.Color.green() if participant["win"] else discord.Color.red(),
        )
        embed.add_field(
            name="KDA",
            value=f"{participant['kills']}/{participant['deaths']}/{participant['assists']}",
        )
        embed.add_field(name="CS", value=str(participant["totalMinionsKilled"] + participant["neutralMinionsKilled"]))
        embed.add_field(name="Gold", value=str(participant["goldEarned"]))
        embed.add_field(name="Damage to champions", value=str(participant["totalDamageDealtToChampions"]))
        embed.add_field(name="Game mode", value=match["info"]["gameMode"])
        embed.add_field(name="Duration", value=f"{match['info']['gameDuration'] // 60}m")

        item_ids = [participant[f"item{i}"] for i in range(7)]
        item_names = [item_name(i) for i in item_ids if item_name(i)]
        embed.add_field(
            name="Build",
            value="\n".join(item_names) if item_names else "No items",
            inline=False,
        )

        role_item = item_name(participant["roleBoundItem"])
        if role_item:
            embed.add_field(name="Role Quest Item", value=role_item, inline=False)

        await interaction.response.send_message(embed=embed) if not interaction.response.is_done() else await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(RecapCog(bot))