Artemis Admin v0.9.0 — Operations, Customers, Communications, Intelligence, Settings

WHAT IS INCLUDED
- Grouped navigation and refreshed styling.
- Action-focused overview, recent signal evidence, and integration coverage.
- Customer drawer with profile, Telegram connection, alert validation, preferences, and existing audited plan/trial controls.
- Customer sorting and local pagination of loaded accounts; existing Cognito next-page loading retained.
- Signal sorting, local pagination, quality/status/search filters, and expandable setup details.
- Read-only feature review matrix with 12 entries, including three separate Telegram controls.
- Notification center with independent channel states and filtered delivery events.
- Existing Data Health and historical ML-readiness checkpoint retained.

DEPLOYMENT
This is for the ADMIN Git repository, not the launch page or subscriber app.
1. Use a Git branch or retain your existing admin index.html for rollback.
2. Compare CFG with your current deployment. This revision preserves the Cognito and admin API settings from the saved v0.7.1/v0.8 source; retain newer live values if you changed them elsewhere.
3. Replace admin index.html with the included index.html. Commit and let the existing Amplify workflow deploy.
4. Sign in and verify existing customer/trial operations against your backend. Live authentication and production responses were not tested here.

LIVE DATA VS UI READINESS
The production file uses existing endpoints for account lists, health, signal samples, publisher observations, analytics, waitlist, invitations, and trials.
Runtime feature values, notification delivery events, and customer alert preferences require additional authenticated admin read endpoints. Those paths default to null and do not make requests until configured. Unconnected states are Unknown, not Disabled.
API-CONTRACT.md describes the proposed adapters. No backend deployment or new permissions are included.
The feature matrix is a review catalog. Its proposed keys are not an assertion that identically named deployed flags exist. Tier columns are intended-access policy, not a live entitlement audit.
Flag editing is deliberately absent from this revision. Existing production alert workers and subscriber delivery are not changed.

PREVIEW
Artemis-Admin-Preview.html is a separate offline design preview with synthetic example.com users, signal fixtures, and example runtime states. It makes no AWS API requests and refuses write operations. Do not deploy it as the admin index.

VALIDATION
- Production and preview JavaScript syntax, element bindings, and unique IDs checked.
- Browser checks: grouped navigation, three Telegram feature entries, independent customer connection/validation/delivery states, customer drawer tabs, customer pagination, signal pagination and quality filter reset, and delivery-event filtering.
- Unconfigured-source behavior checked locally: no API call, unknown state distinct from false.
- The final browser-only no-source pass hit a browser timeout; local fallback checks passed.
- No AWS changes, customer changes, messages, flag updates, or SageMaker jobs performed.
