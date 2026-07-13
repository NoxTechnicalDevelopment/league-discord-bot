import pytest

from leaguebot import riot_api


class _Response:
    status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def json(self):
        return {"puuid": "puuid"}


class _Session:
    def __init__(self, urls, **_):
        self.urls = urls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    def get(self, url, **_):
        self.urls.append(url)
        return _Response()


@pytest.mark.asyncio
async def test_riot_id_path_segments_are_percent_encoded(monkeypatch):
    urls = []
    monkeypatch.setattr(riot_api.aiohttp, "ClientSession", lambda **kwargs: _Session(urls, **kwargs))

    assert await riot_api.get_puuid("name/../@everyone", "tag/#here") == "puuid"
    assert urls == [
        "https://americas.api.riotgames.com/riot/account/v1/accounts/"
        "by-riot-id/name%2F..%2F%40everyone/tag%2F%23here"
    ]
