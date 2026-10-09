# ArtemisSignals Launch — Waitlist-enabled

Static launch website deployed by AWS Amplify from `launch/`.

## Connect backend
1. CloudFormation → Create stack → Upload `backend/waitlist.yaml`. Stack name `artemissignals-waitlist`. DomainOrigin `https://artemissignals.ai`. Acknowledge IAM resource creation.
2. Once deployed, open stack **Outputs**, copy `InterestEndpoint`.
3. In `launch/config.js`, paste the URL between quotes. Commit and push in GitHub Desktop; Amplify redeploys.
4. On **https://artemissignals.ai**, submit a test email, verify in DynamoDB table (CloudFormation `TableName` output), then test duplicate submission and invalid email.

**Important:** This captures opt-in requests but does NOT send a verification or welcome email, and does not yet provide a self-service unsubscribe flow. Before sending bulk marketing emails, integrate an ESP/SES with unsubscribe handling and ideally confirmed double opt-in. The privacy notice assumes `hello@artemissignals.ai` is monitored for data requests; edit the notice if that is not true. Do not put secrets in config.js. API Gateway endpoint is public by design, protected by basic throttling and a bot honeypot, not a CAPTCHA/WAF. Consider additional anti-abuse controls before advertising broadly.
