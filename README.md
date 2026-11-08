# Artemis Communications v1

Adds an authenticated Communications API, admin message composer, and subscriber service notices. Existing signal ingestion, account linking, preferences, and live Telegram alert-worker stacks are not modified.

## Deploy the backend in AWS CloudShell

1. Upload this ZIP to your CloudShell home folder.
2. Extract it into a new directory:

```bash
unzip ~/Artemis-Communications-v1.zip -d ~/artemis-communications-v1
cd ~/artemis-communications-v1
python3 setup_communications.py --deploy
```

The script discovers your existing JWT authorizers, linked-account configuration, and admin callback origins. It reuses the existing bot credential parameter without retrieving the token during setup. If your admin hosting origin is missing from the printed origins, add `--admin-origin https://YOUR-ADMIN-HOST` and redeploy.

Creates one new CloudFormation stack: `artemis-communications-v1`. Includes one Lambda, an HTTP API with separate admin/customer JWT authorizers, an isolated DynamoDB table, a one-minute outbox schedule, and CloudWatch logs. No reserved concurrency is requested. No messages are queued and no notices are published by setup. The scheduled worker sends nothing until an administrator approves an announcement.

Both `/admin/communications` and `/notices` must return HTTP 401 without a token. Do not deploy frontend configuration if those checks fail.

## Deploy through Git

After backend deployment generates the real configuration:

| Repository | Files to replace or add |
|---|---|
| Admin portal | `admin-app/index.html` → your existing `index.html`; `admin-app/communications.js`; `admin-app/communications-config.js` |
| Subscriber app | `customer-app/index.html` → your existing `index.html`; `customer-app/service-notices.js`; `customer-app/communications-config.js` |

Copy the generated `communications-config.js` into each repository beside `index.html`. Commit these changes and use your normal Amplify deployment. Keep all existing assets and `telegram-config.js`.

The admin index is based on the exact file uploaded November 8. It contains the v0.9 read-only feature catalog; Communications preserves that supplied catalog and existing sections. It does not restore the older editable feature-flag interface or customer overrides that were absent from this upload.

The subscriber index includes the latest Telegram icon and separate Connected / Account Validated / Delivery Enabled cards.

## First use

Open **Communications → Compose & notices** in the admin portal and refresh.

### Telegram

- Initial recipient scope is the single linked Elite account already enabled for live delivery. This does not roll out Telegram to other subscribers.
- Write a message, or use **Generate from notice details**. Generation uses a deterministic template and entered facts; no AI model is connected or billed.
- Select the eligible recipient, preview the exact message, check the review confirmation, then click **Send approved announcement** and accept the recipient-count confirmation.
- Refresh after about one minute for results. `SENT` means Telegram accepted it; it does not prove the device displayed it or the member read it.
- Existing `/stop`, disconnect, delivery enablement, ownership checks, and live Elite membership are rechecked. Reconnecting to a different chat invalidates queued recipients.
- Quality and market filters apply to trading signals, not these explicitly approved service announcements.
- Approved but undelivered announcements expire after one hour. Preview approval expires after ten minutes.
- Sending the same approved preview again cannot create another batch. Ambiguous send results or timed-out claims become `REVIEW_REQUIRED`, never automatic retries. Review before deliberately creating a new announcement.

### Dashboard notices

- Enter the notice, affected services, status, local start/end times, and display-until time.
- Review the preview and publication confirmation, then click **Publish dashboard notice**.
- Subscriber **Service Status** shows the notice on refresh or within about one minute. Current investigating incidents and active scheduled windows also show a banner.
- Edit an existing notice to resolve or cancel it. Updates require the current version, so stale editors cannot silently overwrite another change.
- Expiration is checked by the API and browser; it does not depend on eventual DynamoDB TTL deletion.
- Publishing a notice never sends Telegram. Generate a separate announcement if desired.
- An unavailable feed displays **Unavailable**, rather than claiming there are no notices.

## Records and controls

Communication records and results are retained for 90 days; audit events for one year; expired notices for an additional 30 days. DynamoDB TTL deletion is asynchronous. Table deletion/replacement retention is enabled. API administrators must still be active in the `ARTEMIS_ADMIN` Cognito group; customer tokens cannot invoke admin actions.

New-stack creation is reversible through CloudFormation; retain the communications table for its audit records. To stop only announcement processing, disable the new stack's EventBridge rule. This does not stop the separate trading-signal alert worker. No ingestion or signal table writes are permitted by the new role.

## Validation

26 backend tests cover authorization, recipient eligibility, preview binding and expiry, immutable approval, duplicate sends, transactional audit, ambiguous sends, stale claims, notice versions, expiration and Unicode limits. Node tests cover UI approval/reset logic, notice rendering, feed failures, and plain-text display. JavaScript syntax and HTML IDs are checked. Browser visual verification was unavailable in the build environment; check the deployed page on desktop and mobile.

```bash
python3 tests/test_service.py
node tests/test_ui.cjs
```
