# ArtemisSignals Launch v1.2

AWS Amplify static monorepo app (`appRoot: launch`) + existing `artemissignals-waitlist` CloudFormation stack in **eu-west-2 (London)**.

## Copy / deploy

Copy `launch/`, `backend/waitlist.yaml`, and root `amplify.yml` into the existing **artemissignals-platform** repository. Do **not** replace any other projects or Lambda stacks.

`launch/config.js` already targets the existing London endpoint: `https://k9k2llavp8.execute-api.eu-west-2.amazonaws.com/interest`. Keep it unless CloudFormation Outputs provides a different endpoint. Commit + push `main` to deploy the static site automatically through Amplify.

The current landing page continues to collect addresses even before email verification is activated. It will explicitly describe these as unverified. The referral counter only increments for verified signups after SES has been enabled.

## Update existing CloudFormation stack (important)

1. AWS console -> London `eu-west-2` -> CloudFormation -> existing **artemissignals-waitlist** stack -> **Update** -> Replace existing template -> upload `backend/waitlist.yaml`.
2. Confirm change set. **The table logical ID `WaitlistTable`, API `WaitlistApi`, Lambda `WaitlistFunction` and other original logical IDs are intentionally preserved.** Double-check that CloudFormation isn't proposing to replace or delete the DynamoDB table. Stop if replacement is shown.
3. Parameters: `DomainOrigin=https://artemissignals.ai`, `PreviewOrigin=https://main.d1pj4l274bgn2q.amplifyapp.com`, `VerificationBaseUrl=https://main.d1pj4l274bgn2q.amplifyapp.com` for initial testing, and `SenderEmail` blank until SES is ready.
4. Deploy; confirm status UPDATE_COMPLETE and verify that your London `InterestEndpoint` is still in `launch/config.js`.
5. Test the signup form. It should continue to accept records in DynamoDB.

## Enable verified email and welcome messages with SES

1. In London SES, verify a sending identity such as `hello@artemissignals.ai` or a verified domain and configure DKIM/SPF as SES recommends **without replacing existing MX/SPF**. Multiple services usually require one combined SPF TXT value for the root, not duplicate SPF records. SES domain verification may use additional CNAME records; preserve the existing domain's DKIM records.
2. If the AWS SES account is in sandbox, recipient addresses must also be verified for testing; request production access before opening public email verification to everyone.
3. CloudFormation -> Update stack -> Use current template -> set `SenderEmail` to the verified sender. Preserve existing parameters.
4. Register an address you own from the temporary Amplify URL. A verification email should arrive with a 24-hour link. Click it, then expect a welcome email containing the personal referral URL; new referred signups count only once when they verify their email.
5. After `artemissignals.ai` is serving this site with working HTTPS, update `VerificationBaseUrl` to `https://artemissignals.ai` in CloudFormation. You can keep the temporary origin in CORS for QA.

## Safeguards / limitations

- Source files do not contain AWS secrets. No schema migration or table replacement is intended. DynamoDB PITR remains enabled.
- Existing v1.1 records aren't automatically marked VERIFIED. If their owners register again with SES enabled, they can complete verification.
- SES sending may fail due to sandbox, verification or quotas; in that case the API returns an error rather than claiming that verification mail was sent. A signup remains pending, and the visitor can retry.
- Basic honeypot and API throttling are **not** a substitute for WAF/anti-abuse, rate limits per identity, SES bounce management or consent/unsubscribe automation. Build these before paid acquisition campaigns.
- Adding `ReferralCodeIndex` creates a DynamoDB GSI in place. Watch index creation progress and test referral attribution only when the index becomes ACTIVE. Referrals count only when new visitors verify. The initial release does not include self-service ranking or rewards.
- The sample signal preview is explicitly fictional, not a live data feed or trading recommendation.
- Update the privacy notice with the operator's full identity, contact, legal basis and data-retention period before public marketing. Review financial promotions and UK GDPR applicability with appropriate advisers.
- Social card currently uses `social-card.png` as its OG image and `robots.txt`/`sitemap.xml` for discovery.
