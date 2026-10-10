# ArtemisSignals Customer Dashboard v0.8.4 — Launch Theme

This release is derived from the uploaded `index(1).html` (v0.8.3).

## Changed
- Adopted the ArtemisSignals launch site navy/peach/teal palette.
- Matched backgrounds, panel outlines, buttons and highlights across dark/light themes.
- Preserved dashboard layout and existing JavaScript behaviour.

## Deploy
1. Copy the `dashboard/` directory into your existing `artemissignals-platform` checkout. Do not replace `launch/` or `backend/`.
2. In AWS Amplify create the Git-connected dashboard app with monorepo app root `dashboard`.
3. If your repository already has a root `amplify.yml`, **keep the working launch application entry**, and add the dashboard app entry from `dashboard-amplify-entry.yml`.
4. Commit and push the changes. Test the temporary Amplify URL before attaching the custom subdomain.

## Existing integrations preserved (not tested)
- Signals: `https://0wudrtkh3b.execute-api.eu-west-2.amazonaws.com/v1/signals`
- Scanner: `https://0wudrtkh3b.execute-api.eu-west-2.amazonaws.com/v1/scanner-state`
- Cognito client/domain values retained from v0.8.3

**Important:** `COGNITO_REDIRECT_URI` is still the old `https://staging.d25slvada984cq.amplifyapp.com`. Before authenticating on the new Amplify URL, add the new callback/logout URL to your Cognito app client and update this JavaScript constant. Do not put a Cognito client secret or any API secrets in this static file.

No AWS backend changes or domain updates are included.
