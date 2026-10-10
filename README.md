# ArtemisSignals v0.9.0 — Intelligence Dashboard

GitHub/Amplify monorepo deploy package. Copy the **contents** of this ZIP into your existing `artemissignals-platform` repository root, preserving `.git` and any newer local modifications. Review before overwriting `launch/` or `backend/`; these are inherited unchanged from the v0.8.6 package and may be older than your working branch.

## Dashboard v0.9.0
- Branded market briefing with honest authenticated signal and scanner counts; manual Refresh Now button
- Opportunity Radar and evidence-based "Why no signal?" explanation (scanner's actual reason/missing condition, when available)
- Scanner stale/offline detection, including missing/invalid timestamps; no fake ready states
- Clearer signal cards: age and TP1 entry-to-stop risk/reward (only when input prices exist)
- Responsive briefing, richer hierarchy, preserved watchlist filtering and detail drawers
- No changes to existing Cognito PKCE authentication, redirect, API endpoints, data storage or plan enforcement

## Deploy
1. Back up/commit your working GitHub branch first.
2. Compare this ZIP to your checked-out repository; copy `dashboard/index.html` and `dashboard/favicon.svg` first. `amplify.yml` in the ZIP has `appRoot: launch` and `appRoot: dashboard`; only replace if your live build spec does not have later customisations.
3. Preserve any newer live `launch` files and `backend` infrastructure; **do not redeploy backend** for this frontend release.
4. Commit and push `main` via GitHub Desktop, then check both Amplify builds.
5. Test login/logout, live signals, scanner response, watchlist, dark/light theme and mobile.

## Limitations
- Counts and radar need a functioning scanner-state API: `https://0wudrtkh3b.execute-api.eu-west-2.amazonaws.com/v1/scanner-state`.
- "Why no signal?" uses scanner evidence; cannot infer conditions that were never published.
- `USER_PLAN=PRO` remains a display-side placeholder, not a security entitlement control.
- Waitlist/launch files are preserved from earlier package, not verified against current live main.
- No live AWS end-to-end test performed here.
