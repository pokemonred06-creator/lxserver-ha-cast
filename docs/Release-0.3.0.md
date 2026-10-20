# LX Music 0.3.0

Adds a complete dashboard media card, bundled and automatically loaded by the HACS integration.

- Previous, play/pause, next and stop controls.
- Live output volume, mute and playback-position slider.
- Cast output selector with saved selection; changes apply to subsequent playback.
- Player, Browse, Queue and Settings tabs inside the card.
- Visual editor and automatic discovery in the Home Assistant card picker.
- Shared backend and library with the LX Music sidebar.

Add **LX Music** from the dashboard card picker, or use:

```yaml
type: custom:lx-music-card
entity: media_player.lx_server
```

Restart Home Assistant after updating, then refresh the frontend.
