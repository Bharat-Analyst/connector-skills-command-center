# Build brief: Acme Payroll connector (CON-152)

**Priority:** High (score 52/100) · **Owner:** Integrations Eng – Pod B · **Target start:** build week 2

## Why build it
- 5 customers asking (1 Enterprise); 0 new asks via nan.
- Blocked deals: $0.
- Priority score 52/100. Top reasons: Customers asking, Online traction (mentions, 90 days).

## What customers want to do
- (no use cases given; confirm with requesters)

## Technical
- API: Public API · Auth: OAuth 2.0 · Docs: https://acmepayroll.com/developers
- Transport: remote MCP (HTTP). Scopes: request only what the capabilities below need.

## Acceptance criteria
- Every capability below works on a test workspace with real-shaped data.
- Auth works for an org admin and a regular member; scopes match the listing's permissions.
- 10+ representative prompts pass QA (90%+), logged in the QA sheet.
- Listing below passes all 8 template checks before launch.

## Draft listing
**Acme Payroll**: Search and work with your Acme Payroll data from chat.

Capabilities:
- Search records by keyword or owner
- Summarize recent activity
- Answer questions about your data

Permissions: Read · Required connectors: None · Author: Marketplace team

Try asking:
- What changed in Acme Payroll this week?
- Summarize the top items in Acme Payroll for my team
- Find anything in Acme Payroll about our Q4 launch
