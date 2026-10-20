# Current Progress

## Complete Dashboard Card - 0.3.0

- [x] Bundle `custom:lx-music-card` and its visual editor in the integration.
- [x] Register frontend module automatically in Home Assistant.
- [x] Add previous/play/pause/next/stop, live volume, mute, seek and Cast output selection.
- [x] Keep Browse, Queue and Settings inside the card using the shared interface.
- [x] Save output selection without reloading the integration or transferring playback.
- [x] Verify standalone card/editor at dashboard and phone widths; nine mocked controls, live search and editor changes pass with no receiver commands.
- [x] Deploy package on HA 2026.10.2; 33 backend tests and JS/Python checks pass.
- [ ] Publish the verified 0.3.0 HACS release.

Preview dashboard: `/lx-music-player/player` (administrator-only, no additional sidebar entry). Backup: `/config/.audit-backups/lxserver-card-20261020-161752`. Live output source list contains four Cast players; the selected RZ50 and morning automation were preserved. Screenshots: `output/playwright/lx-complete-card-desktop.png` and `lx-complete-card-phone.png`.

## Previous Sidebar Release

- [x] HACS integration with login form and native media player.
- [x] Media browser, favorite buttons and device controls.
- [x] Bundled sidebar with Player, Browse, Queue and Settings.
- [x] Authenticated library search and playlist navigation.
- [x] Serialize queue operations and discard stale stream resolutions.
- [x] Complete backend regression checks: 31 tests, Python compilation and JS syntax.
- [x] Back up and deploy the package to Home Assistant; Core check and restart succeeded.
- [x] Verify live sidebar, entities, search and media browsing without playback.
- [x] Live desktop/390px browser: tabs, search, artwork and no horizontal overflow.
- [x] Publish the tested HACS release: v0.2.0, code be9d3e3; HACS and backend/frontend CI passed.

Music selection, receiver changes and the morning automation are deferred at the user's request.

## Deployment Evidence - 20 October 2026

Home Assistant 2026.10.2. Backup: `/config/.audit-backups/lxserver-ui-20261020-153217`.
Authenticated read-only verification passed for the sidebar, 20 search results, a 97-track playlist, native media browsing, both control buttons and frontend delivery. Temporary API login was revoked.
Browser evidence is in ignored `output/playwright/`. No receiver playback was started during verification.
Native Settings navigation and playlist detail/back navigation passed in the live browser. Console: no errors; desktop and 390px layouts verified. Browser rendering does not certify physical phone operation.
