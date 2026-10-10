ARTEMIS SIGNALS APP v0.8.3 — LIVE SCANNER EXPERIENCE

v0.8.3 VISUAL UPDATE
- Active session status now uses a restrained outward pulse
- Pulse automatically stops during the traditional weekend market closure
- Reduced-motion accessibility preference disables the animation

PRIVATE SUBSCRIBER APP
https://staging.d25slvada984cq.amplifyapp.com

PUBLIC WEBSITE
Keep your public ArtemisSignals.ai website separate. Do not deploy this ZIP over it.

COGNITO
Domain:
https://eu-west-2ptwnbug4q.auth.eu-west-2.amazoncognito.com

Client ID:
63u0rb0dvvtln29jf2bui3n085

Flow:
Authorization Code Grant + PKCE

Scopes:
openid email profile

COGNITO SETTINGS REQUIRED
Allowed callback URL:
https://staging.d25slvada984cq.amplifyapp.com

Default redirect URL:
https://staging.d25slvada984cq.amplifyapp.com

Allowed sign-out URL:
https://staging.d25slvada984cq.amplifyapp.com

WHAT v0.8 / v0.8.1 / v0.8.2 ADD
- v0.8: consumes real MT5 scanner-state telemetry rather than inferring setup state from signal history
- v0.8: displays bias, confluence, evidence, missing condition and current setup stage
- v0.8.1: scanner heartbeat, freshness and automatic offline/stale detection
- v0.8.1: graceful degraded mode if scanner telemetry is unavailable
- v0.8.2: asset-class and scanner-state filters
- v0.8.2: persistent personal instrument watchlist stored in the browser
- v0.8.2: scanner evidence and service-health detail drawer

RETAINED FROM v0.7.9
- Protects the subscriber dashboard behind Cognito login
- Sends login/signup to Cognito
- Returns users to the NEW private Amplify app
- Shows signed-in user's email
- Includes logout
- Keeps live signal feed/dashboard functionality
- Sends the signed-in user's Cognito ID token to the signals API
- Adds a persistent Dark / Light theme toggle
- Adds a global London / New York / Tokyo / UTC market clock
- Adds premium signal direction rails and target progress tracking
- Adds loading skeletons, polished errors and responsive navigation
- Uses real Cognito email data in the profile
- Removes placeholder billing dates and adds a clear risk footer
- Adds a market scanner matrix using the latest real record per instrument
- Adds FX, Metals, Indices and Crypto overview cards
- Adds a live signal activity ticker
- Adds a real-data outcome donut and session activity heatmap
- Adds persistent Compact / Comfortable dashboard density modes
- Detects the weekend FX trading break in UTC
- Shows FX, Metals and Indices as closed during the weekend
- Keeps Crypto shown as open 24/7
- Replaces weekday session wording with a clear weekend status message

MARKET HOURS NOTE
The status uses the standard weekly FX window (Sunday 22:00 UTC to Friday 22:00 UTC). Broker, instrument, holiday and exchange hours can vary.

SIGNAL EXPERIENCE
- Adds a market-aware Opportunity Board from the latest real record per instrument
- Adds clickable premium signal-detail drawers
- Adds issued / TP1 / TP2 / closed lifecycle visualization
- Adds evidence-based Why This Signal summaries from supplied metadata
- Adds R:R calculations when entry, stop and targets are available
- Adds a position-size planner requiring the broker's value-per-price-move input
- Adds authenticated API heartbeat and latest-event monitoring
- Adds honest empty and weekend states without fabricating scanner conditions

API GATEWAY REQUIRED
- Existing: GET /v1/signals with ArtemisCognitoJWT
- Add POST /v1/scanner-state using the private X-Artemis-Key ingestion check
- Add GET /v1/scanner-state with ArtemisCognitoJWT
- Use token source: Authorization
- Attach the authorizer without method-level OAuth scopes (the app sends the ID token)
- Keep the MT5 ingestion route on its existing API-key protection

DEPLOY
Upload this ZIP to the private Amplify app:
https://staging.d25slvada984cq.amplifyapp.com
