"""Queue ownership regressions, without a Home Assistant runtime or receiver."""

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components/lxserver_cast"
pkg = types.ModuleType("_queue_test")
pkg.__path__ = [str(ROOT)]
sys.modules[pkg.__name__] = pkg
core = types.ModuleType("homeassistant.core")
core.Event = object
core.HomeAssistant = object
core.callback = lambda func: func
events = types.ModuleType("homeassistant.helpers.event")
events.async_track_state_change_event = lambda *args: lambda: None
with patch.dict(sys.modules, {"homeassistant.core": core, "homeassistant.helpers.event": events}):
    spec = importlib.util.spec_from_file_location("_queue_test.player", ROOT / "player.py")
    player_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(player_module)


class QueueTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.hass = types.SimpleNamespace(services=types.SimpleNamespace(async_call=AsyncMock()))
        self.client = types.SimpleNamespace(cast_stream=AsyncMock(return_value=("grant", "http://example/media")), revoke_grant=AsyncMock())
        self.player = player_module.CastQueuePlayer(self.hass, self.client, "media_player.output", "128k")

    async def test_stop_detaches_queue_before_receiver_idle(self):
        await self.player.start([{"name": "A"}, {"name": "B"}], shuffle=False, volume=0.1)
        await self.player.stop()
        await self.player._advance()
        self.assertEqual(self.client.cast_stream.await_count, 1)
        self.assertEqual(self.player.snapshot, {"current": None, "upcoming": []})

    async def test_concurrent_skips_are_serialized(self):
        await self.player.start([{"name": "A"}, {"name": "B"}, {"name": "C"}], shuffle=False, volume=0.1)
        await asyncio.gather(self.player.skip(), self.player.skip())
        self.assertEqual(self.player.current_title, "C")
        self.assertEqual(self.client.cast_stream.await_count, 3)

    async def test_unload_during_resolution_revokes_and_does_not_play(self):
        resolving = asyncio.Event()
        finish = asyncio.Event()

        async def resolve(*args):
            resolving.set()
            await finish.wait()
            return "stale", "http://example/media"

        self.client.cast_stream.side_effect = resolve
        task = asyncio.create_task(self.player.start([{"name": "A"}], shuffle=False, volume=0.1))
        await resolving.wait()
        await self.player.release()
        finish.set()
        await task
        self.client.revoke_grant.assert_awaited_once_with("stale")
        services = [call.args[1] for call in self.hass.services.async_call.await_args_list]
        self.assertNotIn("play_media", services)

    async def test_skip_at_end_stops_and_clears(self):
        await self.player.start([{"name": "A"}], shuffle=False, volume=0.1)
        await self.player.skip()
        self.assertIsNone(self.player.current_title)
        self.assertEqual(self.hass.services.async_call.await_args.args[1], "media_stop")

    async def test_previous_restores_previous_track_and_queue(self):
        await self.player.start([{"name": "A"}, {"name": "B"}, {"name": "C"}], shuffle=False, volume=0.1)
        await self.player.skip()
        await self.player.previous()
        self.assertEqual(self.player.current_title, "A")
        self.assertEqual([song["name"] for song in self.player.snapshot["upcoming"]], ["B", "C"])

    async def test_previous_on_first_track_restarts_it(self):
        await self.player.start([{"name": "A"}, {"name": "B"}], shuffle=False, volume=0.1)
        await self.player.previous()
        self.assertEqual(self.player.current_title, "A")
        self.assertEqual([song["name"] for song in self.player.snapshot["upcoming"]], ["B"])
