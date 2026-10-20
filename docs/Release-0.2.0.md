# LX Music 0.2.0

- Adds a bundled LX Music sidebar with Player, Browse, Queue and Settings tabs.
- Adds authenticated song search, popular playlist navigation and favorite browsing.
- Adds native next/stop buttons, favorite playlist buttons and media-player controls.
- Fixes queue races during repeated Next requests and entry unload.
- Fixes HACS license/topic validation and adds automated backend/frontend checks.

Tested on Home Assistant 2026.10.2 with 31 backend regression tests, successful HACS validation and live desktop/mobile browser checks. Music playback and the morning automation were not operated during this deployment.

After updating, restart Home Assistant and refresh the frontend. Open **LX Music** in the sidebar. The bundled sidebar is available to administrators.
