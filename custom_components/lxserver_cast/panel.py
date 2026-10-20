"""Authenticated sidebar interface. Account credentials never reach the frontend."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import probatio as vol

from homeassistant.components import panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .lxserver import LxServerError

ASSET_URL = "/lxserver_cast_frontend"


def _display(song: dict | None) -> dict | None:
    if not song:
        return None
    return {key: song.get(key) for key in ("name", "singer", "img", "interval", "albumName")}


async def async_setup_panel(hass: HomeAssistant) -> None:
    await hass.http.async_register_static_paths(
        [StaticPathConfig(ASSET_URL, str(Path(__file__).parent / "frontend"), False)]
    )
    websocket_api.async_register_command(hass, handle_panel)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path="lx-music",
        webcomponent_name="lx-music-panel",
        sidebar_title="LX Music",
        sidebar_icon="mdi:music-box-multiple",
        module_url=f"{ASSET_URL}/panel.js?v=0.2.0",
        require_admin=True,
        config_panel_domain=DOMAIN,
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "lxserver_cast/panel",
        vol.Required("action"): vol.In(["status", "search", "popular", "playlist", "play"]),
        vol.Optional("entry_id"): str,
        vol.Optional("query", default=""): vol.All(str, vol.Length(max=200)),
        vol.Optional("source", default="wy"): vol.In(["wy", "kw", "tx", "kg", "mg"]),
        vol.Optional("list_id", default=""): vol.All(str, vol.Length(max=256)),
        vol.Optional("track_id", default=""): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def handle_panel(hass, connection, msg) -> None:
    runtimes = hass.data.get(DOMAIN, {})
    entry_id = msg.get("entry_id") or next(iter(runtimes), None)
    runtime = runtimes.get(entry_id)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "LX Server is not loaded")
        return
    try:
        action = msg["action"]
        if action == "status":
            entries = hass.config_entries.async_entries(DOMAIN)
            target = runtime.default_target
            player = runtime.players.get(target)
            snapshot = player.snapshot if player else {"current": None, "upcoming": []}
            result = {
                "entries": [{"entry_id": e.entry_id, "title": e.title} for e in entries],
                "entry_id": entry_id,
                "target": target,
                "quality": runtime.quality,
                "volume": runtime.default_volume,
                "current": _display(snapshot["current"]),
                "upcoming": [_display(s) for s in snapshot["upcoming"]],
                "favorites": [{"name": f.name, "id": f.list_id, "source": f.source} for f in runtime.favorites],
            }
        elif action == "popular":
            items = await runtime.client.popular_playlists(msg["source"])
            result = [{k: s.get(k) for k in ("id", "name", "img", "author", "total")} for s in items]
        elif action in ("search", "playlist"):
            if action == "search":
                if not msg["query"].strip():
                    connection.send_error(msg["id"], "invalid_query", "Enter a search")
                    return
                songs = await runtime.client.search(msg["query"], source=msg["source"], limit=20)
            else:
                songs = await runtime.client.songlist_tracks(msg["source"], msg["list_id"])
            result = []
            for song in songs[:200]:
                key = uuid4().hex
                runtime.ui_tracks[key] = song
                result.append({**_display(song), "track_id": key})
            while len(runtime.ui_tracks) > 1000:
                del runtime.ui_tracks[next(iter(runtime.ui_tracks))]
        else:
            song = runtime.ui_tracks.get(msg["track_id"])
            if song is None:
                connection.send_error(msg["id"], "expired", "Refresh the results and choose the track again")
                return
            if not runtime.default_target:
                connection.send_error(msg["id"], "no_target", "Choose an output in integration settings")
                return
            await runtime.player_for(runtime.default_target).start([song], shuffle=False, volume=runtime.default_volume)
            result = {"started": True}
        connection.send_result(msg["id"], result)
    except LxServerError:
        connection.send_error(msg["id"], "server_error", "LX Server could not complete this request")
