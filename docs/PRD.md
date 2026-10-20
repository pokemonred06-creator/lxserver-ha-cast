# LX Music Home Assistant Interface

The HACS integration provides server-address, username and password setup; an LX Server media player; device control buttons; and an LX Music sidebar page.

## Acceptance Criteria

- The sidebar has Player, Browse, Queue and Settings views on desktop and mobile.
- Browse supports song search, popular playlists and configured favorites. Results display title and artist with explicit play buttons.
- Player offers play/pause, next, stop and volume. Queue lists the current track and upcoming songs.
- Settings opens Home Assistant's integration configuration. Credentials stay in Home Assistant config entries and never appear in frontend responses.
- The library is browsable without an output device. Playback reports an actionable error if no output exists.
- Installation remains one HACS integration. The sidebar is bundled with the integration.
- Verification must not start music or modify the morning automation.

The sidebar is administrator-only, matching its server library and configuration access. Standard entity controls retain Home Assistant's entity permissions.
