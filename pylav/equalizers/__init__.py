from __future__ import annotations

import asyncio
import datetime
import pathlib
from typing import TYPE_CHECKING

import ujson
from sqlalchemy import and_, event, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from pylav._config import CONFIG_DIR
from pylav.equalizers.models import Base, EqualizerDBEntry

if TYPE_CHECKING:
    from pylav.client import Client


class EqualizerManager:
    def __init__(self, client: Client, config_folder: pathlib.Path = CONFIG_DIR, sql_connection_string: str = None):
        __database_folder: pathlib.Path = config_folder
        __default_db_name: pathlib.Path = __database_folder / "equalizers.db"
        if not sql_connection_string or "sqlite+aiosqlite:///" in sql_connection_string:
            sql_connection_string = f"sqlite+aiosqlite:///{__default_db_name}"
        if "sqlite" in sql_connection_string:
            from sqlalchemy.dialects.sqlite import Insert

            self._insert = Insert
        else:
            from sqlalchemy.dialects.postgresql import Insert

            self._insert = Insert
        self._engine = create_async_engine(
            sql_connection_string, json_deserializer=ujson.loads, json_serializer=ujson.dumps
        )
        self._client = client
        self._session = sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)
        event.listen(self._engine.sync_engine, "connect", self.on_db_connect)
        event.listen(EqualizerDBEntry.band_25, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_40, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_63, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_100, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_160, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_200, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_250, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_400, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_630, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_1000, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_1600, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_2500, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_4000, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_6300, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_10000, "set", EqualizerDBEntry.before_set_band)
        event.listen(EqualizerDBEntry.band_16000, "set", EqualizerDBEntry.before_set_band)

    @staticmethod
    def on_db_connect(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA temp_store=2")
        cursor.execute("PRAGMA read_uncommitted=1")
        cursor.execute("PRAGMA optimize")
        cursor.close()

    async def init(self):
        await self.create_tables()

    @property
    def client(self) -> Client:
        return self._client

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def session(self) -> AsyncSession:
        return self._session()

    async def close(self):
        self._engine.dispose()

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.commit()

    async def _create_built_ins(self, bot_id: int):
        eq_list = [
            dict(
                name="Default",
                description="Default (no equalizer)",
                scope=1,
                scope_id=bot_id,
                author=bot_id,
                id=1,
                band_25=0.0,
                band_40=0.0,
                band_63=0.0,
                band_100=0.0,
                band_160=0.0,
                band_250=0.0,
                band_400=0.0,
                band_630=0.0,
                band_1000=0.0,
                band_1600=0.0,
                band_2500=0.0,
                band_4000=0.0,
                band_6300=0.0,
                band_10000=0.0,
                band_16000=0.0,
            ),
            dict(
                name="Boost",
                description=(
                    "This equalizer emphasizes Punchy Bass and Crisp Mid-High tones. "
                    "Not suitable for tracks with Deep/Low Bass."
                ),
                scope=1,
                scope_id=bot_id,
                author=bot_id,
                id=2,
                band_25=-0.075,
                band_40=0.125,
                band_63=0.125,
                band_100=0.1,
                band_160=0.1,
                band_250=0.05,
                band_400=0.075,
                band_630=0.0,
                band_1000=0.0,
                band_1600=0.0,
                band_2500=0.0,
                band_4000=0.0,
                band_6300=0.125,
                band_10000=0.15,
                band_16000=0.05,
            ),
            dict(
                name="Metal/Rock",
                description="Experimental Metal/Rock Equalizer. Expect clipping on Bassy songs.",
                scope=1,
                scope_id=bot_id,
                author=bot_id,
                id=3,
                band_25=0.0,
                band_40=0.1,
                band_63=0.1,
                band_100=0.15,
                band_160=0.13,
                band_250=0.1,
                band_400=0.0,
                band_630=0.125,
                band_1000=0.175,
                band_1600=0.175,
                band_2500=0.125,
                band_4000=0.125,
                band_6300=0.1,
                band_10000=0.075,
                band_16000=0.0,
            ),
            dict(
                name="Piano",
                description=(
                    "Suitable for Piano tracks, or tracks with an emphasis on Female Vocals. "
                    "Could also be used as a Bass Cutoff."
                ),
                scope=1,
                scope_id=bot_id,
                author=bot_id,
                id=4,
                band_25=-0.25,
                band_40=-0.25,
                band_63=-0.125,
                band_100=0.0,
                band_160=0.25,
                band_250=0.25,
                band_400=0.0,
                band_630=-0.25,
                band_1000=-0.25,
                band_1600=0.0,
                band_2500=0.0,
                band_4000=0.5,
                band_6300=0.25,
                band_10000=-0.025,
                band_16000=0.0,
            ),
            dict(
                name="Nightcore",
                description="Experimental to be used with the Nightcore preset.",
                scope=1,
                scope_id=bot_id,
                author=bot_id,
                id=4,
                band_25=-0.075,
                band_40=0.125,
                band_63=0.125,
                band_100=0.0,
                band_160=0.0,
                band_250=0.0,
                band_400=0.0,
                band_630=0.0,
                band_1000=-0.0,
                band_1600=0.0,
                band_2500=0.0,
                band_4000=0.0,
                band_6300=0.0,
                band_10000=0.0,
                band_16000=0.0,
            ),
            dict(
                name="Vaporwave",
                description="Experimental to be used with the Vaporwave preset.",
                scope=1,
                scope_id=bot_id,
                author=bot_id,
                id=6,
                band_25=-0.075,
                band_40=0.125,
                band_63=0.125,
                band_100=0.0,
                band_160=0.0,
                band_250=0.0,
                band_400=0.0,
                band_630=0.0,
                band_1000=-0.0,
                band_1600=0.0,
                band_2500=0.0,
                band_4000=0.0,
                band_6300=0.0,
                band_10000=0.0,
                band_16000=0.0,
            ),
            dict(
                name="Synth",
                description="Experimental to be used with the Synth preset.",
                scope=1,
                scope_id=bot_id,
                author=bot_id,
                id=7,
                band_25=-0.075,
                band_40=0.325,
                band_63=0.325,
                band_100=0.0,
                band_160=0.25,
                band_250=0.25,
                band_400=0.0,
                band_630=-0.35,
                band_1000=-0.35,
                band_1600=0.0,
                band_2500=0.0,
                band_4000=0.8,
                band_6300=0.45,
                band_10000=-0.025,
                band_16000=0.0,
            ),
        ]

        await self.upsert_equalizers(eq_list)

    async def upsert_equalizers(self, equalizers: list[dict[str, float | str | int | None]]):
        async with self.session as session:
            async with session.begin():
                equalizer_values = equalizers
                equalizer_op = await asyncio.to_thread(insert(EqualizerDBEntry).values, equalizer_values)
                equalizer_update_values = {c.name: c for c in equalizer_op.excluded if not c.primary_key}
                equalizer_update_values["last_updated"] = datetime.datetime.utcnow()
                equalizer_on_conflict = equalizer_op.on_conflict_do_update(
                    index_elements=["id"],
                    set_=equalizer_update_values,
                )
                await session.execute(equalizer_on_conflict)

    async def get_equalizer(
        self,
        eq_name: str | None = None,
        eq_id: int | None = None,
        scope: int | None = None,
        scope_int: int | None = None,
    ) -> list[dict]:
        filter_list = []
        if eq_id is not None:
            filter_list.append(EqualizerDBEntry.id == eq_id)
        if eq_name is not None:
            filter_list.append(EqualizerDBEntry.name == eq_name)
        if scope is not None:
            filter_list.append(EqualizerDBEntry.scope == scope)
        if scope_int is not None:
            filter_list.append(EqualizerDBEntry.scope_id == scope_int)
        if not filter_list:
            query = select(EqualizerDBEntry)
        else:
            query = select(EqualizerDBEntry).where(and_(*filter_list))
        async with self.session as session:
            result = await session.execute(query)
            result = result.scalars().all()
            if result:
                return [row.as_dict() for row in result]
        return []