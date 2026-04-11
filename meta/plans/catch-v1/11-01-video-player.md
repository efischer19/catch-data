# feat: Implement browser-native video player for condensed games

## What do you want to build?

Build a video player component that plays MLB condensed game highlight videos
directly in the browser. The player receives a raw `.mp4` URL from the Gold
data and plays it using the browser's native `<video>` element. This is the
default playback experience for users who are not casting to a Chromecast.

## Acceptance Criteria

- [ ] A video player component accepts a `condensed_game_url` (string) prop and renders a `<video>` element
- [ ] The player uses the native HTML5 `<video>` element with standard controls (play, pause, seek, volume, fullscreen)
- [ ] The player displays a loading indicator while the video is buffering
- [ ] If the video URL is invalid or fails to load, a user-friendly error message is displayed
- [ ] The player includes a "Cast" button that opens the Google Cast flow (implemented in ticket 11-02)
- [ ] The player can be closed/dismissed to return to the schedule/boxscore view
- [ ] The video player renders in a modal/overlay, not a new page
- [ ] The player is responsive: full-width on mobile, centered with max-width on desktop
- [ ] Keyboard controls: Space to play/pause, arrow keys to seek, Escape to close
- [ ] Video playback does not auto-start (user must click play)

## Implementation Notes

**📺 Living Room Tester notes:**

- The `.mp4` URLs come from MLB's CDN. These are typically 720p or 1080p
  condensed game recaps, 5-15 minutes long, 50-200 MB.
- **Cross-origin concerns:** The video URLs are on MLB's domain, not ours.
  CORS may block `<video>` playback in some browsers. Test with actual URLs.
  If blocked, the frontend may need to link to the video instead of embedding
  it.
- The native `<video>` element is the simplest and most compatible player.
  Avoid third-party player libraries unless `<video>` proves insufficient.
- Test on: Chrome, Firefox, Safari (desktop and mobile), and Chrome on Android
  TV (for Cast-adjacent scenarios).

**♿ Accessibility Coordinator notes:**

- The `<video>` element should have: `aria-label` describing the content
  (e.g., "Condensed game: Yankees vs Red Sox, July 10"), keyboard-accessible
  controls.
- Native `<video>` controls are generally accessible. Do not build custom
  controls unless necessary (custom controls often break accessibility).
- The modal/overlay must trap focus: Tab should cycle within the player, not
  reach background content. Escape should close the player.
- Announce modal open/close to screen readers via `role="dialog"` and
  `aria-modal="true"`.

**⚡ PWA Performance Fanatic notes:**

- The video player component should be lazy-loaded. Don't include the player
  code in the initial bundle — load it only when the user clicks "Watch."
- Do NOT preload video content. The `.mp4` files are large and expensive.
  Only load when the user explicitly clicks play.
- The service worker must NOT cache these videos (see ticket 09-04).

**🤑 FinOps Miser notes:**

- Video hosting/streaming costs are zero — the videos are hosted on MLB's
  CDN, not ours. We simply link to them.

This is a catch-app repository ticket.
