# LX Server Cast

Home Assistant integration that plays music from an lxserver (LX Music Server) on a Google Cast device, such as an Onkyo TX-RZ50.

## Install with HACS

1. In HACS, open Integrations, then the menu, then Custom repositories.
2. Add `https://github.com/pokemonred06-creator/lxserver-ha-cast` with category Integration.
3. Download LX Server Cast and restart Home Assistant.
4. Go to Settings, Devices and services, Add integration, and choose LX Server Cast.

Before setup, create a dedicated user in the lxserver admin panel, and make sure the Cast device appears under Google Cast.

## Services

- `lxserver_cast.play_songlist`: queue an online playlist by source and playlist ID.
- `lxserver_cast.play_tracks`: search each query and queue the top match, in order or shuffled.
- `lxserver_cast.stop`: stop playback and release the stream grant.

Each track gets a fresh stream grant when it starts. Grants expire after two hours on the server.

## Media player

The integration adds an `LX Server` media player that sends playback to the default Cast device set in the options.

- `media_player.play_media` with `media_content_type: playlist` and `media_content_id: wy:17879848678` (source:playlist ID) queues a playlist.
- `media_player.play_media` with `media_content_type: music` and a search phrase plays the top match.

## Tests

    python3 -m unittest discover -s tests -v
