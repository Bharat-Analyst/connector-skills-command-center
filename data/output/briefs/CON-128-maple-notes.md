# Build brief: Maple Notes connector (CON-128)

**Priority:** High (score 59/100) · **Owner:** Integrations Eng – Pod A · **Target start:** build week 3

## Why build it
- 6 customers asking (1 Enterprise); 0 new asks via nan.
- Blocked deals: $0.
- Model: 59% chance of 50+ weekly active orgs by day 90. Top reasons: Customers asking, Company size.

## What customers want to do
- (no use cases given; confirm with requesters)

## Technical
- API: Public API · Auth: API key · Docs: https://maplenotes.com/developers
- Transport: remote MCP (HTTP). Scopes: request only what the capabilities below need.

## Acceptance criteria
- Every capability below works on a test workspace with real-shaped data.
- Auth works for an org admin and a regular member; scopes match the listing's permissions.
- 10+ representative prompts pass QA (90%+), logged in the QA sheet.
- Listing below passes all 8 template checks before launch.

## Draft listing
**Maple Notes**: Search and work with your Maple Notes data from chat.

Capabilities:
- Search records by keyword or owner
- Summarize recent activity
- Answer questions about your data

Permissions: Read · Required connectors: None · Author: Marketplace team

Try asking:
- What changed in Maple Notes this week?
- Summarize the top items in Maple Notes for my team
- Find anything in Maple Notes about our Q4 launch
