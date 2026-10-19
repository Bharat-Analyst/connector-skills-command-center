# Build brief: Fernhill Shield connector (CON-157)

**Priority:** High (score 56/100) · **Owner:** Integrations Eng – Pod B · **Target start:** build week 4

## Why build it
- 3 customers asking (1 Enterprise); 0 new asks via nan.
- Blocked deals: $0.
- Model: 56% chance of 50+ weekly active orgs by day 90. Top reasons: Growth (headcount, 12 months), Online traction (mentions, 90 days).

## What customers want to do
- (no use cases given; confirm with requesters)

## Technical
- API: Public API · Auth: API key · Docs: https://fernhillshield.com/developers
- Transport: remote MCP (HTTP). Scopes: request only what the capabilities below need.

## Acceptance criteria
- Every capability below works on a test workspace with real-shaped data.
- Auth works for an org admin and a regular member; scopes match the listing's permissions.
- 10+ representative prompts pass QA (90%+), logged in the QA sheet.
- Listing below passes all 8 template checks before launch.

## Draft listing
**Fernhill Shield**: Search and work with your Fernhill Shield data from chat.

Capabilities:
- Search records by keyword or owner
- Summarize recent activity
- Answer questions about your data

Permissions: Read · Required connectors: None · Author: Marketplace team

Try asking:
- What changed in Fernhill Shield this week?
- Summarize the top items in Fernhill Shield for my team
- Find anything in Fernhill Shield about our Q4 launch
