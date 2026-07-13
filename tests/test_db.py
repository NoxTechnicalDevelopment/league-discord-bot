import sqlite3
import time

import pytest

from leaguebot import db


@pytest.fixture
def database_path(monkeypatch, tmp_path):
    path = tmp_path / "bot.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


@pytest.mark.asyncio
async def test_profiles_and_matches_are_isolated_by_guild(database_path):
    await db.init_db()
    await db.register_user(1, 10, "one", "tag", "puuid-one")
    await db.register_user(2, 10, "two", "tag", "puuid-two")

    now = int(time.time())
    assert await db.save_match(
        1, 10, "puuid-one", "match-one", "Ahri", True, 1, 2, 3, 4, now
    )
    assert await db.save_match(
        2, 10, "puuid-two", "match-two", "Annie", False, 5, 6, 7, 8, now
    )

    assert (await db.get_registered_user(1, 10))["game_name"] == "one"
    assert (await db.get_registered_user(2, 10))["game_name"] == "two"
    assert [match["match_id"] for match in await db.get_all_recent_matches(1, now)] == ["match-one"]
    assert [match["match_id"] for match in await db.get_all_recent_matches(2, now)] == ["match-two"]


@pytest.mark.asyncio
async def test_old_sync_cannot_write_after_reregistration(database_path):
    await db.init_db()
    await db.register_user(1, 10, "old", "tag", "old-puuid")
    await db.register_user(1, 10, "new", "tag", "new-puuid")

    now = int(time.time())
    assert not await db.save_match(
        1, 10, "old-puuid", "old-match", "Ahri", True, 1, 2, 3, 4, now
    )
    assert await db.save_match(
        1, 10, "new-puuid", "new-match", "Ahri", True, 1, 2, 3, 4, now
    )
    assert [match["match_id"] for match in await db.get_recent_matches(1, 10, now)] == ["new-match"]


@pytest.mark.asyncio
async def test_duplicate_match_is_not_reported_as_new(database_path):
    await db.init_db()
    await db.register_user(1, 10, "name", "tag", "puuid")
    now = int(time.time())
    args = (1, 10, "puuid", "match", "Ahri", True, 1, 2, 3, 4, now)

    assert await db.save_match(*args)
    assert not await db.save_match(*args)


@pytest.mark.asyncio
async def test_rank_write_requires_the_current_profile(database_path):
    await db.init_db()
    await db.register_user(1, 10, "name", "tag", "current-puuid")
    now = int(time.time())

    await db.save_rank(1, 10, "old-puuid", "GOLD", "I", 50, now)
    assert await db.get_rank(1, 10) is None

    await db.save_rank(1, 10, "current-puuid", "GOLD", "I", 50, now)
    assert (await db.get_rank(1, 10))["league_points"] == 50


@pytest.mark.asyncio
async def test_legacy_unscoped_cache_is_removed(database_path):
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE users (discord_id INTEGER PRIMARY KEY, game_name TEXT, tag_line TEXT, puuid TEXT)"
        )
        connection.execute(
            "INSERT INTO users VALUES (10, 'legacy', 'tag', 'legacy-puuid')"
        )

    await db.init_db()

    assert await db.get_registered_user(1, 10) is None
