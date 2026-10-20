# Architecture

The Python integration owns authenticated lxserver HTTP requests, queue state, native media browsing, buttons and configuration flows. A bundled web component is registered using Home Assistant's `panel_custom` API at `/lx-music`.

The panel uses Home Assistant's authenticated WebSocket connection. Its command is administrator-restricted. Search and playlist responses expose presentation metadata and bounded opaque track references, never passwords, account tokens or stream grants. Explicit play requests resolve those references on the backend.

Home Assistant's standard media-player services implement transport controls. A serialized queue owns per-track grants; entry unload revokes the current grant. Stale async resolutions cannot issue playback after release.

The panel maps artist search to lxserver's `singer` search type and loads `/api/music/artistSongs`; playlist search uses `playlist`. Collection responses normalize `picUrl`/`creator`/`trackCount` into presentation fields. Source capabilities are validated on the backend and returned with status. Artist/playlist rows fetch tracks before enqueueing their bounded opaque references, never submitting arbitrary song URLs.

The `enqueue` WebSocket action validates the entire batch before appending under the player's lock. It sends no receiver commands and does not resolve streams early. Idle queues are staged until native `media_play` calls `play_staged`; existing active queues still resume through the receiver. Late state-advance callbacks cannot start a staged queue. Queue data is in-memory and resets on reload/restart.

Frontend assets are served from the integration package. HACS installs all files together. Home Assistant 2026.10+ is required for the validated panel and WebSocket APIs. No additional frontend repository or build step is required.
