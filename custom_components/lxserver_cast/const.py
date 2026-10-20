"""Constants for the LX Server Cast integration."""

DOMAIN = "lxserver_cast"

CONF_URL = "url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_TARGET = "target"
CONF_VOLUME = "volume"
CONF_QUALITY = "quality"

DEFAULT_VOLUME = 0.3
DEFAULT_QUALITY = "128k"
DEFAULT_SEARCH_SOURCE = "kw"
QUALITY_OPTIONS = ["128k", "320k", "flac"]
CONF_FAVORITES = "favorites"
DEFAULT_FAVORITES = ""
BROWSE_SOURCE = "wy"
MAX_PLAYLIST_TRACKS = 200

SERVICE_PLAY_SONGLIST = "play_songlist"
SERVICE_PLAY_TRACKS = "play_tracks"
SERVICE_STOP = "stop"

ATTR_SOURCE = "source"
ATTR_LIST_ID = "list_id"
ATTR_QUERIES = "queries"
ATTR_SEARCH_SOURCE = "search_source"
ATTR_TARGET = "target"
ATTR_VOLUME = "volume"
ATTR_SHUFFLE = "shuffle"
ATTR_LIMIT = "limit"
