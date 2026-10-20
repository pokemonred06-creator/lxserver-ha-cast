"""Read-only live checks using a temporary trusted-network login, revoked on exit."""

import argparse
import asyncio
import json

import aiohttp


async def verify(base, user_id, preflight):
    client_id = "http://localhost/"
    refresh = None
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async def post(path, payload):
            async with session.post(base + path, json=payload) as response:
                response.raise_for_status()
                return await response.json()

        flow = await post("/auth/login_flow", {"client_id": client_id, "handler": ["trusted_networks", None], "redirect_uri": client_id})
        result = await post("/auth/login_flow/" + flow["flow_id"], {"client_id": client_id, "user": user_id})
        async with session.post(base + "/auth/token", data={"grant_type": "authorization_code", "code": result["result"], "client_id": client_id}) as response:
            response.raise_for_status()
            tokens = await response.json()
        refresh = tokens["refresh_token"]
        try:
            async with session.ws_connect(base + "/api/websocket") as ws:
                await ws.receive_json()
                await ws.send_json({"type": "auth", "access_token": tokens["access_token"]})
                assert (await ws.receive_json())["type"] == "auth_ok"
                sequence = 0

                async def command(kind, **kwargs):
                    nonlocal sequence
                    sequence += 1
                    await ws.send_json({"id": sequence, "type": kind, **kwargs})
                    while True:
                        reply = await ws.receive_json()
                        if reply.get("id") == sequence:
                            assert reply.get("success"), reply.get("error")
                            return reply.get("result")

                states = await command("get_states")
                player = next(s for s in states if s["entity_id"] == "media_player.lx_server")
                print("player:", player["state"], "features:", player["attributes"].get("supported_features"))
                if preflight:
                    return
                panels = await command("get_panels")
                assert "lx-music" in panels, list(panels)
                print("sidebar:", panels["lx-music"].get("title"))
                status = await command("lxserver_cast/panel", action="status")
                assert "current" in status and "upcoming" in status
                print("panel status: OK; favorites:", len(status["favorites"]))
                rows = await command("lxserver_cast/panel", action="search", query="Mozart", source="kw")
                assert rows and rows[0].get("track_id")
                assert all("token" not in r and "url" not in r for r in rows)
                print("search: OK; results:", len(rows))
                popular = await command("lxserver_cast/panel", action="popular", source="wy")
                assert popular
                tracks = await command("lxserver_cast/panel", action="playlist", source="wy", list_id=str(popular[0]["id"]))
                assert tracks
                print("playlist navigation: OK; tracks:", len(tracks))
                browser = await command("media_player/browse_media", entity_id="media_player.lx_server")
                assert browser.get("children")
                print("native media browser: OK")
                buttons = [s["entity_id"] for s in states if s["entity_id"].startswith("button.lx_server")]
                assert len(buttons) >= 2, buttons
                print("buttons:", json.dumps(buttons))
                async with session.get(base + "/lxserver_cast_frontend/panel.js") as response:
                    assert response.status == 200
                    assert "class LxMusicPanel" in await response.text()
                print("frontend asset: OK")
        finally:
            if refresh:
                async with session.post(base + "/auth/revoke", data={"token": refresh}) as response:
                    assert response.status == 200
                print("temporary login: revoked")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    asyncio.run(verify(args.base.rstrip("/"), args.user_id, args.preflight))
