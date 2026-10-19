# Build brief: Cinder Billing connector (CON-149)

**Priority:** High (score 69/100) · **Owner:** Integrations Eng – Pod A · **Target start:** build week 1

## Why build it
- 4 customers asking (3 Enterprise); 2 new asks via Form.
- Blocked deals: $0.
- Model: 69% chance of 50+ weekly active orgs by day 90. Top reasons: Share of asks from Enterprise customers, Online traction (mentions, 90 days).

## What customers want to do
- look up failed payments

## Technical
- API: Public API · Auth: API key · Docs: https://cinderbilling.com/developers
- Transport: remote MCP (HTTP). Scopes: request only what the capabilities below need.

## Acceptance criteria
- Every capability below works on a test workspace with real-shaped data.
- Auth works for an org admin and a regular member; scopes match the listing's permissions.
- 10+ representative prompts pass QA (90%+), logged in the QA sheet.
- Listing below passes all 8 template checks before launch.

## Draft listing
**Cinder Billing**: Search and work with your Cinder Billing data from chat.

Capabilities:
- Look up failed payments
- Summarize recent activity
- Answer questions about your data

Permissions: Read · Required connectors: None · Author: Marketplace team

Try asking:
- What changed in Cinder Billing this week?
- Summarize the top items in Cinder Billing for my team
- Find anything in Cinder Billing about our Q4 launch
