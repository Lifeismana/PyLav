from __future__ import annotations

from typing import TYPE_CHECKING, Any

import aiohttp
import ujson

from pylav.events import Event
from pylav.exceptions import Unauthorized
from pylav.player import Player
from pylav.websocket import WebSocket

if TYPE_CHECKING:
    from pylav.node_manager import NodeManager


class Penalty:
    """
    Represents the penalty of the stats of a Node.
    Attributes
    ----------
    player_penalty: :class:`int`
    cpu_penalty: :class:`int`
    null_frame_penalty: :class:`int`
    deficit_frame_penalty: :class:`int`
    total: :class:`int`
    """

    __slots__ = (
        "player_penalty",
        "cpu_penalty",
        "null_frame_penalty",
        "deficit_frame_penalty",
        "total",
    )

    def __init__(self, stats):
        self.player_penalty = stats.playing_players
        self.cpu_penalty = 1.05 ** (100 * stats.system_load) * 10 - 10
        self.null_frame_penalty = 0
        self.deficit_frame_penalty = 0

        if stats.frames_nulled != -1:
            self.null_frame_penalty = (1.03 ** (500 * (stats.frames_nulled / 3000))) * 300 - 300
            self.null_frame_penalty *= 2

        if stats.frames_deficit != -1:
            self.deficit_frame_penalty = (1.03 ** (500 * (stats.frames_deficit / 3000))) * 600 - 600

        self.total = self.player_penalty + self.cpu_penalty + self.null_frame_penalty + self.deficit_frame_penalty


class Stats:
    """
    Represents the stats of Lavalink node.
    Attributes
    ----------
    uptime: :class:`int`
        How long the node has been running for in milliseconds.
    players: :class:`int`
        The amount of players connected to the node.
    playing_players: :class:`int`
        The amount of players that are playing in the node.
    memory_free: :class:`int`
        The amount of memory free to the node.
    memory_used: :class:`int`
        The amount of memory that is used by the node.
    memory_allocated: :class:`int`
        The amount of memory allocated to the node.
    memory_reservable: :class:`int`
        The amount of memory reservable to the node.
    cpu_cores: :class:`int`
        The amount of cpu cores the system of the node has.
    system_load: :class:`int`
        The overall CPU load of the system.
    lavalink_load: :class:`int`
        The CPU load generated by Lavalink.
    frames_sent: :class:`int`
        The number of frames sent to Discord.
        Warning
        -------
        Given that audio packets are sent via UDP, this number may not be 100% accurate due to dropped packets.
    frames_nulled: :class:`int`
        The number of frames that yielded null, rather than actual data.
    frames_deficit: :class:`int`
        The number of missing frames. Lavalink generates this figure by calculating how many packets to expect
        per minute, and deducting ``frames_sent``. Deficit frames could mean the CPU is overloaded, and isn't
        generating frames as quickly as it should be.
    penalty: :class:`Penalty`
    """

    __slots__ = (
        "_node",
        "uptime",
        "players",
        "playing_players",
        "memory_free",
        "memory_used",
        "memory_allocated",
        "memory_reservable",
        "cpu_cores",
        "system_load",
        "lavalink_load",
        "frames_sent",
        "frames_nulled",
        "frames_deficit",
        "penalty",
    )

    def __init__(self, node, data):
        self._node = node

        self.uptime = data["uptime"]

        self.players = data["players"]
        self.playing_players = data["playingPlayers"]

        memory = data["memory"]
        self.memory_free = memory["free"]
        self.memory_used = memory["used"]
        self.memory_allocated = memory["allocated"]
        self.memory_reservable = memory["reservable"]

        cpu = data["cpu"]
        self.cpu_cores = cpu["cores"]
        self.system_load = cpu["systemLoad"]
        self.lavalink_load = cpu["lavalinkLoad"]

        frame_stats = data.get("frameStats", {})
        self.frames_sent = frame_stats.get("sent", -1)
        self.frames_nulled = frame_stats.get("nulled", -1)
        self.frames_deficit = frame_stats.get("deficit", -1)
        self.penalty = Penalty(self)


class Node:
    """
    Represents a Node connection with Lavalink.
    Note
    ----
    Nodes are **NOT** meant to be added manually, but rather with :func:`Client.add_node`.

    Attributes
    ----------
    host: :class:`str`
        The address of the Lavalink node.
    port: Optional[:class:`int`]
        The port to use for websocket and REST connections.
    password: :class:`str`
        The password used for authentication.
    region: :class:`str`
        The region to assign this node to.
    name: :class:`str`
        The name the :class:`Node` is identified by.
    stats: :class:`Stats`
        The statistics of how the :class:`Node` is performing.
    ssl: :class:`bool`
        Whether to use a ssl connection.
    """

    def __init__(
        self,
        manager: NodeManager,
        host: str,
        password: str,
        region: str,
        resume_key: str,
        resume_timeout: int,
        port: int | None = None,
        name: str | None = None,
        reconnect_attempts: int = 3,
        ssl: bool = False,
        search_only: bool = False,
    ):
        self._manager = manager
        self._session = manager.session

        self._ssl = ssl
        if port is None:
            if self._ssl:
                self._port = 443
            else:
                self._port = 80
        else:
            self._port = port
        self._host = host
        self._password = password
        self._region = region
        self._name = name or f"{self.region}-{self.host}:{self.port}"
        self._resume_key = resume_key
        self._resume_timeout = resume_timeout
        self._reconnect_attempts = reconnect_attempts
        self._search_only = search_only

        self._stats = None

        self._ws = WebSocket(
            node=self,
            host=self.host,
            port=self.port,
            password=self.password,
            resume_key=self.resume_key,
            resume_timeout=self.resume_timeout,
            reconnect_attempts=self.reconnect_attempts,
            ssl=self.ssl,
        )

    @property
    def search_only(self) -> bool:
        return self._search_only

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property
    def websocket(self) -> WebSocket:
        """The websocket of the node."""
        return self._ws

    @property
    def node_manager(self) -> NodeManager:
        """The :class:`NodeManager` this node belongs to."""
        return self._manager

    @property
    def port(self) -> int:
        """The port of the node."""
        return self._port

    @property
    def ssl(self) -> bool:
        """Whether the node is using a ssl connection."""
        return self._ssl

    @property
    def connection_protocol(self) -> str:
        """The protocol used for the connection."""
        return "https" if self.ssl else "http"

    @property
    def host(self) -> str:
        """The host of the node."""
        return self._host

    @property
    def region(self) -> str:
        """The region of the node."""
        return self._region

    @property
    def name(self) -> str:
        """The name of the node."""
        return self._name

    @property
    def password(self) -> str:
        """The password of the node."""
        return self._password

    @property
    def resume_key(self) -> str:
        """The resume key of the node."""
        return self._resume_key

    @property
    def resume_timeout(self) -> int:
        """The timeout to use for resuming."""
        return self._resume_timeout

    @property
    def reconnect_attempts(self) -> int:
        """The number of attempts to reconnect to the node."""
        return self._reconnect_attempts

    @property
    def stats(self) -> Stats:
        """The stats of the node."""
        return self._stats

    @stats.setter
    def stats(self, value: Stats) -> None:
        if not isinstance(value, Stats):
            raise TypeError("stats must be of type Stats")
        self._stats = value

    @property
    def available(self) -> bool:
        """Returns whether the node is available for requests."""
        return self._ws.connected

    @property
    def _original_players(self) -> list[Player]:
        """Returns a list of players that were assigned to this node, but were moved due to failover etc."""
        return [p for p in self._manager.client.player_manager.values() if p._original_node == self]

    @property
    def players(self) -> list[Player]:
        """Returns a list of all players on this node."""
        return [p for p in self._manager.client.player_manager.values() if p.node == self]

    @property
    def playing_players(self) -> list[Player]:
        """Returns a list of all players on this node that are playing."""
        return [p for p in self.players if p.is_playing]

    @property
    def connected_players(self) -> list[Player]:
        """Returns a list of all players on this node that are connected."""
        return [p for p in self.players if p.is_connected]

    @property
    def count(self) -> int:
        """Returns the number of players on this node."""
        return len(self.players)

    @property
    def playing_count(self) -> int:
        """Returns the number of players on this node that are playing."""
        return len(self.playing_players)

    @property
    def connected_count(self) -> int:
        """Returns the number of players on this node that are connected."""
        return len(self.connected_players)

    @property
    def penalty(self) -> float:
        """Returns the load-balancing penalty for this node."""
        if not self.available or not self.stats:
            return 9e30

        return self.stats.penalty.total

    async def dispatch_event(self, event: Event) -> None:
        """|coro|
        Dispatches the given event to all registered hooks.
        Parameters
        ----------
        event: :class:`Event`
            The event to dispatch to the hooks.
        """
        await self.node_manager.client._dispatch_event(event)

    async def send(self, **data: Any) -> None:
        """|coro|
        Sends the passed data to the node via the websocket connection.
        Parameters
        ----------
        data: class:`any`
            The dict to send to Lavalink.
        """
        await self.websocket.send(**data)

    def __repr__(self):
        return f"<Node name={self.name} region={self.region} SSL: {self.ssl}>"

    async def get_tracks(self, query: str, first: bool = False) -> list[dict]:
        """|coro|
        Gets all tracks associated with the given query.

        Parameters
        ----------
        query: :class:`str`
            The query to perform a search for.
        first: :class:`bool`
            Whether to return the first result or all results.
        Returns
        -------
        :class:`list` of :class:`dict`
            A dict representing tracks.
        """
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/loadtracks"
        async with self._session.get(
            destination, headers={"Authorization": self.password}, params={"identifier": query}
        ) as res:
            if res.status == 200:
                result = await res.json(loads=ujson.loads)
                if first:
                    return result.get("tracks", [])[0]
                return result
            if res.status == 401 or res.status == 403:
                raise Unauthorized

            return []

    async def decode_track(self, track: str) -> dict | None:
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/decodetrack"
        async with self.session.get(
            destination, headers={"Authorization": self.password}, params={"track": track}
        ) as res:
            if res.status == 200:
                return await res.json(loads=ujson.loads)

            if res.status == 401 or res.status == 403:
                raise Unauthorized

            return None

    async def decode_tracks(self, tracks: list[str]) -> list[dict]:
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/decodetracks"
        async with self.session.get(destination, headers={"Authorization": self.password}, json=tracks) as res:
            if res.status == 200:
                return await res.json(loads=ujson.loads)

            if res.status == 401 or res.status == 403:
                raise Unauthorized
            return []

    async def routeplanner_status(self) -> dict | None:
        """|coro|
        Gets the route-planner status of the target node.

        Returns
        -------
        :class:`dict`
            A dict representing the route-planner information.
        """
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/routeplanner/status"
        async with self._session.get(destination, headers={"Authorization": self.password}) as res:
            if res.status == 200:
                return await res.json(loads=ujson.loads)

            if res.status == 401 or res.status == 403:
                raise Unauthorized
            return None

    async def routeplanner_free_address(self, address: str) -> bool:
        """|coro|
        Gets the route-planner status of the target node.

        Parameters
        ----------
        address: :class:`str`
            The address to free.

        Returns
        -------
        :class:`bool`
            True if the address was freed, False otherwise.
        """
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/route planner/free/address"

        async with self._session.post(
            destination, headers={"Authorization": self.password}, json={"address": address}
        ) as res:
            return res.status == 204

    async def routeplanner_free_all_failing(self) -> bool:
        """|coro|
        Gets the route-planner status of the target node.

        Returns
        -------
        :class:`bool`
            True if all failing addresses were freed, False otherwise.
        """
        destination = f"{self.connection_protocol}://{self.host}:{self.port}/route planner/free/all"

        async with self._session.post(destination, headers={"Authorization": self.password}) as res:
            return res.status == 204
