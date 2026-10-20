# LX Server Cast

Home Assistant custom integration that plays lxserver tracks on a Google Cast device such as the Onkyo TX-RZ50.

## Setup

1. Create a dedicated user in the lxserver admin panel for Home Assistant.
2. Copy `custom_components/lxserver_cast` into the Home Assistant `custom_components` folder and restart Home Assistant once.
3. Add Google Cast under Settings, Devices and services, so the Cast device appears as a media player.
4. Add LX Server Cast under Settings, Devices and services, and enter the server URL and the dedicated user's credentials.
5. Open the integration options to choose the default Cast device, volume, and audio quality.

## Services

- `lxserver_cast.play_songlist`: queue an online playlist by source and playlist ID.
- `lxserver_cast.play_tracks`: search each query and queue the top match, in order or shuffled.
- `lxserver_cast.stop`: stop playback and release the stream grant.

Each track gets a fresh stream grant when it starts. Grants expire after two hours on the server.

## Tests

    python3 -m unittest discover -s tests -v
