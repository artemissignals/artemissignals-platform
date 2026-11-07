# Admin observability integration contracts

These are proposed read adapters, not existing endpoints or a deployed backend. All configuration paths default to `null`. Configure a path only after implementing and testing its read handler behind the existing admin API's JWT authorization and server-side ARTEMIS_ADMIN check. No write endpoint is consumed by these new views.

The UI accepts only relative `/admin/...` paths on the existing `CFG.api` origin and sends the current admin access token. It does not use the customer Telegram token or call the Telegram Bot API from the browser. Do not return bot tokens, secrets, raw private chat IDs, or credentials.

To connect deployed read handlers, put this before the main application script in the admin HTML (example paths):

```html
<script>
window.ARTEMIS_ADMIN_OBSERVABILITY = {
  flagsPath: '/admin/feature-flags',
  notificationsPath: '/admin/notification-status',
  customerPath: '/admin/customer-alerts'
};
</script>
```

## Feature configuration read response

```json
{
  "asOfUtc": "2026-11-07T12:00:00Z",
  "flags": [
    {
      "key": "telegram.accountLinking",
      "value": true,
      "source": "Descriptive deployed source identifier",
      "enforcement": "Description of the actual server-side guard"
    }
  ]
}
```

`value` must be a Boolean. Missing entries remain Unknown. Duplicate keys, invalid timestamps, and non-Boolean values cause the UI to reject the response. The UI displays source update and retrieval times; it does not independently certify the reported enforcement. The service should return a fresh retrieval timestamp only when it has actually read the underlying source. Use `cache-control: no-store` for these responses.

Proposed catalog keys:

| Key | Intended review source |
| --- | --- |
| telegram.accountLinking | Linking API eligibility and subscriber configuration |
| telegram.pilotAccess | Account allowlist plus ELITE entitlement |
| telegram.subscriberDelivery | Subscriber worker enablement, consent, and schedule |
| signals.forexMetals | PRO/ELITE market entitlements |
| signals.indicesCrypto | ELITE market entitlements |
| signals.history | History API access and paging |
| intelligence.marketNews | ELITE calendar entitlement and feed |
| intelligence.aiBriefings | Planned briefing service |
| intelligence.predictiveML | Research workflow; no assigned customer tier |
| notifications.browserPush | Automatic push subscription and worker; device test is separate |
| notifications.emailSignals | Email worker and consent/suppression |
| platform.serviceStatus | Service-status read sources |

Map these names to real deployed controls; do not create truth values from UI visibility, plan-group names alone, or assumed deployment state. In particular, private test Telegram delivery is separate from subscriber delivery. A single Boolean does not express pilot targeting: retain target-account restrictions server-side and describe them in the source-review evidence. The matrix's FREE/PRO/ELITE columns remain documented intended access, not runtime per-account targeting.

## Delivery telemetry read response

```json
{
  "asOfUtc": "2026-11-07T12:00:00Z",
  "channels": [
    {
      "id": "telegram",
      "status": "unknown",
      "deliveryEnabled": false,
      "transport": "Private bot transport"
    }
  ],
  "events": [
    {
      "channel": "telegram",
      "status": "failed",
      "at": "2026-11-07T11:30:00Z",
      "summary": "Sanitized operational summary"
    }
  ],
  "hasMore": false
}
```

Channel IDs: `telegram`, `email`, `browser`. Channel states: `healthy`, `failed`, `degraded`, `unknown`, `disabled`. Event states: `sent`, `failed`, `pending`, `blocked`. Keep channel IDs unique. `deliveryEnabled` is optional; omission means Unknown. Derive transport health from actual telemetry, not from whether a Lambda exists. A successful send response is not proof that a user read the message. The UI displays up to 100 matching returned events and never implies global queue counts. The backend must bound the response and indicate more records where appropriate. No resend button is included.

## Customer alert-status read response

The UI appends `?username=<encoded Cognito username>` to `customerPath`. Resolve that identity server-side to the correct account, then retrieve the existing link, entitlement, and preference records. Never infer eligibility solely from browser-supplied data.

```json
{
  "username": "exact-requested-cognito-username",
  "asOfUtc": "2026-11-07T12:00:00Z",
  "telegram": {
    "connected": true,
    "accountValidated": false,
    "deliveryEnabled": false
  },
  "preferences": {
    "markets": ["FX", "Metals"],
    "timeframes": ["H1", "M30"],
    "directions": ["BUY", "SELL"],
    "minimumQuality": 90
  }
}
```

The response username must exactly match the selected account. The frontend ignores stale drawer responses after switching accounts or closing the drawer. Each Telegram state is independent. Omit unknown Booleans rather than substituting false. `accountValidated` means alert-delivery eligibility, not email verification. Consent, plan access, pilot access, worker enablement, and preferences still require enforcement at send time. This endpoint is read-only; the UI does not edit alert preferences.

## Remaining backend work

1. Review the current admin Lambda and API routes before adding handlers.
2. Identify actual configuration sources for the Telegram linking pilot, private test worker, subscriber delivery, calendar access, and other capabilities.
3. Implement bounded read handlers using least-privilege access to those sources and existing customer records.
4. Add or verify delivery instrumentation before reporting sent/failed states.
5. Test unauthorized and non-admin requests, wrong-customer mapping, unavailable dependencies, and stale responses.
6. Wire the validated relative paths into the frontend. Runtime values then replace Unknown; do not enable subscriber delivery as a side effect.

Editable flags would be a separate change requiring server-side allowed keys and values, target validation, audit reasons, and an auditable rollback path. This makeover does not add that capability.
