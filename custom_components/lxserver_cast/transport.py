"""aiohttp transport used by Home Assistant."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import aiohttp

from .lxserver import LxServerError


class AiohttpTransport:
    def __init__(self, session: aiohttp.ClientSession, base_url: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> tuple[int, Any]:
        try:
            async with self._session.request(
                method,
                f"{self._base_url}{path}",
                params=params,
                json=json,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                try:
                    data: Any = await resp.json(content_type=None)
                except ValueError:
                    data = None
                return resp.status, data
        except (aiohttp.ClientError, TimeoutError) as err:
            raise LxServerError(f"Cannot reach lxserver: {err}") from err
