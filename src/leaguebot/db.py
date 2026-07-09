# SQLite-backed storage for Discord user -> Riot account mappings. Used by /register and any command that accepts @user instead of a raw Riot ID.
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "bot.db"


async def init_db() -> None:
    DB_PATH.parent.mkdir(exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                discord_id INTEGER PRIMARY KEY,
                game_name TEXT NOT NULL,
                tag_line TEXT NOT NULL,
                puuid TEXT NOT NULL
            )
        """)
        await db.commit()


async def register_user(discord_id: int, game_name: str, tag_line: str, puuid: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (discord_id, game_name, tag_line, puuid)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET
                game_name = excluded.game_name,
                tag_line = excluded.tag_line,
                puuid = excluded.puuid
            """,
            (discord_id, game_name, tag_line, puuid),
        )
        await db.commit()


async def get_registered_user(discord_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None