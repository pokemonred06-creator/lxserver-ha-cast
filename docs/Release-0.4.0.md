# v0.4.0 - Search Types and Queue

- Search Songs, Artists or Playlists with provider choices supported by lxserver.
- Open artist and playlist results into tracks, then return to the previous results.
- Add individual songs, artist tracks, playlists or all displayed results to the queue.
- Queue additions preserve the current song. Idle additions wait for Play.
- Queue confirmations report actual batch size. Displayed batches are capped at 200 tracks; playlist details use their first server page. The in-memory queue supports 1000 upcoming tracks and resets on integration reload/restart.

Included in the existing HACS integration; no separate frontend package is required. Reload the Home Assistant page after updating.
