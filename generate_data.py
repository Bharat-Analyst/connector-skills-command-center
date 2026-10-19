"""
generate_data.py — creates the raw extracts that pipeline.py reads.

Stands in for the places connector and skill work actually arrives from. Like the
real thing, it is messy on purpose: the same tool is asked for under different
spellings in different channels, some asks don't name a tool at all, some tools
are already live or already in the backlog, half the old backlog has no priority
or owner, and many marketplace listings drift from the template.

Outputs (data/raw/):
    intake_forms.csv          connector request form submissions
    slack_requests.csv        messages in the #connector-requests channel
    direct_asks.csv           asks sent straight to the PM by sales / CS / partners
    linear_issues.csv         the existing Linear backlog (with customer request counts)
    live_catalog.csv          connectors already in the marketplace
    companies.csv             research signals per tool: size, growth, traction, API / MCP
    past_connector_launches.csv  connectors we launched before, with request-time signals
                              and whether they reached adoption (training data for the model)
    skill_candidates.csv      open-source agent skills spotted on GitHub, X and communities
    past_skill_ports.csv      skills we ported before, with signals at port time and installs
    skill_outreach.csv        creator permission requests and attribution text
    qa_runs.csv               test prompts run against skill ports (pass / fail)
    listings.csv              every marketplace listing (connector, skill, plugin) + monthly views
    listing_rewrites.csv      hand-written rewrites of listings (the copywriting work)

Seeded (42) so every run produces identical files. Every name is made up.
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
AS_OF_DATE = pd.Timestamp("2026-10-16")            # Friday: weekly triage day
INTAKE_START = pd.Timestamp("2026-08-22")          # 8 weeks of intake under the new process
OUT = Path(__file__).parent / "data" / "raw"

rng = np.random.default_rng(SEED)

# -----------------------------------------------------------------------------
# Name pools (all fictional)
# -----------------------------------------------------------------------------
PREFIXES = [
    "Acme", "Bluefin", "Cobalt", "Driftwood", "Ember", "Fernhill", "Granite", "Harbor",
    "Ironleaf", "Juniper", "Kestrel", "Lumen", "Maple", "Nimbus", "Orchard", "Pinecrest",
    "Quarry", "Redwood", "Saltmarsh", "Tidewater", "Upland", "Vantage", "Willow", "Zephyr",
    "Alder", "Basalt", "Cinder", "Dovetail", "Elmstead", "Foxglove", "Gullwing", "Heron",
    "Indigo", "Jetty", "Kiln", "Lattice", "Meridian", "Northgate", "Oakum", "Prism",
]
CATEGORIES = {
    "CRM": ["CRM", "Sales"],
    "Analytics": ["Analytics", "Metrics", "Insights"],
    "Payments": ["Payments", "Pay", "Billing"],
    "HR": ["HR", "People", "Payroll"],
    "Project management": ["Projects", "Tasks", "Boards"],
    "Docs & notes": ["Docs", "Notes", "Wiki"],
    "Design": ["Design", "Canvas", "Studio"],
    "Developer tools": ["Deploy", "CI", "Logs"],
    "Support": ["Support", "Helpdesk", "Desk"],
    "Marketing": ["Mail", "Campaigns", "Social"],
    "Data": ["Data", "Warehouse", "Sync"],
    "Security": ["Shield", "Vault", "Identity"],
}
AUTH = ["OAuth 2.0", "OAuth 2.0", "OAuth 2.0", "API key", "API key"]
PLANS = ["Free", "Team", "Team", "Enterprise"]
ORG_WORDS = ["Labs", "Group", "Systems", "Co", "Partners", "Works", "Health", "Retail", "Bank", "Media"]

USE_CASES = {
    "CRM": ["pull deal notes before calls", "update opportunities from meeting notes", "summarize pipeline by stage"],
    "Analytics": ["ask questions about dashboards", "explain a metric drop", "pull weekly KPIs into a report"],
    "Payments": ["look up failed payments", "reconcile payouts", "summarize churned subscriptions"],
    "HR": ["answer policy questions", "look up PTO balances", "draft onboarding plans"],
    "Project management": ["create tasks from meeting notes", "summarize sprint status", "find blocked tickets"],
    "Docs & notes": ["search team docs", "turn notes into a spec", "keep docs in sync"],
    "Design": ["describe a design file", "export assets", "review a mockup"],
    "Developer tools": ["read deploy logs", "explain a failed build", "open incidents from alerts"],
    "Support": ["summarize open tickets", "draft replies to tickets", "find recurring issues"],
    "Marketing": ["draft campaign emails", "report campaign results", "schedule posts"],
    "Data": ["query tables in plain English", "describe a schema", "check a pipeline run"],
    "Security": ["review access requests", "summarize alerts", "look up user permissions"],
}

# The model's "truth" for connector adoption (the pipeline never sees these; it re-fits them).
# Bigger, faster-growing, more-talked-about tools that many orgs (and enterprises) ask for
# are the ones that reach 50+ weekly active orgs within 90 days of launch.
TRUE_ADOPTION = {"intercept": -0.35, "log_employees": 0.55, "growth": 1.6,
                 "log_mentions": 0.85, "log_requesting_orgs": 0.9, "enterprise_share": 1.1}


def pick(seq):
    return seq[rng.integers(len(seq))]


def business_day_between(start, end):
    """A random weekday timestamp between start and end (requests arrive on workdays)."""
    while True:
        d = start + pd.Timedelta(days=int(rng.integers(0, (end - start).days + 1)))
        if d.weekday() < 5:
            return d + pd.Timedelta(hours=int(rng.integers(8, 19)), minutes=int(rng.integers(0, 60)))


# -----------------------------------------------------------------------------
# Companies (the tools people ask us to connect to) + research signals
# -----------------------------------------------------------------------------
def make_companies():
    rows, used = [], set()
    # Featured tools, planted with exact profiles so the story is stable.
    featured = [
        dict(company_name="Brightpath Analytics", domain="brightpath.io", category="Analytics",
             employees=920, headcount_growth_12m=0.48, mentions_90d=6400, api_type="Public API",
             auth="OAuth 2.0", aliases="Brightpath|BrightPath|brightpath.io|Bright Path"),
        dict(company_name="Larkspur Payments", domain="larkspurpay.com", category="Payments",
             employees=4100, headcount_growth_12m=0.22, mentions_90d=9800, api_type="Official MCP (remote)",
             auth="OAuth 2.0", aliases="Larkspur|LarkspurPay|larkspurpay.com"),
        dict(company_name="Pebblework Notes", domain="pebblework.app", category="Docs & notes",
             employees=12, headcount_growth_12m=0.05, mentions_90d=40, api_type="No public API",
             auth="", aliases="Pebblework|pebblework.app"),
        dict(company_name="Granite Docs", domain="granitedocs.com", category="Docs & notes",
             employees=2600, headcount_growth_12m=0.18, mentions_90d=7200, api_type="Public API",
             auth="OAuth 2.0", aliases="GraniteDocs|granitedocs.com"),
    ]
    for f in featured:
        used.add(f["company_name"])
        rows.append(f)

    api_types = ["Public API"] * 58 + ["Official MCP (remote)"] * 11 + ["Official MCP (local only)"] * 6 \
        + ["No public API"] * 19 + ["Unknown"] * 6
    while len(rows) < 240:
        cat = pick(list(CATEGORIES))
        name = f"{pick(PREFIXES)} {pick(CATEGORIES[cat])}"
        if name in used:
            continue
        used.add(name)
        employees = int(np.clip(rng.lognormal(5.0, 1.4), 5, 60000))
        api = pick(api_types)
        slug = name.lower().replace(" ", "")
        rows.append(dict(
            company_name=name, domain=f"{slug}.com", category=cat, employees=employees,
            headcount_growth_12m=round(float(np.clip(rng.normal(0.14, 0.17), -0.3, 0.9)), 2),
            mentions_90d=int(np.clip(rng.lognormal(5.6, 1.3) * (employees / 300) ** 0.25, 5, 80000)),
            api_type=api, auth="" if api in ("No public API", "Unknown") else pick(AUTH),
            aliases=f"{name.split()[0]}{name.split()[1]}|{slug}.com",
        ))
    df = pd.DataFrame(rows)
    df.insert(0, "company_id", [f"CO-{i:04d}" for i in range(1, len(df) + 1)])
    return df


# -----------------------------------------------------------------------------
# Live catalog + Linear backlog
# -----------------------------------------------------------------------------
def make_catalog_and_backlog(companies):
    featured = {"Brightpath Analytics", "Larkspur Payments", "Pebblework Notes"}
    pool = companies[~companies.company_name.isin(featured)]
    buildable = pool[pool.api_type.isin(["Public API", "Official MCP (remote)"])]

    live = buildable.sample(70, random_state=SEED).copy()
    # Granite Docs is live (its listing is one of the two rewrites).
    if "Granite Docs" not in set(live.company_name):
        live = pd.concat([live.iloc[:-1], companies[companies.company_name == "Granite Docs"]])
    catalog = pd.DataFrame({
        "connector_id": [f"CN-{i:03d}" for i in range(1, len(live) + 1)],
        "connector_name": live.company_name.values,
        "category": live.category.values,
        "launched_on": [str((pd.Timestamp("2025-03-01") + pd.Timedelta(days=int(d))).date())
                        for d in rng.integers(0, 560, len(live))],
    })

    rest = pool[~pool.company_name.isin(catalog.connector_name)]
    backlog_cos = rest.sample(62, random_state=SEED + 1)
    rows = []
    for i, (_, c) in enumerate(backlog_cos.iterrows()):
        created = pd.Timestamp("2026-01-05") + pd.Timedelta(days=int(rng.integers(0, 225)))
        prioritized = rng.random() < 0.35      # most of the old backlog was never scored
        orgs = int(rng.integers(1, 9))
        rows.append(dict(
            issue_id=f"CON-{101 + i}",
            title=f"Connector request: {c.company_name}" if rng.random() < 0.6 else f"{c.company_name.lower()} integration?",
            created_at=str(created.date()),
            status=pick(["Triage", "Triage", "Backlog", "Backlog", "Backlog", "Todo"]),
            priority=pick(["High", "Medium", "Low"]) if prioritized else "",
            assignee=pick(["Integrations Eng – Pod A", "Integrations Eng – Pod B", "Connector PM"]) if rng.random() < 0.45 else "",
            customer_request_count=orgs,
            enterprise_customer_count=int(rng.binomial(orgs, 0.3)),
            last_reply_at=str((created + pd.Timedelta(days=int(rng.integers(1, 30)))).date()) if rng.random() < 0.4 else "",
        ))
    return catalog, pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# New intake: forms, Slack, direct asks (last 8 weeks)
# -----------------------------------------------------------------------------
def spelling(company):
    """How a requester might write the tool's name."""
    options = [company.company_name, company.company_name.lower(), company.domain]
    options += [a for a in company.aliases.split("|") if a]
    return pick(options)


def requester_org():
    return f"{pick(PREFIXES)} {pick(ORG_WORDS)}"


def make_intake(companies, catalog, backlog):
    # Demand is skewed: a few tools get asked for constantly, most once or twice.
    ordinary = companies[~companies.company_name.isin(
        ["Brightpath Analytics", "Larkspur Payments", "Pebblework Notes", "Granite Docs"])]
    weights = rng.pareto(1.3, len(ordinary)) + 0.2
    weights = weights / weights.sum()

    forms, slack, direct = [], [], []

    def add(channel, company, when, plan=None, blocked=0, text=None):
        cat = company.category if company is not None else pick(list(CATEGORIES))
        plan = plan or pick(PLANS)
        use = pick(USE_CASES[cat])
        org = requester_org()
        if channel == "form":
            forms.append(dict(submitted_at=when, submitter_email=f"admin@{org.lower().replace(' ', '')}.com",
                              requester_org=org, plan=plan,
                              tool_requested=text if text is not None else spelling(company),
                              use_case=use, blocked_deal_arr=blocked))
        elif channel == "slack":
            body = text if text is not None else pick([
                f"any chance we get a {spelling(company)} connector? customer wants to {use}",
                f"+1 for {spelling(company)}, {org} asked again ({plan} plan)",
                f"customer on {plan} asking for {spelling(company)} — they want to {use}",
            ])
            slack.append(dict(posted_at=when, channel="#connector-requests",
                              posted_by=pick(["AE", "CSM", "SE", "Support"]), requester_org=org, plan=plan,
                              message=body, blocked_deal_arr=blocked))
        else:
            direct.append(dict(asked_at=when, from_role=pick(["AE", "CSM", "Partner manager"]),
                               requester_org=org, plan=plan,
                               tool_mentioned=text if text is not None else spelling(company),
                               notes=f"Customer wants to {use}.", blocked_deal_arr=blocked))

    # Featured: Brightpath Analytics — 6 asks, 3 channels, one blocked enterprise deal.
    bp_row = companies[companies.company_name == "Brightpath Analytics"].iloc[0]
    for ch, day, text, plan, blocked in [
        ("form", "2026-09-28", "Brightpath", "Enterprise", 0),
        ("slack", "2026-09-30", "any chance we get a BrightPath connector? 2 enterprise customers want to explain a metric drop", "Enterprise", 0),
        ("form", "2026-10-05", "brightpath.io", "Team", 0),
        ("direct", "2026-10-07", "Brightpath Analytics", "Enterprise", 180_000),
        ("slack", "2026-10-12", "+1 for Bright Path, Meridian Bank asked again (Enterprise plan)", "Enterprise", 0),
        ("form", "2026-10-14", "BrightPath Analytics", "Enterprise", 0),
    ]:
        add(ch, bp_row, pd.Timestamp(day) + pd.Timedelta(hours=10), plan=plan, blocked=blocked, text=text)

    lp = companies[companies.company_name == "Larkspur Payments"].iloc[0]
    for ch, day, plan in [("form", "2026-09-08", "Enterprise"), ("direct", "2026-09-22", "Enterprise"),
                          ("slack", "2026-10-01", "Team"), ("form", "2026-10-09", "Enterprise")]:
        add(ch, lp, pd.Timestamp(day) + pd.Timedelta(hours=11), plan=plan)

    pb = companies[companies.company_name == "Pebblework Notes"].iloc[0]
    add("form", pb, pd.Timestamp("2026-10-13 09:30"), plan="Free", text="Pebblework")

    # Featured Need info: a Slack ask that never names the tool.
    add("slack", None, pd.Timestamp("2026-10-15 15:10"), plan="Enterprise",
        text="can we get a connector for the HR tool we use? customer keeps asking")

    # Everything else.
    channels = ["form"] * 50 + ["slack"] * 32 + ["direct"] * 18
    for _ in range(330):
        when = business_day_between(INTAKE_START, AS_OF_DATE)
        ch = pick(channels)
        if rng.random() < 0.03:                # vague asks with no tool name
            vague = pick(["the tool our finance team uses", "our internal wiki", "that new AI notes app",
                          "whatever CRM the customer has", "a design tool"])
            text = vague if ch != "slack" else f"customer asking for a connector to {vague}"
            add(ch, None, when, text=text)
            continue
        c = ordinary.iloc[rng.choice(len(ordinary), p=weights)]
        plan = pick(PLANS)
        blocked = int(rng.choice([50_000, 80_000, 120_000, 250_000, 400_000])) \
            if (ch == "direct" and plan == "Enterprise" and rng.random() < 0.5) else 0
        add(ch, c, when, plan=plan, blocked=blocked)

    def finish(rows, col):
        df = pd.DataFrame(rows).sort_values(col).reset_index(drop=True)
        df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M")
        return df

    f = finish(forms, "submitted_at");  f.insert(0, "submission_id", [f"F-{i:04d}" for i in range(1, len(f) + 1)])
    s = finish(slack, "posted_at");     s.insert(0, "message_id", [f"S-{i:04d}" for i in range(1, len(s) + 1)])
    d = finish(direct, "asked_at");     d.insert(0, "ask_id", [f"D-{i:04d}" for i in range(1, len(d) + 1)])
    return f, s, d


# -----------------------------------------------------------------------------
# History for the connector adoption model
# -----------------------------------------------------------------------------
def make_past_launches(n=260):
    rows = []
    for i in range(n):
        log_emp = float(np.clip(rng.normal(2.6, 0.75), 0.8, 4.7))
        growth = float(np.clip(rng.normal(0.15, 0.17), -0.3, 0.9))
        log_mentions = float(np.clip(rng.normal(2.6, 0.7) + 0.25 * (log_emp - 2.6), 0.7, 4.9))
        orgs = int(np.clip(rng.lognormal(1.0, 0.8), 1, 60))
        ent_share = float(np.clip(rng.beta(2, 4), 0, 1))
        t = TRUE_ADOPTION
        z = (t["intercept"] + t["log_employees"] * (log_emp - 2.6) + t["growth"] * (growth - 0.15)
             + t["log_mentions"] * (log_mentions - 2.6) + t["log_requesting_orgs"] * (np.log1p(orgs) - 1.2)
             + t["enterprise_share"] * (ent_share - 0.33))
        adopted = int(rng.random() < 1 / (1 + np.exp(-z)))
        rows.append(dict(
            connector=f"{pick(PREFIXES)} {pick(sum(CATEGORIES.values(), []))} (2024-{i:03d})",
            launched_on=str((pd.Timestamp("2024-01-08") + pd.Timedelta(days=int(rng.integers(0, 540)))).date()),
            employees=int(round(10 ** log_emp)), headcount_growth_12m=round(growth, 2),
            mentions_90d=int(round(10 ** log_mentions)), requesting_orgs=orgs,
            enterprise_share=round(ent_share, 2),
            weekly_active_orgs_day90=int(rng.integers(50, 400)) if adopted else int(rng.integers(0, 50)),
        ))
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Skills: candidates, history, outreach, QA
# -----------------------------------------------------------------------------
SKILL_CATEGORIES = ["Illustration & diagrams", "Reverse engineering", "Docs & writing", "Data analysis",
                    "Testing", "Design", "DevOps", "Research", "Spreadsheets", "Security review"]
SKILL_WORDS = ["forge", "smith", "wright", "kit", "lens", "scribe", "pilot", "craft", "loom", "sketch"]
SKILL_ROOTS = ["chart", "slide", "schema", "trace", "diff", "spec", "lint", "map", "query", "sheet",
               "frame", "probe", "atlas", "patch", "graph", "proof", "brief", "audit", "plot", "relay"]
LICENSES = ["MIT"] * 46 + ["Apache-2.0"] * 22 + ["BSD-3-Clause"] * 6 + ["ISC"] * 3 + ["GPL-3.0"] * 9 \
    + ["AGPL-3.0"] * 4 + ["No license"] * 7 + ["Custom"] * 3
CREATORS = ["inkline", "tessaroo", "byteforager", "mkellner", "pallas-dev", "quietcompiler", "rhea-builds",
            "nullpointer_nia", "ogunlabs", "vectorvale", "hexwren", "dunmore", "kaizen_kit", "lowtide",
            "marisol-codes", "fennick", "arclight-oss", "j0hanna", "sprocketeer", "tamsin_t"]

# Truth for skill installs (pipeline re-fits it): fast-rising repos that people talk
# about on X and in communities get installed; total stars matter less than momentum.
TRUE_INSTALLS = {"intercept": -0.6, "log_stars_7d": 0.62, "log_x_mentions": 0.35,
                 "log_community": 0.22, "log_total_stars": 0.10, "noise": 0.45}


def skill_signals():
    stars = int(np.clip(rng.lognormal(7.0, 1.2), 30, 90000))
    stars_7d = int(np.clip(stars * rng.lognormal(-2.6, 0.9), 0, 20000))
    x_mentions = int(np.clip(stars_7d * rng.lognormal(-1.0, 0.8), 0, 9000))
    community = int(np.clip(stars_7d * rng.lognormal(-1.8, 0.9), 0, 3000))
    return stars, stars_7d, x_mentions, community


def predicted_log_installs(stars, stars_7d, x, community):
    t = TRUE_INSTALLS
    return (t["intercept"] + t["log_stars_7d"] * np.log1p(stars_7d) + t["log_x_mentions"] * np.log1p(x)
            + t["log_community"] * np.log1p(community) + t["log_total_stars"] * np.log1p(stars))


def make_skills():
    used = {"sketchwright", "bincrack", "chartcraft"}
    cands = [
        dict(repo="inkline/sketchwright", skill_name="sketchwright", category="Illustration & diagrams",
             description="Turns a plain-English description into a clean technical illustration (SVG).",
             license="MIT", stars=8400, stars_7d=2900, x_mentions_7d=1850, community_mentions_7d=420,
             transport="None (instructions + scripts)", sandbox_needs="File write (outputs folder)",
             creator="inkline", first_seen="2026-09-29"),
        dict(repo="hexwren/bincrack", skill_name="bincrack", category="Reverse engineering",
             description="Walks through a compiled binary: strings, symbols, control flow, likely behavior.",
             license="GPL-3.0", stars=12100, stars_7d=2400, x_mentions_7d=1300, community_mentions_7d=510,
             transport="Local stdio only", sandbox_needs="Host binaries (ghidra, radare2)",
             creator="hexwren", first_seen="2026-10-02"),
    ]
    while len(cands) < 64:
        name = f"{pick(SKILL_ROOTS)}{pick(SKILL_WORDS)}"
        if name in used:
            continue
        used.add(name)
        stars, s7, x, comm = skill_signals()
        creator = pick(CREATORS)
        cat = pick(SKILL_CATEGORIES)
        cands.append(dict(
            repo=f"{creator}/{name}", skill_name=name, category=cat,
            description=f"An agent skill for {cat.lower()}.",
            license=pick(LICENSES), stars=stars, stars_7d=s7, x_mentions_7d=x, community_mentions_7d=comm,
            transport=pick(["None (instructions + scripts)"] * 6 + ["Remote MCP (HTTP)"] * 2 + ["Local stdio only"] * 2),
            sandbox_needs=pick(["None"] * 5 + ["File write (outputs folder)"] * 3 + ["Network (allow-listed APIs)"] * 2
                               + ["Host binaries"] + ["GPU"]),
            creator=creator,
            first_seen=str((AS_OF_DATE - pd.Timedelta(days=int(rng.integers(1, 60)))).date()),
        ))
    cands = pd.DataFrame(cands)

    # History: skills we ported before (training data for the installs model).
    hist = []
    for i in range(90):
        stars, s7, x, comm = skill_signals()
        log_inst = predicted_log_installs(stars, s7, x, comm) + rng.normal(0, TRUE_INSTALLS["noise"])
        hist.append(dict(
            skill_name=f"{pick(SKILL_ROOTS)}{pick(SKILL_WORDS)}-{i:02d}",
            launched_on=str((pd.Timestamp("2026-01-05") + pd.Timedelta(weeks=int(i // 2.2))).date()),
            stars_at_port=stars, stars_7d_at_port=s7, x_mentions_7d_at_port=x, community_mentions_7d_at_port=comm,
            installs_30d=int(round(np.expm1(log_inst))),
        ))
    hist = pd.DataFrame(hist)

    # Outreach to creators (permission + attribution).
    outreach = []
    for _, c in cands.iterrows():
        if c.skill_name == "sketchwright":
            outreach.append(dict(repo=c.repo, creator=c.creator, requested_on="2026-10-01", status="Granted",
                                 responded_on="2026-10-02",
                                 attribution_text="Ported from inkline/sketchwright by @inkline (MIT)."))
            continue
        if c.skill_name == "bincrack":
            outreach.append(dict(repo=c.repo, creator=c.creator, requested_on="2026-10-05", status="Pending",
                                 responded_on="", attribution_text=""))
            continue
        status = pick(["Granted"] * 5 + ["Pending"] * 3 + ["Declined"] + ["Not requested"] * 3)
        req = AS_OF_DATE - pd.Timedelta(days=int(rng.integers(2, 30)))
        outreach.append(dict(
            repo=c.repo, creator=c.creator,
            requested_on="" if status == "Not requested" else str(req.date()), status=status,
            responded_on=str((req + pd.Timedelta(days=int(rng.integers(1, 6)))).date()) if status in ("Granted", "Declined") else "",
            attribution_text=f"Ported from {c.repo} by @{c.creator} ({c.license})." if status == "Granted" and rng.random() < 0.85 else "",
        ))
    outreach = pd.DataFrame(outreach)
    return cands, hist, outreach


QA_PROMPTS = {
    "sketchwright": [
        ("Draw a diagram of a load balancer in front of three web servers", "core"),
        ("Illustrate the TCP three-way handshake as a sequence diagram", "core"),
        ("Make a labeled cutaway of a centrifugal pump", "core"),
        ("Sketch our data pipeline: S3 → Spark → warehouse → dashboard", "core"),
        ("Turn this list of steps into a flowchart", "core"),
        ("Draw a circuit for an LED with a 220 ohm resistor", "core"),
        ("Make the previous diagram dark-mode friendly", "follow-up"),
        ("Export it as PNG instead of SVG", "follow-up"),
        ("Draw something with 40+ nodes: a full microservices map", "stress"),
        ("Illustrate with no description at all", "edge"),
        ("Draw a copyrighted cartoon character", "safety"),
        ("Write the SVG to my home folder", "sandbox"),
    ],
}


def make_qa(cands):
    rows = []
    # sketchwright: round 1 had two failures (stress + sandbox), fixed, round 2 clean.
    for rnd, fails in [(1, {"stress", "sandbox"}), (2, set())]:
        for i, (prompt, kind) in enumerate(QA_PROMPTS["sketchwright"], 1):
            failed = kind in fails
            note = ""
            if failed and kind == "stress":
                note = "Layout overlapped past ~30 nodes; added auto-layout fallback"
            elif failed and kind == "sandbox":
                note = "Tried to write outside outputs folder; restricted path in SKILL.md"
            rows.append(dict(skill_name="sketchwright", round=rnd, tested_on=f"2026-10-{8 + 5 * (rnd - 1):02d}",
                             prompt_id=f"SW-{i:02d}", prompt=prompt, prompt_type=kind,
                             passed=int(not failed), notes=note))
    # A few other ports currently in QA.
    others = cands[(cands.license.isin(["MIT", "Apache-2.0"])) &
                   (cands.skill_name != "sketchwright")].nlargest(3, "stars_7d")
    for _, c in others.iterrows():
        for i in range(1, 13):
            kind = ["core"] * 6 + ["follow-up"] * 2 + ["stress", "edge", "safety", "sandbox"]
            rows.append(dict(skill_name=c.skill_name, round=1, tested_on="2026-10-15",
                             prompt_id=f"{c.skill_name[:2].upper()}-{i:02d}",
                             prompt=f"Representative {kind[i - 1]} prompt #{i}", prompt_type=kind[i - 1],
                             passed=int(rng.random() < 0.88), notes=""))
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Marketplace listings (with template drift) + hand-written rewrites
# -----------------------------------------------------------------------------
def messy_listing(name, kind, category, author):
    """A listing that may break some template rules, the way catalogs drift."""
    verb_caps = [f"Search {category.lower()} records", f"Summarize recent activity",
                 f"Create and update items", f"Answer questions about your data", f"Export results"]
    title = name
    if rng.random() < 0.30:
        title = pick([f"{name} Connector", f"{name} MCP Integration", f"The {name} plugin", f"{name.upper()}"])
    summary = f"Connect to {name} and work with your {category.lower()} data in chat."
    if rng.random() < 0.30:
        summary = pick(["", f"{name} is a leading platform for {category.lower()} used by thousands of teams around the world to get work done faster and better.",
                        f"integration for {name}"])
    n_caps = int(rng.choice([0, 1, 2, 3, 4, 5, 6, 7], p=[.08, .07, .10, .30, .25, .12, .05, .03]))
    caps = [pick(verb_caps) for _ in range(n_caps)]
    if caps and rng.random() < 0.25:
        caps[0] = "it can " + caps[0].lower()
    prompts_pool = [f"What changed in {name} this week?", f"Summarize my open {category.lower()} items",
                    f"Find anything in {name} about the Q3 launch", f"Draft an update from my {name} data"]
    n_prompts = int(rng.choice([0, 1, 2, 3, 4], p=[.15, .15, .20, .35, .15]))
    return dict(
        title=title, summary=summary, capabilities="|".join(caps),
        permissions="" if rng.random() < 0.25 else pick(["Read", "Read and write", "Read, write, delete"]),
        required_connectors="None" if kind != "plugin" or rng.random() < 0.5 else ("" if rng.random() < 0.4 else name),
        try_asking="|".join(prompts_pool[:n_prompts]),
        author="" if rng.random() < 0.18 else author,
    )


def make_listings(catalog, hist_skills):
    rows = []
    for _, c in catalog.iterrows():
        rows.append(dict(kind="connector", name=c.connector_name, category=c.category,
                         author=f"{c.connector_name} (verified partner)" if rng.random() < 0.3 else "Marketplace team"))
    for _, s in hist_skills.sample(48, random_state=SEED).iterrows():
        rows.append(dict(kind="skill", name=s.skill_name.split("-")[0], category=pick(SKILL_CATEGORIES),
                         author=f"Ported from @{pick(CREATORS)}"))
    for i in range(22):
        nm = f"{pick(PREFIXES)} {pick(['Toolkit', 'Assistant', 'Pack', 'Workflows'])}"
        rows.append(dict(kind="plugin", name=nm, category=pick(list(CATEGORIES)), author="Marketplace team"))

    out = []
    for i, r in enumerate(rows, 1):
        lst = messy_listing(r["name"], r["kind"], r["category"], r["author"])
        out.append(dict(listing_id=f"L-{i:03d}", kind=r["kind"], name=r["name"], category=r["category"], **lst,
                        monthly_views=int(np.clip(rng.lognormal(7.0, 1.1), 40, 90000))))
    df = pd.DataFrame(out)

    # Featured: two high-traffic listings that break the template (the interview's rewrite task).
    granite = df.index[df.name == "Granite Docs"][0]
    df.loc[granite, ["title", "summary", "capabilities", "permissions", "try_asking", "author", "monthly_views"]] = [
        "Granite Docs MCP Integration",
        "Granite Docs is the collaborative documentation platform trusted by over 40,000 teams, and with this integration you can now access it.",
        "it can search docs|Docs",
        "",
        "granite",
        "",
        41200,
    ]
    df.loc[len(df)] = dict(listing_id=f"L-{len(df) + 1:03d}", kind="skill", name="chartcraft",
                           category="Data analysis", title="CHARTCRAFT - the best charting skill",
                           summary="", capabilities="Makes charts|charts from csv files|Lots of chart types and themes and more",
                           permissions="Read and write", required_connectors="",
                           try_asking="", author="Ported from @lowtide", monthly_views=28700)
    return df


def make_rewrites(listings):
    granite = listings[listings.name == "Granite Docs"].iloc[0]
    chart = listings[listings.name == "chartcraft"].iloc[0]
    return pd.DataFrame([
        dict(listing_id=granite.listing_id, rewritten_on="2026-10-14", rewritten_by="Connector PM",
             title="Granite Docs",
             summary="Search, read and update your team's Granite Docs pages from chat.",
             capabilities="Search pages and spaces by keyword or owner|Read a page and summarize it|Create a new page from a draft|Update an existing page section|List recent edits in a space",
             permissions="Read and write (pages you can already access)",
             required_connectors="None",
             try_asking="Find our onboarding doc for new engineers|Summarize the Q3 planning page in five bullets|Draft a release-notes page from this changelog",
             author="Granite Docs (verified partner)"),
        dict(listing_id=chart.listing_id, rewritten_on="2026-10-15", rewritten_by="Connector PM",
             title="Chartcraft",
             summary="Turn a CSV or table into a clear, labeled chart you can download.",
             capabilities="Build bar, line, scatter and area charts from a CSV|Pick a chart type that fits the data|Label axes, units and sources automatically|Export charts as PNG or SVG",
             permissions="Read files you upload; write charts to the outputs folder",
             required_connectors="None",
             try_asking="Chart monthly revenue from this CSV as a line chart|Compare these three regions in a bar chart|Which chart fits this data best?",
             author="Ported from lowtide/chartcraft by @lowtide (MIT)"),
    ])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    companies = make_companies()
    catalog, backlog = make_catalog_and_backlog(companies)
    forms, slack, direct = make_intake(companies, catalog, backlog)
    launches = make_past_launches()
    cands, hist, outreach = make_skills()
    qa = make_qa(cands)
    listings = make_listings(catalog, hist)
    rewrites = make_rewrites(listings)

    files = {
        "companies.csv": companies, "live_catalog.csv": catalog, "linear_issues.csv": backlog,
        "intake_forms.csv": forms, "slack_requests.csv": slack, "direct_asks.csv": direct,
        "past_connector_launches.csv": launches, "skill_candidates.csv": cands,
        "past_skill_ports.csv": hist, "skill_outreach.csv": outreach, "qa_runs.csv": qa,
        "listings.csv": listings, "listing_rewrites.csv": rewrites,
    }
    for name, df in files.items():
        df.to_csv(OUT / name, index=False)
        print(f"{name:30s} {len(df):5d} rows")


if __name__ == "__main__":
    main()
