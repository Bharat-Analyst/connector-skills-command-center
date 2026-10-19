# Build brief: Alder Billing connector (CON-165)

**Priority:** High (score 58/100) · **Owner:** Integrations Eng – Pod A · **Target start:** build week 1

## Why build it
- 21 customers asking (6 Enterprise); 21 new asks via Direct ask, Form, Slack.
- Blocked deals: $0.
- Priority score 58/100. Top reasons: Customers asking, Company size.

## What customers want to do
- look up failed payments
- summarize churned subscriptions
- reconcile payouts

## Technical
- API: Public API · Auth: API key · Docs: https://alderbilling.com/developers
- Transport: remote MCP (HTTP). Scopes: request only what the capabilities below need.

## Acceptance criteria
- Every capability below works on a test workspace with real-shaped data.
- Auth works for an org admin and a regular member; scopes match the listing's permissions.
- 10+ representative prompts pass QA (90%+), logged in the QA sheet.
- Listing below passes all 8 template checks before launch.

## Draft listing
**Alder Billing**: Search and work with your Alder Billing data from chat.

Capabilities:
- Look up failed payments
- Summarize churned subscriptions
- Reconcile payouts

Permissions: Read and write · Required connectors: None · Author: Marketplace team

Try asking:
- What changed in Alder Billing this week?
- Summarize the top items in Alder Billing for my team
- Find anything in Alder Billing about our Q4 launch
