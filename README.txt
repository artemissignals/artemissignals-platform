Artemis dashboard new-signal sounds v1

GIT INSTALL (no AWS changes or backend deployment)
1. Extract this ZIP. Merge its dashboard/ and tools/ folders into your existing
   artemissignals-platform Git checkout. Do not replace the whole dashboard folder.
   Your existing dashboard/index.html is kept as the input for patching.
2. Open a terminal in that repository folder and run:
   Windows: python tools/patch_dashboard_sounds.py dashboard/index.html
   CloudShell/macOS/Linux: python3 tools/patch_dashboard_sounds.py dashboard/index.html
3. Commit dashboard/index.html and dashboard/signal-sounds.js together, then push.
   The patcher can optionally be committed under tools/ too for repeatability.
   Backups are outside the repository in ~/artemis-backups/dashboard-sounds/.
4. Wait for your existing subscriber deployment, then hard-refresh the dashboard.
5. In Account Settings > New-signal sounds, click Preview sound once and check
   your speakers/headphones. Browser audio needs user interaction.

IF YOU USE CLOUDSHELL TO PATCH
Upload this ZIP and download/upload your CURRENT Git dashboard/index.html as
/home/cloudshell-user/index.html. Then:
 unzip -o ~/Artemis-Dashboard-Signal-Sounds-v1.zip -d ~/artemis-dashboard-sounds-v1
 python3 ~/artemis-dashboard-sounds-v1/tools/patch_dashboard_sounds.py ~/index.html
Download ~/index.html and ~/signal-sounds.js. Replace Git dashboard/index.html and
add dashboard/signal-sounds.js, commit together, and push. Do not deploy the ZIP.

BEHAVIOR
- Sound defaults ON; one synthesized sound per newly detected matching batch.
- Top bar has a clearly labeled Sound on / Sound off bell beside the existing
  unread-notifications bell. Click to mute/unmute; the icons serve separate functions.
- Account Settings: on/off, Bell / Chime / Double ping / Soft tone, volume, preview.
- Preferences are per account on this browser; they do not sync across devices.
- Audio follows Notification Center quality/timeframe/watchlist and entitlement
  filters, separate from Telegram filters. Existing default notification quality is 90+.
- NEW signals only: no startup/history replay or target/stop sounds.
- First complete successful load establishes the sound baseline. Partial feeds
  do not establish it. Unknown/missing publication timestamps are not sounded.
- No queued catch-up sounds after audio is blocked, muted, or turned off.
- Same-browser tabs use Web Locks plus stored event IDs where available. This is
  best-effort duplicate suppression; separate browser profiles/devices are independent.
- Four short sounds are synthesized locally; no external audio files or network calls.

LIMITS
Keep the dashboard open, signed in, unmuted and running. Background tabs may ring,
but timers may be throttled; suspension, sleeping/locked devices and closed tabs
can delay/prevent delivery. This is not background Web Push and does not promise
instant or closed-tab alerts. Existing Telegram delivery is unchanged.

Patcher checks the current Notification Center integration before editing and
stops on an unfamiliar layout. It preserves current configuration, sign-in,
Telegram, maintenance and other page content. The patch is idempotent.
Keep existing communications-config.js, telegram-config.js and all other assets.

VALIDATION
Mock browser logic checks: default on, initial baseline, fresh NEW only, duplicates,
filters, lifecycle exclusion, mute persistence, per-account isolation, choice preview,
autoplay blocked without later replay, partial-feed baseline, multi-tab suppression,
and sign-out. Patcher idempotence/unique controls and all embedded JS syntax checked.
Actual speaker output and OS/browser background behavior require your device test.
