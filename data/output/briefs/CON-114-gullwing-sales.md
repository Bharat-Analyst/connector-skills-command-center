# Build brief: Gullwing Sales connector (CON-114)

**Priority:** High (score 56/100) · **Owner:** Integrations Eng – Pod A · **Target start:** build week 4

## Why build it
- 8 customers asking (1 Enterprise); 0 new asks via nan.
- Blocked deals: $0.
- Model: 56% chance of 50+ weekly active orgs by day 90. Top reasons: Customers asking, Online traction (mentions, 90 days).

## What customers want to do
- (no use cases given; confirm with requesters)

## Technical
- API: Public API · Auth: API key · Docs: https://gullwingsales.com/developers
- Transport: remote MCP (HTTP). Scopes: request only what the capabilities below need.

## Acceptance criteria
- Every capability below works on a test workspace with real-shaped data.
- Auth works for an org admin and a regular member; scopes match the listing's permissions.
- 10+ representative prompts pass QA (90%+), logged in the QA sheet.
- Listing below passes all 8 template checks before launch.

## Draft listing
**Gullwing Sales**: Search and work with your Gullwing Sales data from chat.

Capabilities:
- Search records by keyword or owner
- Summarize recent activity
- Answer questions about your data

Permissions: Read · Required connectors: None · Author: Marketplace team

Try asking:
- What changed in Gullwing Sales this week?
- Summarize the top items in Gullwing Sales for my team
- Find anything in Gullwing Sales about our Q4 launch
