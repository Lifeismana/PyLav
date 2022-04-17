from __future__ import annotations

import pathlib
import re
from typing import Literal

from discord.ext import commands

CLYPIT_REGEX = re.compile(r"(http://|https://(www.)?)?clyp\.it/(.*)")
GETYARN_REGEX = re.compile(r"(?:http://|https://(?:www.)?)?getyarn.io/yarn-clip/(.*)")
MIXCLOUD_REGEX = re.compile(
    r"https?://(?:(?:www|beta|m)\.)?mixcloud.com/([^/]+)/(?!stream|uploads|favorites|listens|playlists)([^/]+)/?"
)
OCRREMIX_PATTERN = re.compile(r"(?:https?://(?:www\.)?ocremix\.org/remix/)?(?P<id>OCR\d+)(?:.*)?")
PORNHUB_REGEX = re.compile(r"^https?://([a-z]+.)?pornhub\.(com|net)/view_video\.php\?viewkey=([a-zA-Z\d]+).*$")
REDDIT_REGEX = re.compile(
    r"https://(?:www|old)\.reddit\.com/"
    r"r/[^/]+/[^/]+/([^/]+)"
    r"(?:/?(?:[^/]+)?/?)?|"
    r"https://v\.redd\.it/([^/]+)(?:.*)?"
)
SOUNDGASM_REGEX = re.compile(r"https?://soundgasm\.net/u/(?P<path>(?P<author>[^/]+)/[^/]+)")
TIKTOK_REGEX = re.compile(r"^https://(?:www\.|m\.)?tiktok\.com/@(?P<user>[^/]+)/video/(?P<video>\d+).*$")


SPOTIFY_REGEX = re.compile(
    r"(https?://)?(www\.)?open\.spotify\.com/(user/[a-zA-Z\d\\-_]+/)?"
    r"(?P<type>track|album|playlist|artist)/"
    r"(?P<identifier>[a-zA-Z\d\\-_]+)"
)

APPLE_MUSIC_REGEX = re.compile(
    r"(https?://)?(www\.)?music\.apple\.com/"
    r"(?P<countrycode>[a-zA-Z]{2}/)?"
    r"(?P<type>album|playlist|artist)(/[a-zA-Z\d\\-]+)?/"
    r"(?P<identifier>[a-zA-Z\d.]+)"
    r"(\?i=(?P<identifier2>\d+))?"
)

BANDCAMP_REGEX = re.compile(r"^(https?://(?:[^.]+\.|)bandcamp\.com)/(track|album)/([a-zA-Z\d\\-_]+)/?(?:\?.*|)$")
NICONICO_REGEX = re.compile(r"(?:http://|https://|)(?:www\.|)nicovideo\.jp/watch/(sm\d+)(?:\?.*|)$")
TWITCH_REGEX = re.compile(r"^https://(?:www\.|go\.)?twitch\.tv/([^/]+)$")
VIMEO_REGEX = re.compile(r"^https://vimeo.com/\d+(?:\?.*|)$")

SOUND_CLOUD_REGEX = re.compile(
    r"^(?:http://|https://|)soundcloud\.app\.goo\.gl/([a-zA-Z\d\\-_]+)/?(?:\?.*|)$|"
    r"^(?:http://|https://|)(?:www\.|)(?:m\.|)soundcloud\.com/([a-zA-Z\d\\-_]+)/([a-zA-Z\d\\-_]+)/?(?:\?.*|)$|"
    r"^(?:http://|https://|)(?:www\.|)(?:m\.|)soundcloud\.com/([a-zA-Z\d\\-_]+)/"
    r"([a-zA-Z\d\\-_]+)/s-([a-zA-Z\d\\-_]+)(?:\?.*|)$|"
    r"^(?:http://|https://|)(?:www\.|)(?:m\.|)soundcloud\.com/([a-zA-Z\d\\-_]+)/likes/?(?:\?.*|)$"
)

YOUTUBE_REGEX = re.compile(r"(?:http://|https://|)(?:www\.|)(?P<music>music\.)?youtu(be\.com|\.be)")
TTS_REGEX = re.compile(r"^(speak|tts):(.*)$")
GCTSS_REGEX = re.compile(r"^(tts://)(.*)$")
SEARCH_REGEX = re.compile(r"^(?P<source>yt|ytm|sp|sc|am)search:(.*)$")
HTTP_REGEX = re.compile(r"^http(s)?://")

YOUTUBE_TIMESTAMP = re.compile(r"[&|?]t=(\d+)s?")
YOUTUBE_INDEX = re.compile(r"&index=(\d+)")
SPOTIFY_TIMESTAMP = re.compile(r"#(\d+):(\d+)")
SOUNDCLOUD_TIMESTAMP = re.compile(r"#t=(\d+):(\d+)s?")
TWITCH_TIMESTAMP = re.compile(r"\?t=(\d+)h(\d+)m(\d+)s")


def process_youtube(cls: type[Query], query: str):
    index = 0
    if match := re.search(YOUTUBE_TIMESTAMP, query):
        start_time = int(match.group(1))
    else:
        start_time = 0
    _has_index = "&index=" in query
    if _has_index and (match := re.search(YOUTUBE_INDEX, query)):
        index = int(match.group(1)) - 1
    if all(k in query for k in ["&list=", "watch?"]):
        query_type = "playlist"
        index = 0
    elif all(x in query for x in ["playlist?"]):
        query_type = "playlist"
    elif any(k in query for k in ["list="]):
        index = 0
        query_type = "single" if _has_index else "playlist"
    else:
        query_type = "single"
    return cls(query, "youtube", start_time=start_time, query_type=query_type, index=index)  # type: ignore


def process_spotify(cls: type[Query], query: str) -> Query:
    query_type = "single"
    if "/playlist/" in query:
        query_type = "playlist"
    elif "/album/" in query:
        query_type = "album"
    return cls(query, "spotify", query_type=query_type)  # type: ignore


def process_soundcloud(cls: type[Query], query: str):
    if "/sets/" in query:
        if "?in=" in query:
            query_type = "single"
        else:
            query_type = "playlist"
    else:
        query_type = "single"
    return cls(query, "soundcloud", query_type=query_type)  # type: ignore


def process_bandcamp(cls: type[Query], query: str) -> Query:
    if "/album/" in query:
        query_type = "album"
    else:
        query_type = "single"
    return cls(query, "bandcamp", query_type=query_type)  # type: ignore


class Query:
    def __init__(
        self,
        query: str,
        source: str,
        search: bool = False,
        start_time=0,
        index=0,
        query_type: Literal["single", "playlist", "album"] = None,
    ):
        self._query = query
        self.source = source
        self._search = search
        self.start_time = start_time
        self.index = index
        self._type = query_type

    @property
    def is_clypit(self) -> bool:
        return self.source == "clypit"

    @property
    def is_getyarn(self) -> bool:
        return self.source == "getyarn"

    @property
    def is_mixcloud(self) -> bool:
        return self.source == "mixcloud"

    @property
    def is_ocremix(self) -> bool:
        return self.source == "ocremix"

    @property
    def is_pornhub(self) -> bool:
        return self.source == "pornhub"

    @property
    def is_reddit(self) -> bool:
        return self.source == "reddit"

    @property
    def is_soundgasm(self) -> bool:
        return self.source == "soundgasm"

    @property
    def is_tiktok(self) -> bool:
        return self.source == "tiktok"

    @property
    def is_spotify(self) -> bool:
        return self.source == "spotify"

    @property
    def is_apple_music(self) -> bool:
        return self.source == "applemusic"

    @property
    def is_bandcamp(self) -> bool:
        return self.source == "bandcamp"

    @property
    def is_youtube(self) -> bool:
        return self.source == "youtube"

    @property
    def is_soundcloud(self) -> bool:
        return self.source == "soundcloud"

    @property
    def is_twitch(self) -> bool:
        return self.source == "twitch"

    @property
    def is_http(self) -> bool:
        return self.source == "http"

    @property
    def is_local(self) -> bool:
        return self.source == "local"

    @property
    def is_niconico(self) -> bool:
        return self.source == "niconico"

    @property
    def is_vimeo(self) -> bool:
        return self.source == "vimeo"

    @property
    def is_search(self) -> bool:
        return self._search

    @property
    def is_album(self) -> bool:
        return self._type == "album"

    @property
    def is_playlist(self) -> bool:
        return self._type == "playlist"

    @property
    def is_single(self) -> bool:
        return self._type == "single"

    @property
    def is_tts(self) -> bool:
        return self.source == "tts" or self.is_gctts

    @property
    def is_gctts(self) -> bool:
        return self.source == "gctts"

    @property
    def query_string(self) -> str:
        if self.is_search:
            if self.is_youtube:
                return f"ytmsearch:{self._query}"
            elif self.is_spotify:
                return f"spsearch:{self._query}"
            elif self.is_apple_music:
                return f"amsearch:{self._query}"
            elif self.is_soundcloud:
                return f"scsearch:{self._query}"
            elif self.is_tts:
                if self.is_gctts:
                    return f"tts://{self._query}"
                return f"speak:{self._query}"
            else:
                return f"ytsearch:{self._query}"
        return self._query

    @classmethod
    def __process_urls(cls, query: str) -> Query | None:
        if re.match(YOUTUBE_REGEX, query):
            return process_youtube(cls, query)
        elif re.match(SPOTIFY_REGEX, query):
            return process_spotify(cls, query)
        elif re.match(APPLE_MUSIC_REGEX, query):
            return cls(query, "applemusic")
        elif re.match(SOUND_CLOUD_REGEX, query):
            return process_soundcloud(cls, query)
        elif re.match(TWITCH_REGEX, query):
            return cls(query, "twitch")
        elif re.match(GCTSS_REGEX, query):
            query = query.replace("tts://", "")
            return cls(query, "gctts")
        elif re.match(TTS_REGEX, query):
            query = query.replace("tts:", "").replace("speak:", "")
            return cls(query, "tts", search=True)
        elif re.match(CLYPIT_REGEX, query):
            return cls(query, "clypit")
        elif re.match(GETYARN_REGEX, query):
            return cls(query, "getyarn")
        elif re.match(MIXCLOUD_REGEX, query):
            return cls(query, "mixcloud")
        elif re.match(OCRREMIX_PATTERN, query):
            return cls(query, "ocremix")
        elif re.match(PORNHUB_REGEX, query):
            return cls(query, "pornhub")
        elif re.match(REDDIT_REGEX, query):
            return cls(query, "reddit")
        elif re.match(SOUNDGASM_REGEX, query):
            return cls(query, "soundgasm")
        elif re.match(TIKTOK_REGEX, query):
            return cls(query, "tiktok")
        elif re.match(BANDCAMP_REGEX, query):
            return process_bandcamp(cls, query)
        elif re.match(NICONICO_REGEX, query):
            return cls(query, "niconico")
        elif re.match(VIMEO_REGEX, query):
            return cls(query, "vimeo")
        elif re.match(HTTP_REGEX, query):
            return cls(query, "http")

    @classmethod
    def __process_search(cls, query: str) -> Query | None:
        if match := re.match(SEARCH_REGEX, query):
            if match.group("source") == "ytm":
                return cls(query, "youtube", search=True)
            elif match.group("source") == "sp":
                return cls(query, "spotify", search=True)
            elif match.group("source") == "sc":
                return cls(query, "soundcloud", search=True)
            elif match.group("source") == "am":
                return cls(query, "applemusic", search=True)
            else:
                return cls(query, "youtube", search=True)  # Fallback to YouTube

    @classmethod
    def __process_local(cls, query: str) -> Query | None:
        path = pathlib.Path(query).resolve()
        query_type = "single"
        if path.is_dir():
            query_type = "album"
        if path.exists():
            return cls(str(path.absolute()), "local", query_type=query_type)  # type: ignore
        else:
            raise ValueError

    @classmethod
    def from_query(cls, query: Query | str) -> Query:
        if isinstance(query, Query):
            return query
        elif query is None:
            raise ValueError("Query cannot be None")
        if output := cls.__process_urls(query):
            return output
        elif output := cls.__process_search(query):
            return output
        else:
            try:
                return cls.__process_local(query)
            except Exception:
                return cls(query, "youtube", search=True)  # Fallback to YouTube


class QueryConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> Query:
        return Query.from_query(arg)