# feat: Implement Google Cast SDK integration for Chromecast

## What do you want to build?

Integrate the Google Cast Web Sender SDK into catch-app to allow users to cast
condensed game highlight videos to Google Cast devices (Chromecast, Android TV
with Cast support, smart displays, etc.). The implementation uses the Default
Media Receiver — no custom Cast receiver app is needed.

## Acceptance Criteria

- [ ] The Google Cast Web Sender SDK is loaded from Google's CDN
- [ ] A Cast button (using the standard `google-cast-launcher` custom element) appears in the video player when a Cast device is available on the local network
- [ ] Clicking the Cast button opens the device picker and connects to the selected device
- [ ] Once connected, the condensed game `.mp4` URL is sent to the Cast device for playback
- [ ] The Cast session uses the Default Media Receiver (`CC1AD845`) — no custom receiver app ID
- [ ] Playback controls (play, pause, seek, volume, stop) are available in the browser while casting
- [ ] When the user stops casting, playback resumes in the browser (or the player resets)
- [ ] If no Cast devices are found, the Cast button does not appear (graceful degradation)
- [ ] The Cast SDK loading does not block initial page render (async load)
- [ ] Integration is tested manually with a physical Chromecast device

## Implementation Notes

**📺 Living Room Tester notes:**

- The Default Media Receiver handles `.mp4` playback natively. No custom
  receiver app development is needed. This is the simplest Cast integration.
- **URL accessibility:** The Cast device fetches the `.mp4` URL directly from
  MLB's CDN. The URL must be accessible from the Chromecast's network
  (usually the local network with internet access). This should work for
  publicly accessible URLs.
- **HTTPS requirement:** The Cast SDK requires the sender app to be served
  over HTTPS. The PWA must be deployed on HTTPS (GitHub Pages/Vercel/
  Cloudflare all provide this by default).
- **Media metadata:** When casting, send media metadata (title, subtitle) so
  the Cast device displays "Yankees vs Red Sox — Condensed Game" on the TV,
  not just a raw URL.
- Test with: Chromecast (Gen 3), Chromecast with Google TV, Android TV. Edge
  case: test when the Chromecast is on a different subnet than the sender
  (should fail gracefully).

**♿ Accessibility Coordinator notes:**

- The `google-cast-launcher` custom element is provided by Google and includes
  standard accessibility attributes. However, verify it works with screen
  readers.
- When casting is active, announce the state change to screen readers: "Now
  casting to Living Room TV."
- Cast controls (play, pause, etc.) must be keyboard-accessible.

**⚡ PWA Performance Fanatic notes:**

- Load the Cast SDK asynchronously: `<script async src="https://www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1">`
- The SDK is ~100 KB. Loading it async ensures it does not block the initial
  page render or affect Core Web Vitals.
- Lazy-load the Cast integration module: only initialize the Cast context
  when the video player is opened.

**🤑 FinOps Miser notes:**

- The Default Media Receiver is free to use — no registration or costs.
- The Cast SDK is loaded from Google's CDN — no hosting cost for us.

This is a catch-app repository ticket.
