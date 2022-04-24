from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from red_commons.logging import getLogger

from pylav.exceptions import EntryNotFoundError
from pylav.sql.models import QueryModel
from pylav.sql.tables import PlaylistRow, QueryRow
from pylav.utils import AsyncIter

if TYPE_CHECKING:
    from pylav.client import Client
    from pylav.query import Query

LOGGER = getLogger("red.PyLink.LibConfigManager")


class QueryCacheManager:
    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        return self._client

    @staticmethod
    async def get_query(query: Query) -> QueryModel | None:
        if query.is_local or query.is_single or query.is_http:
            # Do not cache local queries and single track urls or http source entries
            return None
        query = (
            await QueryRow.select()
            .output(as_json=True)
            .where(
                (QueryRow.identifier == query.query_identifier)
                & (
                    QueryRow.last_updated
                    > datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=30)
                )
            )
            .first()
        )
        if query:
            return QueryModel(**query)

    @staticmethod
    async def add_query(query: Query, result: dict):
        if query.is_local or query.is_single or query.is_http:
            # Do not cache local queries and single track urls or http source entries
            return
        if result.get("loadType") in ["NO_MATCHES", "LOAD_FAILED", None]:
            return

        tracks = result.get("tracks", [])
        if not tracks:
            raise EntryNotFoundError(f"No tracks found for query {query.query_identifier}")
        name = result.get("playlistInfo", {}).get("name", None)
        await QueryModel(
            identifier=query.query_identifier,
            name=name,
            tracks=[t["track"] async for t in AsyncIter(tracks)],
            last_updated=datetime.datetime.now(tz=datetime.timezone.utc),
        ).save()

    @staticmethod
    async def delete_query(playlist_id: int) -> None:
        await PlaylistRow.delete().where(PlaylistRow.id == playlist_id)

    @staticmethod
    async def delete_old() -> None:
        await QueryRow.delete().where(
            QueryRow.last_updated <= datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=30)
        )