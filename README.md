# ArtemisSignals platform — Brand Sync v0.8.6

Drop-in GitHub repository contents, preserving the London waitlist v1.2.1 files and the existing customer dashboard v0.8.5 functionality.

## What changed
- `dashboard/index.html`: shared midnight navy / slate / peach / teal visual palette, brand text and `⌁` icon in header and Cognito sign-in gate; v0.8.6 identifier; favicon.
- `dashboard/favicon.svg`: same simple `⌁` brand mark as the waitlist.
- `launch/index.html`: only adds a favicon link. Existing signup logic unchanged.
- `launch/favicon.svg`: favicon matching its existing `⌁` mark.
- Root `amplify.yml`: preserves `launch` static app and includes `dashboard` static app so both Git-backed Amplify apps build from `main`.
- `backend/`: copied intact from the provided v1.2.1 launch package; DO NOT redeploy CloudFormation for this visual release.

## Deployment
1. Make a backup of your local repository. Extract this ZIP, and copy its contents **into the root of `artemissignals-platform/`** (NOT into `dashboard/`). Keep your `.git` directory.
2. Verify `launch/config.js` matches your currently working London API. This bundle contains the last packaged launch config, which might differ from your current live repository; if it differs, KEEP YOUR WORKING VERSION. Likewise preserve newer modifications in `backend/` and `launch/` if they've been made since the earlier ZIP.
3. Confirm `dashboard/index.html` still contains the existing Cognito app client and the redirect `https://app.artemissignals.ai/`.
4. Commit and push `main` using GitHub Desktop. Both Amplify apps may build automatically.
5. Verify `artemissignals.ai` and `app.artemissignals.ai` load, Cognito login/logout, dashboard API and waitlist POST all work.

## Amplify app settings
- Launch app environment: `AMPLIFY_MONOREPO_APP_ROOT=launch`
- Customer app environment: `AMPLIFY_MONOREPO_APP_ROOT=dashboard`
- Both apps: branch `main`.
- Each app uses its matching entry in root `amplify.yml`.

## Scope and safety
- No changes to Cognito IDs, OAuth/PKCE login, signal/scanner API URLs, subscription logic, Lambda, DynamoDB, SES or SNS.
- Version and brand elements changed in frontend only.
- This is a visual update, not proof of end-to-end production testing.
