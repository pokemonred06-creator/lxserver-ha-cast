# Architecture

The Python integration owns authenticated lxserver HTTP requests, queue state, native media browsing, buttons and configuration flows. A bundled web component is registered using Home Assistant's `panel_custom` API at `/lx-music`.

The panel uses Home Assistant's authenticated WebSocket connection. Its command is administrator-restricted. Search and playlist responses expose presentation metadata and bounded opaque track references, never passwords, account tokens or stream grants. Explicit play requests resolve those references on the backend.

Home Assistant's standard media-player services implement transport controls. A serialized queue owns per-track grants; entry unload revokes the current grant. Stale async resolutions cannot issue playback after release.

Frontend assets are served from the integration package. HACS installs all files together. Home Assistant 2026.10+ is required for the validated panel and WebSocket APIs. No additional frontend repository or build step is required.
