"""Unit tests for the lxserver client, using a scripted transport."""

from __future__ import annotations

import asyncio
import importlib.util
import pathlib
import sys
import unittest
from typing import Any

_PKG = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "lxserver_cast"


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"_lxcast_{name}", _PKG / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lxserver = _load("lxserver")


class ScriptedTransport:
    """Returns queued (status, body) pairs and records every request."""

    def __init__(self, responses: list[tuple[int, Any]]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def request(self, method, path, *, params=None, json=None, headers=None):
        self.calls.append(
            {"method": method, "path": path, "params": params, "json": json, "headers": dict(headers or {})}
        )
        return self._responses.pop(0)


BASE = "http://lx.test:29527"


class LxServerClientTests(unittest.TestCase):
    def test_cast_stream_logs_in_then_returns_absolute_grant_url(self) -> None:
        transport = ScriptedTransport(
            [
                (200, {"token": "tok-1"}),
                (200, {"url": "https://upstream.example/track.mp3"}),
                (200, {"id": "g1", "url": "/api/music/cast/media?id=g1", "expiresAt": 1}),
            ]
        )
        client = lxserver.LxServerClient(transport, BASE, "homeassistant", "pw")
        grant_id, url = asyncio.run(client.cast_stream({"name": "A", "source": "kw"}, "128k"))

        self.assertEqual(grant_id, "g1")
        self.assertEqual(url, f"{BASE}/api/music/cast/media?id=g1")
        self.assertEqual(transport.calls[0]["path"], "/api/user/login")
        self.assertEqual(transport.calls[1]["headers"]["x-user-token"], "tok-1")
        self.assertEqual(transport.calls[2]["json"], {"url": "https://upstream.example/track.mp3", "mime": "audio/mpeg"})

    def test_flac_quality_requests_flac_mime(self) -> None:
        transport = ScriptedTransport(
            [
                (200, {"token": "tok-1"}),
                (200, {"url": "https://upstream.example/track.flac"}),
                (200, {"id": "g2", "url": "/api/music/cast/media?id=g2"}),
            ]
        )
        client = lxserver.LxServerClient(transport, BASE, "homeassistant", "pw")
        asyncio.run(client.cast_stream({"name": "A"}, "flac"))
        self.assertEqual(transport.calls[2]["json"]["mime"], "audio/flac")

    def test_expired_token_triggers_one_relogin_and_retry(self) -> None:
        transport = ScriptedTransport(
            [
                (200, {"token": "tok-1"}),
                (401, {"error": "expired"}),
                (200, {"token": "tok-2"}),
                (200, {"list": [{"name": "A"}]}),
            ]
        )
        client = lxserver.LxServerClient(transport, BASE, "homeassistant", "pw")
        songs = asyncio.run(client.search("mozart"))
        self.assertEqual(songs, [{"name": "A"}])
        self.assertEqual(transport.calls[3]["headers"]["x-user-token"], "tok-2")

    def test_rejected_credentials_raise_auth_error(self) -> None:
        transport = ScriptedTransport([(401, {"success": False})])
        client = lxserver.LxServerClient(transport, BASE, "homeassistant", "wrong")
        with self.assertRaises(lxserver.LxServerAuthError):
            asyncio.run(client.login())

    def test_search_ignores_non_dict_items(self) -> None:
        transport = ScriptedTransport([(200, {"token": "t"}), (200, {"list": [{"name": "A"}, "bad"]})])
        client = lxserver.LxServerClient(transport, BASE, "u", "p")
        self.assertEqual(asyncio.run(client.search("x")), [{"name": "A"}])

    def test_songlist_requests_playlist_id(self) -> None:
        transport = ScriptedTransport([(200, {"token": "t"}), (200, {"list": [{"name": "A"}]})])
        client = lxserver.LxServerClient(transport, BASE, "u", "p")
        asyncio.run(client.songlist_tracks("wy", "123"))
        self.assertEqual(transport.calls[1]["params"]["id"], "123")
        self.assertEqual(transport.calls[1]["params"]["source"], "wy")

    def test_missing_stream_url_raises(self) -> None:
        transport = ScriptedTransport([(200, {"token": "t"}), (500, {"error": "no source"})])
        client = lxserver.LxServerClient(transport, BASE, "u", "p")
        with self.assertRaises(lxserver.LxServerError):
            asyncio.run(client.stream_url({"name": "A"}, "128k"))

    def test_revoke_is_best_effort(self) -> None:
        transport = ScriptedTransport([(200, {"token": "t"}), (404, {"error": "gone"})])
        client = lxserver.LxServerClient(transport, BASE, "u", "p")
        asyncio.run(client.revoke_grant("g1"))
        self.assertEqual(transport.calls[1]["params"], {"id": "g1"})

    def test_popular_playlists_requests_hot_list(self) -> None:
        transport = ScriptedTransport([(200, {"token": "t"}), (200, {"list": [{"id": "1", "name": "A"}]})])
        client = lxserver.LxServerClient(transport, BASE, "u", "p")
        songs = asyncio.run(client.popular_playlists("wy"))
        self.assertEqual(songs, [{"id": "1", "name": "A"}])
        self.assertEqual(transport.calls[1]["path"], "/api/music/songList/list")
        self.assertEqual(transport.calls[1]["params"]["sortId"], "hot")


if __name__ == "__main__":
    unittest.main()
