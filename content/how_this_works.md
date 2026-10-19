<!-- Source of truth for the "How this works" page (docs/how-this-works.html renders this file).
     Numbers are the pipeline's values for the 2026-10-16 snapshot. If you change a rule here, change pipeline.py too. -->

# How this works

Oct 16, 2026 · @Bharat

## Summary

The command center turns three streams of work into one weekly cycle: connector requests, trending open-source agent skills, and marketplace listings.

Every Friday, each new ask is matched to a tool, deduped, scored with a simple weighted average, and given an owner, a decision (build, partner, decline or need info) and a reply. Skills spotted on GitHub, X and builder communities are ranked by predicted installs, checked against five compliance gates, packaged as SKILL.md, tested and launched on a steady cadence. Every listing is checked against one template. A written status goes out at the end of the week.

Three featured items show the whole path. **Brightpath Analytics** was asked for 6 times through 3 channels; it scores 77/100, is Urgent, and goes to engineering with a build brief. **sketchwright**, a technical illustration skill, passes every gate, goes from 10/12 to 12/12 in QA, and launches crediting its creator. **Granite Docs** and **Chartcraft**, two high-traffic listings, go from 1/8 and 2/8 checks to 8/8.

## The problem

Demand for connectors and skills is growing faster than ad-hoc triage can keep up.

**How it often works today:**

- Asks arrive by form, in a Slack channel and in DMs to whoever seems to own connectors. The same tool gets asked for under five spellings.
- The backlog fills up with issues that have no priority, no owner and no reply. In this snapshot, 40 of 62 old Linear issues had no priority and 41 had never had a reply.
- The loudest request wins, whether or not the connector would get used.
- Trending skills are spotted late, and licensing, permission and attribution get checked after the fact, if at all.
- Listings drift: each one is written differently, so the catalog looks inconsistent as it grows.

**The goal:** a weekly, measurable pipeline where every ask gets a decision and a reply within 5 business days, the skills we port are the ones people will install and are cleared to use, and every listing meets one standard.

## The weekly cycle

1. **Collect.** Forms, the request channel, direct asks, the Linear backlog, and skill candidates from GitHub, X and communities.
2. **Match and dedupe.** One tool per issue, whatever the spelling; already-live tools get a link.
3. **Score.** A weighted average of five signals gives each tool a 0–100 score; the rubric turns that into a tier. *Decision: how much does this matter?*
4. **Decide and reply.** Build, partner, decline or need info, with an owner, a Linear status and a reply. *Decision: what do we do?*
5. **Escalate and brief.** Hard calls and partnerships go to the Product Lead; approved builds get a brief.
6. **Spot and qualify skills.** Rank by predicted installs; check five gates. *Decision: which skills do we port?*
7. **Port, test, launch.** SKILL.md, listing copy, QA on representative prompts, GitHub export, launch notes.
8. **Keep listings consistent and report.** Audit against the template, rewrite the worst high-traffic listings, send the weekly status.

## Collect

| Source | What it tells us | In this snapshot |
|---|---|---|
| Request form | Tool, requester org, plan, use case, blocked deal | 167 asks |
| #connector-requests (Slack) | Free-text asks from AEs, CSMs, SEs, Support | 114 asks |
| Direct asks | Asks sent straight to the PM, often with a deal attached | 61 asks |
| Linear backlog | Existing issues with customer request counts | 62 issues |
| Live catalog | Connectors already in the marketplace | 70 connectors |
| Research signals | Company size, headcount growth, online mentions, API / MCP availability | 240 tools |
| Skill candidates | Repo, license, stars, stars in the last 7 days, X and community mentions, transport, sandbox needs | 64 candidates |

## Match and dedupe

Each ask's text is reduced to letters and digits ("Bright Path" → "brightpath") and compared with every known name, domain and alias. The longest match wins, so "Granite Docs" never matches "Granite CRM".

- **Already live** (64 asks): reply with a link; no new issue.
- **Already in the backlog** (75 asks): joined to the existing Linear issue, which gains a customer.
- **New tool** (194 asks): the first ask opens an issue; later asks are merged into it.
- **Tool not named** (9 asks), like "the HR tool we use": Need info; the reply asks which tool and what they want to do.

342 asks became 94 distinct tools. With the 62 old backlog issues, 110 open tools are scored.

## Score

### The weighted average

Each tool gets a priority score from 0 to 100. Each of five signals is turned into 0–100 points with simple buckets, multiplied by its weight, and the five results are added up.

| Signal | Weight | Points (0–100) | Why it matters |
|---|---|---|---|
| Customers asking | 30% | 20+ orgs → 100 · 10+ → 85 · 5+ → 70 · 3+ → 50 · 2 → 30 · 1 → 15 | Real customers asking is the strongest sign a connector will be used |
| Online traction (mentions, 90 days) | 25% | 10,000+ → 100 · 3,000+ → 80 · 1,000+ → 60 · 300+ → 40 · 50+ → 20 | Tools people talk about pull in users beyond the ones who asked |
| Share of asks from Enterprise customers | 20% | share × 100 | Bigger accounts, and revenue tied to the connector |
| Company size (employees) | 15% | 5,000+ → 100 · 1,000+ → 80 · 250+ → 60 · 50+ → 40 · 10+ → 20 | More users who could turn the connector on |
| Growth (headcount, 12 months) | 10% | 40%+ → 100 · 25%+ → 80 · 10%+ → 60 · 0%+ → 30 · shrinking → 0 | Fast-growing tools gain users after launch |

**Worked example: Brightpath Analytics**

| Signal | Value | Points | × Weight | = |
|---|---|---|---|---|
| Customers asking | 6 orgs | 70 | 30% | 21.0 |
| Online traction | 6,400 mentions | 80 | 25% | 20.0 |
| Enterprise share | 5 of 6 | 83 | 20% | 16.6 |
| Company size | 920 employees | 60 | 15% | 9.0 |
| Growth | +48% | 100 | 10% | 10.0 |
| **Priority score** | | | | **77** |

Pebblework Notes (12 employees, 40 mentions, 1 Free-plan customer) scores 10.

The two signals that add the most points are shown as each tool's top reasons. `validate.py` recomputes every score from the raw signals with separate code.

### Does it pick the right connectors?

The weights are a judgment call, so we check them against history. We scored 260 connectors we launched before with today's weights and asked whether each reached 50+ weekly active orgs 90 days after launch.

- **Picks the right one 74% of the time.** Take one connector that got used and one that didn't: the score ranks the used one higher 74% of the time (AUC 0.74; a coin flip is 50%).
- **"Most asks wins" gets 62%** (AUC 0.62), ranking by request count alone.
- **By tier:** 19% of past launches that would have been Low reached adoption, 46% of Medium, 74% of High and 80% of Urgent.

If a quarterly check shows a tier no longer separates winners from the rest, we adjust the weights.

### The rubric

| Tier | Rule |
|---|---|
| Urgent | 65+, or 50+ with a blocked deal of $100K+ |
| High | 50–64 |
| Medium | 35–49 |
| Low | Below 35 |

The blocked-deal rule is the one judgment call on top of the score: revenue already waiting on a connector makes a strong request time-sensitive. This week: 3 Urgent, 13 High, 51 Medium, 43 Low.

## Decide and reply

Rules run in this order:

1. API availability unknown → **Need info** (research it before deciding).
2. Vendor runs its own MCP server → **Partner** (they maintain it; we list it).
3. No public API → **Decline** (nothing to connect to).
4. Low tier → **Decline** for now; reviewed every quarter.
5. Otherwise → **Build**. Urgent and High get a brief and a build week (3 starts a week); Medium waits in Backlog.

| Decision | Owner | Linear status |
|---|---|---|
| Build | Integrations Eng (Pod A / Pod B, alternating by rank) | Todo (Urgent, High) or Backlog (Medium) |
| Partner | Product Lead (Connector PM if Low) | Backlog, labeled partner |
| Decline | Connector PM | Canceled, with the reason |
| Need info | Connector PM | Triage, labeled need-info |

Every ask gets a reply on the channel it came from, naming the decision and the Linear issue. The pipeline writes `linear_import.csv` in Linear's import shape: existing issues keep their ID.

## Escalate and brief

**To the Product Lead (25 this week):**

- Partnerships: the vendor runs its own MCP server and demand is Medium or higher.
- Hard calls: strong demand (High or Urgent) but no public API, where we could ask the vendor to ship an API or MCP server.
- Hard calls: a blocked deal of $250K+ on a tool the score rates Medium or Low.

**To engineering (7 briefs):** demand (customers, Enterprise share, channels, blocked deals), why it scores the way it does, what customers want to do, API and auth, acceptance criteria, and a draft listing that already passes the template.

## Spot and qualify skills

### Ranking

A regression on 90 skills we ported before predicts log installs in the first 30 days from log signals on port day.

| Signal | Coefficient |
|---|---|
| GitHub stars, last 7 days | 0.68 |
| X mentions, last 7 days | 0.34 |
| Community mentions, last 7 days | 0.25 |
| Total GitHub stars | 0.10 |

Momentum matters far more than lifetime popularity. On held-out ports, the model's rank correlation with real installs is 0.93; ranking by total stars gets 0.48. That is what spotting skills before they peak means in practice.

### Five gates

| Gate | Pass | Action (we can fix) | Fail (stops the port) |
|---|---|---|---|
| License | MIT, Apache-2.0, BSD, ISC | GPL, AGPL, MPL, custom: legal review | No license |
| Creator permission | Granted | Pending or not yet asked | Declined |
| Attribution | Line written: repo, @creator, license | Not written yet | n/a |
| Transport | Instructions and scripts, or remote MCP over HTTP | n/a | Local stdio only |
| Sandbox | None, writes to the outputs folder, allow-listed network | n/a | Host binaries, GPU |

sketchwright (#1 by predicted installs) passes all five. bincrack (#2) is trending just as hard but is GPL-3.0, local stdio only and needs host binaries, so it is Blocked; the next step is to ask the creator about a remote version.

## Port, test, launch

- **Package:** one folder per skill: `SKILL.md` (frontmatter, when to use, how to work, limits, attribution), `listing.json` and `qa_log.md`.
- **QA:** at least 10 representative prompts covering core tasks, follow-ups, a stress case, an edge case, a safety case and a sandbox case. Pass bar: 90% on the latest round. sketchwright failed the stress and sandbox prompts in round 1 (10/12); both were fixed in SKILL.md and round 2 passed 12/12.
- **Launch:** a PR to the marketplace repo; the GitHub export workflow re-runs the license, attribution and listing checks; merge exports it. Launch notes credit the creator by handle.
- **Cadence:** 2 launches a week. Skills that passed QA go first, then skills ready to port (a week to package and test).

## Listings

The template is eight checks a script can run: title is the product name only; a one-line summary that leads with what you can do; 3–5 capability bullets starting with a verb; permissions stated; required connectors stated; 3+ "Try asking" prompts; author shown; and for ports, attribution naming the repo, creator and license.

All 141 listings were audited; 7 pass all eight. The weakest checks are capability bullets (45% pass) and "Try asking" prompts (47%).

**Priority** = monthly views × share of checks failed. The top 20 are rewritten first at 5 a week: Granite Docs (41,200 views a month, 1/8 → 8/8) and Chartcraft (28,700, 2/8 → 8/8) are done; 18 are queued. Every new release has to pass all eight before launch, so the cleanup doesn't grow.

## Weekly status and success metrics

| Metric (first 90 days) | Now | Target |
|---|---|---|
| New asks triaged within 5 business days | 100% | 100% |
| Historical backlog scored and given a decision | 62/62 | All |
| Asks logged with owner, decision and reply | 100% | 100% |
| Skill candidates ranked | 64 | Active, ranked pipeline |
| Launch cadence | ~2 a week | Steady weekly cadence |
| Launches backed by test log, permission and attribution | 100% | 100% |
| Listings audited | 141/141 | All |
| Top-priority listings rewritten | 2/20 | All 20 |

The 5-day target holds because triage runs every Friday: an ask that arrives on a Monday waits 4 business days, one that arrives on a Friday is triaged that day.

## What this data can and can't show

All data is synthetic, generated with a fixed seed. The generator plants real relationships (bigger, faster-growing, more-discussed tools adopt more often; skill momentum drives installs). The backtest and the skills model find them, which shows the method works end to end. It does not prove these weights hold for a real marketplace. With real data, the same backtest would run on real launch outcomes, and we would expect weaker results than the 0.93 here.

## Decision log

| Decision | Why |
|---|---|
| Simple weighted average for the priority score | Anyone can check it by hand and see why a tool ranks where it does; a backtest on past launches keeps the weights honest |
| Label = 50+ weekly active orgs at day 90 | Adoption, not launch, is the outcome that matters; 90 days lets slow-moving Enterprise orgs show up |
| Blocked deal can lift High to Urgent | Revenue already waiting is time-sensitive in a way the adoption model can't see |
| Vendor-run MCP → Partner | The vendor maintains it; building our own would duplicate their work |
| Weekly Friday triage | One fixed pass guarantees the 5-business-day SLA and gives the status report a rhythm |
| Momentum over total stars for skills | On held-out ports, recent momentum ranks real installs far better than lifetime stars |
| Local stdio and host binaries are hard fails | The platform runs remote transports in a sandbox; those skills can't run there |
| Listing template as checks a script can run | A rule a script can check is enforced on every release, not just reviewed once |
