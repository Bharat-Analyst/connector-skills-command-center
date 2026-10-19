<!-- Source of truth for the "How this works" page (docs/how-this-works.html renders this file).
     Numbers are the pipeline's values for the 2026-10-16 snapshot. If you change a rule here, change pipeline.py too. -->

# How this works

Oct 16, 2026 · @Bharat

## Summary

The command center turns three streams of work into one weekly cycle: connector requests, trending open-source agent skills, and marketplace listings.

Every Friday, each new ask is matched to a tool, deduped, scored by a model fitted on past launches, and given an owner, a decision (build, partner, decline or need info) and a reply. Skills spotted on GitHub, X and builder communities are ranked by predicted installs, checked against five compliance gates, packaged as SKILL.md, tested and launched on a steady cadence. Every listing is checked against one template. A written status goes out at the end of the week.

Three featured items show the whole path. **Brightpath Analytics** was asked for 6 times through 3 channels; it scores 93/100, is Urgent, and goes to engineering with a build brief. **sketchwright**, a technical illustration skill, passes every gate, goes from 10/12 to 12/12 in QA, and launches crediting its creator. **Granite Docs** and **Chartcraft**, two high-traffic listings, go from 1/8 and 2/8 checks to 8/8.

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
3. **Score.** A fitted model gives each tool its chance of adoption; the rubric turns that into a tier. *Decision: how much does this matter?*
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

### The model

We don't hand-pick weights. A logistic regression is fitted on 260 connectors we launched before, using the signals we had when they were requested.

- **Label:** 50+ weekly active orgs 90 days after launch (47% of past launches).
- **Signals:** company size (log employees), headcount growth over 12 months, online traction (log mentions in 90 days), customers asking (log), and the share of asks from Enterprise customers.
- **Fit:** iteratively reweighted least squares in numpy, the same method statsmodels uses. `validate.py` refits it with plain gradient descent and checks every score matches within 1 point.

| Signal | Coefficient | Std. error |
|---|---|---|
| Company size (log10 employees) | 0.52 | 0.22 |
| Growth (headcount, 12 months) | 1.10 | 0.84 |
| Online traction (log10 mentions) | 0.93 | 0.21 |
| Customers asking (log) | 0.90 | 0.25 |
| Enterprise share | 1.00 | 0.73 |

Growth and Enterprise share have large standard errors: the direction is right but the size is uncertain with 260 launches. Refitting each quarter narrows this.

### Validation

A quarter of past launches (68) were held out and never used in fitting.

- **Holdout AUC 0.78.** A random adopted connector outscores a random non-adopted one 78% of the time.
- **Baseline AUC 0.72** for "most asks wins", ranking by request count alone. The model adds size, traction and customer mix on top.
- **Calibration:** in five bands of held-out launches, predicted and actual adoption rates track each other (chart on the Intake page).

### The rubric

The score is the predicted chance of adoption, 0–100.

| Tier | Rule |
|---|---|
| Urgent | 75+, or 55+ with a blocked deal of $100K+ |
| High | 55–74 |
| Medium | 35–54 |
| Low | Below 35 |

The blocked-deal rule is the one judgment call on top of the model: revenue already waiting on a connector makes a strong request time-sensitive. This week: 6 Urgent, 17 High, 36 Medium, 51 Low.

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

**To the Product Lead (22 this week):**

- Partnerships: the vendor runs its own MCP server and demand is Medium or higher.
- Hard calls: strong demand (High or Urgent) but no public API, where we could ask the vendor to ship an API or MCP server.
- Hard calls: a blocked deal of $250K+ on a tool the model rates Medium or Low.

**To engineering (12 briefs):** demand (customers, Enterprise share, channels, blocked deals), why the model rates it, what customers want to do, API and auth, acceptance criteria, and a draft listing that already passes the template.

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

All data is synthetic, generated with a fixed seed. The generator plants real relationships (bigger, faster-growing, more-discussed tools adopt more often; skill momentum drives installs), and the models recover them from the data alone. That shows the method works end to end. It does not prove these coefficients hold for a real marketplace. With real data, the same code would be fitted on real launch outcomes, and we would expect weaker fits than the 0.93 here.

## Decision log

| Decision | Why |
|---|---|
| Fit the priority score instead of hand-picking weights | A score that decides what engineering builds should be learned from what was used, and tested on launches it never saw |
| Label = 50+ weekly active orgs at day 90 | Adoption, not launch, is the outcome that matters; 90 days lets slow-moving Enterprise orgs show up |
| Blocked deal can lift High to Urgent | Revenue already waiting is time-sensitive in a way the adoption model can't see |
| Vendor-run MCP → Partner | The vendor maintains it; building our own would duplicate their work |
| Weekly Friday triage | One fixed pass guarantees the 5-business-day SLA and gives the status report a rhythm |
| Momentum over total stars for skills | On held-out ports, recent momentum ranks real installs far better than lifetime stars |
| Local stdio and host binaries are hard fails | The platform runs remote transports in a sandbox; those skills can't run there |
| Listing template as checks a script can run | A rule a script can check is enforced on every release, not just reviewed once |
