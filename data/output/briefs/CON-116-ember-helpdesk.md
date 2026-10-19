# Build brief: Ember Helpdesk connector (CON-116)

**Priority:** High (score 56/100) · **Owner:** Integrations Eng – Pod A · **Target start:** build week 3

## Why build it
- 2 customers asking (2 Enterprise); 0 new asks via nan.
- Blocked deals: $0.
- Model: 56% chance of 50+ weekly active orgs by day 90. Top reasons: Share of asks from Enterprise customers, Growth (headcount, 12 months).

## What customers want to do
- (no use cases given; confirm with requesters)

## Technical
- API: Public API · Auth: OAuth 2.0 · Docs: https://emberhelpdesk.com/developers
- Transport: remote MCP (HTTP). Scopes: request only what the capabilities below need.

## Acceptance criteria
- Every capability below works on a test workspace with real-shaped data.
- Auth works for an org admin and a regular member; scopes match the listing's permissions.
- 10+ representative prompts pass QA (90%+), logged in the QA sheet.
- Listing below passes all 8 template checks before launch.

## Draft listing
**Ember Helpdesk**: Search and work with your Ember Helpdesk data from chat.

Capabilities:
- Search records by keyword or owner
- Summarize recent activity
- Answer questions about your data

Permissions: Read · Required connectors: None · Author: Marketplace team

Try asking:
- What changed in Ember Helpdesk this week?
- Summarize the top items in Ember Helpdesk for my team
- Find anything in Ember Helpdesk about our Q4 launch
