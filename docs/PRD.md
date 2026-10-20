# LX Music Home Assistant Interface

The HACS integration provides server-address, username and password setup; an LX Server media player; device control buttons; and an LX Music sidebar page.

## Acceptance Criteria

- The sidebar has Player, Browse, Queue and Settings views on desktop and mobile.
- Browse supports Songs, Artists and Playlists search, popular playlists and configured favorites. Songs use all five sources; artists use NetEase/QQ; playlist search uses NetEase. Only supported sources appear for each mode.
- Song results provide Play now and Add to queue. Artist and playlist results open into tracks or add their displayed track batch to the queue. A track list also has Add all results to queue.
- Enqueue appends in order without interrupting playback. When idle, tracks wait for Play. Queue capacity is 1000 upcoming tracks; one displayed batch is capped at 200. Artist tracks use the server's hot order; playlist detail currently loads its first page.
- Back restores the previous artist or playlist results. Queue confirmations state how many tracks were actually added; stale references and full queues report an error without partial additions.
- Player offers play/pause, next, stop and volume. Queue lists the current track and upcoming songs.
- Settings opens Home Assistant's integration configuration. Credentials stay in Home Assistant config entries and never appear in frontend responses.
- The library is browsable without an output device. Playback reports an actionable error if no output exists.
- Installation remains one HACS integration. The sidebar is bundled with the integration.
- Verification must not start music or modify the morning automation.

The sidebar is administrator-only, matching its server library and configuration access. Standard entity controls retain Home Assistant's entity permissions.
