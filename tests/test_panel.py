"""Panel action routing and opaque references, without a receiver or HA runtime."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components/lxserver_cast"
pkg = types.ModuleType("_panel_test")
pkg.__path__ = [str(ROOT)]
sys.modules[pkg.__name__] = pkg
vol = types.ModuleType("probatio")
for name in ("Required", "Optional", "All", "In", "Length"):
    setattr(vol, name, lambda *args, **kwargs: args[0] if args else None)
components = types.ModuleType("homeassistant.components")
components.frontend = types.SimpleNamespace()
components.panel_custom = types.SimpleNamespace()
components.websocket_api = types.SimpleNamespace(
    websocket_command=lambda schema: lambda fn: fn, require_admin=lambda fn: fn, async_response=lambda fn: fn,
)
http = types.ModuleType("homeassistant.components.http")
http.StaticPathConfig = object
core = types.ModuleType("homeassistant.core")
core.HomeAssistant = object
with patch.dict(sys.modules, {"probatio": vol, "homeassistant.components": components,
                             "homeassistant.components.http": http, "homeassistant.core": core}):
    spec = importlib.util.spec_from_file_location("_panel_test.panel", ROOT / "panel.py")
    panel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(panel)


class PanelTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.player = types.SimpleNamespace(enqueue=AsyncMock(), start=AsyncMock())
        self.client = types.SimpleNamespace(search=AsyncMock(), artist_tracks=AsyncMock(), songlist_tracks=AsyncMock())
        self.runtime = types.SimpleNamespace(client=self.client, ui_tracks={}, default_target="media_player.cast",
                                             default_volume=0.3, player_for=Mock(return_value=self.player))
        self.hass = types.SimpleNamespace(data={"lxserver_cast": {"entry": self.runtime}})
        self.connection = types.SimpleNamespace(send_result=Mock(), send_error=Mock())

    async def command(self, action, **kwargs):
        msg = {"id": 1, "action": action, "query": "Mozart", "source": "wy", "search_type": "song",
               "list_id": "123", "track_id": "", "track_ids": [], **kwargs}
        await panel.handle_panel(self.hass, self.connection, msg)
        if self.connection.send_result.called:
            return self.connection.send_result.call_args.args[1]

    async def test_collection_search_normalizes_and_sanitizes(self):
        self.client.search.return_value = [{"id": 12, "name": "List", "picUrl": "http://img", "creator": "A",
                                           "trackCount": 5, "token": "private"}]
        rows = await self.command("search", search_type="playlist")
        self.assertEqual(rows, [{"id": "12", "source": "wy", "name": "List", "img": "http://img", "author": "A", "total": 5}])
        self.client.search.assert_awaited_once_with("Mozart", source="wy", kind="playlist", limit=20)

    async def test_unsupported_source_returns_actionable_error(self):
        await self.command("search", search_type="artist", source="kw")
        self.assertEqual(self.connection.send_error.call_args.args[1], "unsupported_source")
        self.client.search.assert_not_awaited()

    async def test_artist_tracks_are_bounded_opaque_references(self):
        self.client.artist_tracks.return_value = [{"name": "A", "songmid": 1, "url": "private"}] * 210
        self.runtime.ui_tracks = {str(i): {"name": "old"} for i in range(999)}
        rows = await self.command("artist")
        self.assertEqual(len(rows), 200)
        self.assertEqual(len(self.runtime.ui_tracks), 1000)
        self.assertNotIn("url", rows[0])
        self.assertNotIn("songmid", rows[0])
        self.assertEqual(self.runtime.ui_tracks[rows[0]["track_id"]]["songmid"], 1)

    async def test_enqueue_routes_batch_without_replacing_playback(self):
        self.runtime.ui_tracks = {"a": {"name": "A"}, "b": {"name": "B"}}
        self.assertEqual(await self.command("enqueue", track_ids=["b", "a"]), {"queued": 2})
        self.player.enqueue.assert_awaited_once_with([{"name": "B"}, {"name": "A"}])
        self.player.start.assert_not_awaited()

    async def test_stale_batch_rejected_in_full(self):
        self.runtime.ui_tracks = {"a": {"name": "A"}}
        await self.command("enqueue", track_ids=["a", "missing"])
        self.assertEqual(self.connection.send_error.call_args.args[1], "expired")
        self.player.enqueue.assert_not_awaited()

    async def test_missing_target_does_not_enqueue(self):
        self.runtime.ui_tracks = {"a": {"name": "A"}}
        self.runtime.default_target = None
        await self.command("enqueue", track_id="a")
        self.assertEqual(self.connection.send_error.call_args.args[1], "no_target")
        self.player.enqueue.assert_not_awaited()

    async def test_play_now_keeps_explicit_replacement(self):
        self.runtime.ui_tracks = {"a": {"name": "A"}}
        self.assertEqual(await self.command("play", track_id="a"), {"started": True})
        self.player.start.assert_awaited_once_with([{"name": "A"}], shuffle=False, volume=0.3)

    async def test_queue_full_returns_actionable_error(self):
        self.runtime.ui_tracks = {"a": {"name": "A"}}
        self.player.enqueue.side_effect = panel.LxQueueFullError()
        await self.command("enqueue", track_id="a")
        self.assertEqual(self.connection.send_error.call_args.args[1], "queue_full")
        self.assertIn("1000", self.connection.send_error.call_args.args[2])
