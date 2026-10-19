# Connector & Skills Command Center: project guide for Claude

## What this is
A portfolio proof-of-concept for a **Connector & Skills Program Manager** role
(integration connectors, open-source AI agent skills, marketplace listings). It shows how I would:
- turn ad-hoc connector requests into a weekly, measurable intake pipeline,
- find, qualify, port and launch trending open-source agent skills, and
- keep every marketplace listing consistent as the catalog grows.

Personal project. All company names, people, repos and handles are fictional. All data is synthetic.

## Role responsibilities → modules (every module must map to one)
| # | Responsibility | Module / output |
|---|----------------|-----------------|
| 1a | Weekly triage | Intake queue from forms, request channel, direct asks; dedupe against live catalog + backlog |
| 1b | Research & scoring | Fitted adoption model → standard rubric points → Urgent / High / Medium / Low |
| 1c | Backlog management | Every request has owner, decision (build / partner / decline / need info), reply; Linear import CSV |
| 1d | Escalations & reporting | Product Lead escalations, engineering build briefs, weekly status summary |
| 2a | Trend spotting | Ranked skill candidates from GitHub + X + community signals (fitted install model) |
| 2b | Qualification & compliance | License, creator permission, attribution, remote MCP transport, sandbox gates |
| 2c | Porting & publishing | SKILL.md package, listing copy, "Try asking" prompts, QA test log |
| 2d | Launch | GitHub export workflow + launch cadence calendar |
| 3 | Listing consistency | Listing template, catalog audit, rewrites of high-traffic listings, pre-launch checklist |
| 4 | First-party plugins (future) | SME-authored SKILL.md recipe through the same QA + listing checklist |
| — | 90-day success metrics | Status page: SLA %, owner/decision/reply coverage, launch cadence, attribution, audit coverage |

## The story
Three featured items flow through every page:
- **Brightpath Analytics** connector request: asked 6 times through 3 channels → merged → scored Urgent → Build → engineering brief → launched with a clean listing.
- **sketchwright** (technical illustration skill on GitHub): trending → passes every compliance gate → ported to SKILL.md → QA'd → launched.
- **Two listing rewrites** of high-traffic entries that fail the template (mirrors the interview's practical assessment).
Plus one featured request per decision: Larkspur Payments (Partner), Pebblework Notes (Decline), an unnamed "HR tool" ask (Need info).

## Technical constraints (do not deviate without asking)
- **Python 3.11**, **pandas**, **numpy**. Models are fitted with numpy (logistic regression via IRLS, OLS), no extra dependencies.
- **No database.** CSV files in folders that mirror warehouse layers:
  - `data/raw/`: source extracts (form submissions, Slack request channel, direct asks, Linear issues,
    live catalog, company signals, skill candidates, past launches, listings + traffic)
  - `data/processed/`: cleaned, deduped, scored tables
  - `data/output/`: files we'd push to tools (Linear import CSV, build briefs, weekly status, SKILL.md ports)
- **Fixed random seed = 42** everywhere. Snapshot date 2026-10-16 (a Friday, the weekly triage day).
- **Scoring must be fitted to outcomes, not hand-picked weights**, and shown with holdout validation.
- **Front end:** static site in `/docs` (plain HTML/CSS/JS + Plotly.js from a pinned CDN version, no build tools)
  reading precomputed JSON in `docs/data/`. Hosted on GitHub Pages from `/docs` on `main`.
- No real company logos or trademarks. Open standards (MCP, SKILL.md, Linear as a tool name) are fine.

## Code style
- Simple, readable code. Small functions. Comments explain the business logic (why a threshold).
- Every assumption (SLA days, tier cut-offs, allowed licenses, QA pass bar) lives in one config block at the top of `pipeline.py`.
- One command runs the pipeline end to end; outputs are deterministic. `validate.py` is the last step and must pass.

## Working rules
- The owner is learning: briefly explain each decision and what each new file does.
- Work in **small steps**. After each step, **commit locally** with a clear message.
- Ask before adding dependencies or changing the constraints above.

## Wording rules
- Plain on-screen labels. Collaborative phrasing ("we could"). Never "I'd".
- Built-with-AI credit stays at the top of every page.

## Current files
- `generate_data.py` → `data/raw/*.csv` (13 files, seed 42, featured items planted).
- `pipeline.py` → processed tables, tool outputs (Linear CSV, briefs, SKILL.md package, escalations, weekly status),
  `docs/data/{intake,skills,catalog,status}.json` and `docs/files/` (copies the site links to). Ends by running `validate.py`.
- `content/how_this_works.md` — the written method; rendered by `docs/how-this-works.html`. Keep numbers in sync with the pipeline.
- Pages: index (weekly cycle), intake, skills, catalog (listings), status, how-this-works. Shared JS: `docs/assets/common.js`.
- Cross-page state is URL-only: `?tool=<slug>`, `?skill=<name>`, `?step=<1-8>`.
- Preview: `python3 -m http.server 8000 -d docs`.
