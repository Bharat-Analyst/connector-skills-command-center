# Build brief: Basalt Canvas connector (CON-153)

**Priority:** High (score 63/100) · **Owner:** Integrations Eng – Pod A · **Target start:** build week 2

## Why build it
- 7 customers asking (3 Enterprise); 0 new asks via nan.
- Blocked deals: $0.
- Model: 63% chance of 50+ weekly active orgs by day 90. Top reasons: Customers asking, Growth (headcount, 12 months).

## What customers want to do
- (no use cases given; confirm with requesters)

## Technical
- API: Public API · Auth: OAuth 2.0 · Docs: https://basaltcanvas.com/developers
- Transport: remote MCP (HTTP). Scopes: request only what the capabilities below need.

## Acceptance criteria
- Every capability below works on a test workspace with real-shaped data.
- Auth works for an org admin and a regular member; scopes match the listing's permissions.
- 10+ representative prompts pass QA (90%+), logged in the QA sheet.
- Listing below passes all 8 template checks before launch.

## Draft listing
**Basalt Canvas**: Search and work with your Basalt Canvas data from chat.

Capabilities:
- Search records by keyword or owner
- Summarize recent activity
- Answer questions about your data

Permissions: Read · Required connectors: None · Author: Marketplace team

Try asking:
- What changed in Basalt Canvas this week?
- Summarize the top items in Basalt Canvas for my team
- Find anything in Basalt Canvas about our Q4 launch
