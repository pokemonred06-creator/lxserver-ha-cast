# LX Server Cast

Home Assistant integration that plays music from an lxserver (LX Music Server) on a Google Cast device, such as an Onkyo TX-RZ50.

## Install with HACS

1. In HACS, open Integrations, then the menu, then Custom repositories.
2. Add `https://github.com/pokemonred06-creator/lxserver-ha-cast` with category Integration.
3. Download LX Server Cast and restart Home Assistant.
4. Go to Settings, Devices and services, Add integration, and choose LX Server Cast.

Before setup, create a dedicated user in the lxserver admin panel and make sure the Cast device appears under Google Cast.

## Using it

Open **LX Music** in the Home Assistant sidebar. The bundled interface includes Player, Browse, Queue and Settings tabs, song search, playlist navigation and playback controls. It follows your Home Assistant theme and works on phones. The sidebar is available to administrators.

- **Media browser:** open the LX Server media player and browse Favorites or Popular playlists. Open a playlist and pick a track to start from there.
- **Player controls:** play, pause, next track, stop, and volume on the LX Server device.
- **Buttons:** Next track, Stop playback, and one button per favorite playlist.
- **Options:** default Cast device, default volume, audio quality, and favorite playlists. Enter favorites one per line as `Name | wy:17879848678`.

## Services

- `lxserver_cast.play_songlist`: queue an online playlist by source and playlist ID.
- `lxserver_cast.play_tracks`: search each query and queue the top match, in order or shuffled.
- `lxserver_cast.stop`: stop playback and release the stream grant.

Each track gets a fresh stream grant when it starts. Grants expire after two hours on the server.

## Tests

    python3 -m unittest discover -s tests -v
