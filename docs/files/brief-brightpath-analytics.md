# Build brief: Brightpath Analytics connector (CON-168)

**Priority:** Urgent (score 77/100) · **Owner:** Integrations Eng – Pod A · **Target start:** build week 1

## Why build it
- 6 customers asking (5 Enterprise); 6 new asks via Direct ask, Form, Slack.
- Blocked deals: $180,000.
- Priority score 77/100. Top reasons: Customers asking, Online traction (mentions, 90 days).

## What customers want to do
- pull weekly KPIs into a report
- explain a metric drop

## Technical
- API: Public API · Auth: OAuth 2.0 · Docs: https://brightpath.io/developers
- Transport: remote MCP (HTTP). Scopes: request only what the capabilities below need.

## Acceptance criteria
- Every capability below works on a test workspace with real-shaped data.
- Auth works for an org admin and a regular member; scopes match the listing's permissions.
- 10+ representative prompts pass QA (90%+), logged in the QA sheet.
- Listing below passes all 8 template checks before launch.

## Draft listing
**Brightpath Analytics**: Search and work with your Brightpath Analytics data from chat.

Capabilities:
- Pull weekly KPIs into a report
- Explain a metric drop
- Answer questions about your data

Permissions: Read · Required connectors: None · Author: Marketplace team

Try asking:
- What changed in Brightpath Analytics this week?
- Summarize the top items in Brightpath Analytics for my team
- Find anything in Brightpath Analytics about our Q4 launch
