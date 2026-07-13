# SQLite-backed storage for guild-scoped Discord-to-Riot account mappings.
from contextlib import asynccontextmanager
import os
from pathlib import Path

import aiosqlite

DB_PATH = Path(__file__).parent.parent.parent / "data" / "bot.db"


@asynccontextmanager
async def _database():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("PRAGMA busy_timeout = 5000")
        yield db


async def _create_schema(db: aiosqlite.Connection) -> None:
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            guild_id INTEGER NOT NULL CHECK(guild_id > 0),
            discord_id INTEGER NOT NULL CHECK(discord_id > 0),
            game_name TEXT NOT NULL CHECK(length(game_name) BETWEEN 1 AND 100),
            tag_line TEXT NOT NULL CHECK(length(tag_line) BETWEEN 1 AND 100),
            puuid TEXT NOT NULL CHECK(length(puuid) > 0),
            PRIMARY KEY (guild_id, discord_id)
        );
        CREATE TABLE IF NOT EXISTS matches (
            guild_id INTEGER NOT NULL,
            match_id TEXT NOT NULL,
            discord_id INTEGER NOT NULL,
            champion TEXT NOT NULL,
            win INTEGER NOT NULL CHECK(win IN (0, 1)),
            kills INTEGER NOT NULL CHECK(kills >= 0),
            deaths INTEGER NOT NULL CHECK(deaths >= 0),
            assists INTEGER NOT NULL CHECK(assists >= 0),
            damage INTEGER NOT NULL CHECK(damage >= 0),
            played_at INTEGER NOT NULL CHECK(played_at > 0),
            duration INTEGER NOT NULL DEFAULT 0 CHECK(duration >= 0),
            cs INTEGER NOT NULL DEFAULT 0 CHECK(cs >= 0),
            gold INTEGER NOT NULL DEFAULT 0 CHECK(gold >= 0),
            PRIMARY KEY (guild_id, match_id, discord_id),
            FOREIGN KEY (guild_id, discord_id)
                REFERENCES users(guild_id, discord_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS matches_by_user_and_time
            ON matches(guild_id, discord_id, played_at);
        CREATE TABLE IF NOT EXISTS ranks (
            guild_id INTEGER NOT NULL,
            discord_id INTEGER NOT NULL,
            tier TEXT,
            rank TEXT,
            league_points INTEGER,
            updated_at INTEGER NOT NULL CHECK(updated_at > 0),
            PRIMARY KEY (guild_id, discord_id),
            FOREIGN KEY (guild_id, discord_id)
                REFERENCES users(guild_id, discord_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS settings (
            guild_id INTEGER PRIMARY KEY CHECK(guild_id > 0),
            leaderboard_channel_id INTEGER
        );
    """)


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with _database() as db:
        await db.execute("PRAGMA journal_mode = WAL")
        await db.execute("PRAGMA secure_delete = ON")
        async with db.execute("PRAGMA table_info(users)") as cursor:
            columns = {row[1] async for row in cursor}

        if columns and "guild_id" not in columns:
            # Legacy rows have no guild ownership, so retaining them would keep
            # leaking one server's registrations into every other server.
            await db.execute("BEGIN IMMEDIATE")
            try:
                await db.execute("DROP TABLE IF EXISTS matches")
                await db.execute("DROP TABLE IF EXISTS ranks")
                await db.execute("DROP TABLE IF EXISTS users")
                await db.commit()
            except Exception:
                await db.rollback()
                raise

        await _create_schema(db)
        await db.commit()

    os.chmod(DB_PATH, 0o600)


async def register_user(
    guild_id: int, discord_id: int, game_name: str, tag_line: str, puuid: str
) -> None:
    async with _database() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN IMMEDIATE")
        try:
            async with db.execute(
                "SELECT puuid FROM users WHERE guild_id = ? AND discord_id = ?",
                (guild_id, discord_id),
            ) as cursor:
                existing = await cursor.fetchone()
            if existing and existing["puuid"] != puuid:
                await db.execute(
                    "DELETE FROM matches WHERE guild_id = ? AND discord_id = ?",
                    (guild_id, discord_id),
                )
                await db.execute(
                    "DELETE FROM ranks WHERE guild_id = ? AND discord_id = ?",
                    (guild_id, discord_id),
                )
            await db.execute(
                """
                INSERT INTO users (guild_id, discord_id, game_name, tag_line, puuid)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, discord_id) DO UPDATE SET
                    game_name = excluded.game_name,
                    tag_line = excluded.tag_line,
                    puuid = excluded.puuid
                """,
                (guild_id, discord_id, game_name, tag_line, puuid),
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def get_registered_user(guild_id: int, discord_id: int) -> dict | None:
    async with _database() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE guild_id = ? AND discord_id = ?",
            (guild_id, discord_id),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_all_registered_users(guild_id: int) -> list[dict]:
    async with _database() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


async def save_match(
    guild_id: int, discord_id: int, puuid: str, match_id: str, champion: str,
    win: bool, kills: int, deaths: int, assists: int, damage: int, played_at: int,
    duration: int = 0, cs: int = 0, gold: int = 0,
) -> bool:
    async with _database() as db:
        cursor = await db.execute(
            """
            INSERT OR IGNORE INTO matches
                (guild_id, match_id, discord_id, champion, win, kills, deaths, assists,
                 damage, played_at, duration, cs, gold)
            SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            WHERE EXISTS (
                SELECT 1 FROM users
                WHERE guild_id = ? AND discord_id = ? AND puuid = ?
            )
            """,
            (guild_id, match_id, discord_id, champion, int(win), kills, deaths,
             assists, damage, played_at, duration, cs, gold,
             guild_id, discord_id, puuid),
        )
        await db.commit()
        return cursor.rowcount == 1


async def delete_old_matches(guild_id: int, before_timestamp: int) -> None:
    async with _database() as db:
        await db.execute(
            "DELETE FROM matches WHERE guild_id = ? AND played_at < ?",
            (guild_id, before_timestamp),
        )
        await db.commit()


async def get_recent_matches(
    guild_id: int, discord_id: int, since_timestamp: int
) -> list[dict]:
    async with _database() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM matches
            WHERE guild_id = ? AND discord_id = ? AND played_at >= ?
            """,
            (guild_id, discord_id, since_timestamp),
        ) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


async def get_all_recent_matches(guild_id: int, since_timestamp: int) -> list[dict]:
    async with _database() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT matches.*, users.game_name, users.tag_line
            FROM matches
            JOIN users ON matches.guild_id = users.guild_id
                AND matches.discord_id = users.discord_id
            WHERE matches.guild_id = ? AND matches.played_at >= ?
            """,
            (guild_id, since_timestamp),
        ) as cursor:
            return [dict(row) for row in await cursor.fetchall()]


async def save_rank(
    guild_id: int, discord_id: int, puuid: str, tier: str | None,
    rank: str | None, league_points: int | None, updated_at: int,
) -> None:
    async with _database() as db:
        await db.execute(
            """
            INSERT INTO ranks
                (guild_id, discord_id, tier, rank, league_points, updated_at)
            SELECT ?, ?, ?, ?, ?, ?
            WHERE EXISTS (
                SELECT 1 FROM users
                WHERE guild_id = ? AND discord_id = ? AND puuid = ?
            )
            ON CONFLICT(guild_id, discord_id) DO UPDATE SET
                tier = excluded.tier,
                rank = excluded.rank,
                league_points = excluded.league_points,
                updated_at = excluded.updated_at
            """,
            (guild_id, discord_id, tier, rank, league_points, updated_at,
             guild_id, discord_id, puuid),
        )
        await db.commit()


async def get_rank(guild_id: int, discord_id: int) -> dict | None:
    async with _database() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM ranks WHERE guild_id = ? AND discord_id = ?",
            (guild_id, discord_id),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def set_leaderboard_channel(guild_id: int, channel_id: int) -> None:
    async with _database() as db:
        await db.execute(
            """
            INSERT INTO settings (guild_id, leaderboard_channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                leaderboard_channel_id = excluded.leaderboard_channel_id
            """,
            (guild_id, channel_id),
        )
        await db.commit()


async def get_leaderboard_channel(guild_id: int) -> int | None:
    async with _database() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT leaderboard_channel_id FROM settings WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row["leaderboard_channel_id"] if row else None
