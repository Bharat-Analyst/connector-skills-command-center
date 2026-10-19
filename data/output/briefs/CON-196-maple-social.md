# Build brief: Maple Social connector (CON-196)

**Priority:** High (score 52/100) · **Owner:** Integrations Eng – Pod A · **Target start:** build week 3

## Why build it
- 1 customers asking (1 Enterprise); 1 new asks via Form.
- Blocked deals: $0.
- Priority score 52/100. Top reasons: Share of asks from Enterprise customers, Online traction (mentions, 90 days).

## What customers want to do
- draft campaign emails

## Technical
- API: Public API · Auth: OAuth 2.0 · Docs: https://maplesocial.com/developers
- Transport: remote MCP (HTTP). Scopes: request only what the capabilities below need.

## Acceptance criteria
- Every capability below works on a test workspace with real-shaped data.
- Auth works for an org admin and a regular member; scopes match the listing's permissions.
- 10+ representative prompts pass QA (90%+), logged in the QA sheet.
- Listing below passes all 8 template checks before launch.

## Draft listing
**Maple Social**: Search and work with your Maple Social data from chat.

Capabilities:
- Draft campaign emails
- Summarize recent activity
- Answer questions about your data

Permissions: Read and write · Required connectors: None · Author: Marketplace team

Try asking:
- What changed in Maple Social this week?
- Summarize the top items in Maple Social for my team
- Find anything in Maple Social about our Q4 launch
