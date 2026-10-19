"""
pipeline.py — turns raw requests, community signals and listings into one weekly
operating picture: what we build, port, fix, and tell people.

Steps (mirrors "How this works"):
    1. Collect            read forms, Slack, direct asks, Linear, catalog, research signals
    2. Match and dedupe   find the tool each ask is about; merge repeats; check the live
                          catalog and the Linear backlog
    3. Score              fit an adoption model on past launches; score every open tool;
                          turn scores into Urgent / High / Medium / Low
    4. Decide             build / partner / decline / need info, with an owner and a reply;
                          escalations; engineering briefs; Linear import
    5. Spot skills        fit an installs model on past ports; rank open-source candidates
    6. Qualify and port   license, permission, attribution, transport, sandbox gates; QA logs;
                          SKILL.md packages and a launch calendar
    7. Keep listings consistent   audit every listing against the template; queue rewrites
    8. Report             weekly status and the 90-day success metrics
Last: validate.py recomputes the key numbers independently and fails loudly on any mismatch.
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
RAW, PROCESSED, OUTPUT, SITE = ROOT / "data/raw", ROOT / "data/processed", ROOT / "data/output", ROOT / "docs/data"

# =============================================================================
# ASSUMPTIONS — every judgment call lives here (documented on "How this works").
# =============================================================================
AS_OF_DATE = pd.Timestamp("2026-10-16")   # Friday: weekly triage day
SEED = 42
TRIAGE_WEEKDAY = 4                         # Friday. A weekly pass means no ask waits more than 5 business days.
SLA_BUSINESS_DAYS = 5                      # the 90-day target: every new ask triaged within 5 business days

# Connector adoption model: label = 50+ weekly active orgs 90 days after launch.
ADOPTION_THRESHOLD = 50
HOLDOUT_SHARE = 0.25                       # share of past launches kept aside to test the model
RIDGE = 1e-3                               # tiny penalty so the fit is stable; doesn't change the story

# Priority rubric: the fitted score (0–100 = chance of adoption) sets the tier.
# A blocked customer deal can lift a strong request to Urgent: revenue is waiting on it.
TIER_URGENT = 75
TIER_HIGH = 55
TIER_MEDIUM = 35
URGENT_BLOCKED_ARR = 100_000               # with a score of TIER_HIGH+, a deal this size makes it Urgent
ESCALATE_BLOCKED_ARR = 250_000             # a deal this size on a Medium/Low request is a hard call for the Product Lead
BUILD_SLOTS_PER_WEEK = 3                   # engineering can start ~3 connector builds a week

OWNER_PM = "Connector PM"
OWNER_PRODUCT_LEAD = "Product Lead"
ENG_PODS = ["Integrations Eng – Pod A", "Integrations Eng – Pod B"]

# Skills
ALLOWED_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"}
REVIEW_LICENSES = {"GPL-3.0", "AGPL-3.0", "MPL-2.0", "Custom"}   # copyleft or custom: legal review first
OK_TRANSPORTS = {"None (instructions + scripts)", "Remote MCP (HTTP)"}
OK_SANDBOX = {"None", "File write (outputs folder)", "Network (allow-listed APIs)"}
QA_PASS_BAR = 0.90                         # latest QA round must pass 90%+ of representative prompts
QA_MIN_PROMPTS = 10
LAUNCHES_PER_WEEK = 2                      # steady cadence the marketplace can absorb and announce

# Listings
LISTING_TITLE_MAX = 30
LISTING_SUMMARY_MAX = 90
CAPABILITIES_MIN, CAPABILITIES_MAX = 3, 5
TRY_ASKING_MIN = 3
TITLE_BANNED = ["connector", "integration", "mcp", "plugin", "skill", "the best", "the "]
TOP_PRIORITY_LISTINGS = 20                 # highest views × biggest gap: audited and rewritten first
REWRITES_PER_WEEK = 5

FEATURED = {"build": "Brightpath Analytics", "partner": "Larkspur Payments", "decline": "Pebblework Notes",
            "skill": "sketchwright", "blocked_skill": "bincrack", "listings": ["Granite Docs", "chartcraft"]}


def norm(text):
    """Lowercase letters and digits only, so 'BrightPath', 'Bright Path' and 'brightpath' match."""
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def to_json(obj, path):
    def default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) else float(o)
        if isinstance(o, (pd.Timestamp,)):
            return str(o.date())
        raise TypeError(type(o))
    path.write_text(json.dumps(obj, indent=1, default=default, ensure_ascii=False))


def records(df):
    return json.loads(df.to_json(orient="records", date_format="iso"))


# =============================================================================
# 1. Collect
# =============================================================================
def load():
    r = {p.stem: pd.read_csv(p, keep_default_na=False, na_values=[""]) for p in RAW.glob("*.csv")}
    return r


def unify_requests(raw):
    """One row per ask, whatever channel it came through."""
    f = raw["intake_forms"].rename(columns={"submission_id": "request_id", "submitted_at": "received_at",
                                            "tool_requested": "tool_text"})
    f["channel"] = "Form"
    s = raw["slack_requests"].rename(columns={"message_id": "request_id", "posted_at": "received_at",
                                              "message": "tool_text"})
    s["channel"] = "Slack"
    s["use_case"] = ""
    d = raw["direct_asks"].rename(columns={"ask_id": "request_id", "asked_at": "received_at",
                                           "tool_mentioned": "tool_text", "notes": "use_case"})
    d["channel"] = "Direct ask"
    d["use_case"] = d.use_case.str.replace("Customer wants to ", "", regex=False).str.rstrip(".")
    cols = ["request_id", "channel", "received_at", "requester_org", "plan", "tool_text", "use_case", "blocked_deal_arr"]
    req = pd.concat([f[cols], s[cols], d[cols]], ignore_index=True)
    req["received_at"] = pd.to_datetime(req.received_at)
    req["use_case"] = req.use_case.fillna("")
    req["blocked_deal_arr"] = req.blocked_deal_arr.fillna(0).astype(int)
    return req.sort_values("received_at").reset_index(drop=True)


# =============================================================================
# 2. Match and dedupe
# =============================================================================
def alias_index(companies):
    """Every way a tool's name is written → company. Longest alias wins when several match."""
    idx = {}
    for _, c in companies.iterrows():
        for a in [c.company_name, c.domain, *str(c.aliases).split("|")]:
            if a and len(norm(a)) >= 4:
                idx[norm(a)] = c.company_name
    return sorted(idx.items(), key=lambda kv: -len(kv[0]))


def match_tool(text, aliases):
    t = norm(text)
    for alias, name in aliases:
        if alias in t:
            return name
    return None


def match_and_dedupe(req, raw):
    aliases = alias_index(raw["companies"])
    req["tool"] = [match_tool(t, aliases) for t in req.tool_text]
    live = set(raw["live_catalog"].connector_name)
    backlog = raw["linear_issues"].copy()
    backlog["tool"] = [match_tool(t, aliases) for t in backlog.title]
    in_backlog = dict(zip(backlog.tool, backlog.issue_id))

    def where(tool):
        if pd.isna(tool):
            return "Tool not named"
        if tool in live:
            return "Already live"
        if tool in in_backlog:
            return "Merged into backlog issue"
        return "New tool"
    req["match_status"] = req.tool.map(where)
    req["linear_issue"] = req.tool.map(in_backlog)
    # The first ask for a tool opens (or joins) the issue; every later ask is a duplicate merged into it.
    req["is_duplicate"] = req.tool.notna() & req.duplicated("tool", keep="first")
    return req, backlog


# =============================================================================
# 3. Score: fit the adoption model, apply it, map to the rubric
# =============================================================================
FEATURES = ["log_employees", "headcount_growth", "log_mentions", "log_requesting_orgs", "enterprise_share"]
FEATURE_LABELS = {
    "log_employees": "Company size", "headcount_growth": "Growth (headcount, 12 months)",
    "log_mentions": "Online traction (mentions, 90 days)", "log_requesting_orgs": "Customers asking",
    "enterprise_share": "Share of asks from Enterprise customers",
}


def model_features(df, employees, growth, mentions, orgs, ent_share):
    return pd.DataFrame({
        "log_employees": np.log10(df[employees].clip(lower=1)),
        "headcount_growth": df[growth],
        "log_mentions": np.log10(df[mentions].clip(lower=1)),
        "log_requesting_orgs": np.log1p(df[orgs]),
        "enterprise_share": df[ent_share],
    })


def fit_logistic(X, y):
    """Logistic regression by iteratively reweighted least squares (what statsmodels does)."""
    Xd = np.column_stack([np.ones(len(X)), X])
    beta = np.zeros(Xd.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-Xd @ beta))
        W = p * (1 - p)
        H = Xd.T @ (Xd * W[:, None]) + RIDGE * np.eye(len(beta))
        step = np.linalg.solve(H, Xd.T @ (y - p) - RIDGE * beta)
        beta += step
        if np.abs(step).max() < 1e-9:
            break
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    return beta, se


def predict_logistic(beta, X):
    return 1 / (1 + np.exp(-(beta[0] + np.asarray(X) @ beta[1:])))


def auc(y, s):
    """Chance a random adopted connector scores above a random non-adopted one."""
    y, s = np.asarray(y), np.asarray(s)
    ranks = pd.Series(s).rank().values
    n1, n0 = y.sum(), len(y) - y.sum()
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def fit_adoption_model(launches):
    X = model_features(launches, "employees", "headcount_growth_12m", "mentions_90d",
                       "requesting_orgs", "enterprise_share")
    y = (launches.weekly_active_orgs_day90 >= ADOPTION_THRESHOLD).astype(int).values
    rng = np.random.default_rng(SEED)
    test = rng.random(len(X)) < HOLDOUT_SHARE

    beta_tr, _ = fit_logistic(X[~test].values, y[~test])
    p_test = predict_logistic(beta_tr, X[test].values)
    # Baseline: "loudest wins" — rank by how many customers asked, the way intake is often run.
    baseline_auc = auc(y[test], X[test].log_requesting_orgs.values)
    cal = pd.DataFrame({"p": p_test, "y": y[test]})
    cal["band"] = pd.qcut(cal.p, 5, labels=False, duplicates="drop")
    calibration = cal.groupby("band").agg(predicted=("p", "mean"), actual=("y", "mean"), n=("y", "size")).reset_index()

    beta, se = fit_logistic(X.values, y)           # final model uses every past launch
    coefs = [{"feature": "Intercept", "label": "Baseline", "coef": beta[0], "se": se[0]}] + [
        {"feature": f, "label": FEATURE_LABELS[f], "coef": b, "se": s, "z": b / s}
        for f, b, s in zip(FEATURES, beta[1:], se[1:])]
    return {
        "beta": beta, "means": X.mean().to_dict(), "coefficients": coefs,
        "n_train": int((~test).sum()), "n_test": int(test.sum()), "base_rate": float(y.mean()),
        "holdout_auc": auc(y[test], p_test), "baseline_auc": baseline_auc,
        "holdout_brier": float(np.mean((p_test - y[test]) ** 2)),
        "calibration": records(calibration.round(3)),
    }


def build_tool_table(req, backlog, raw):
    """One row per open tool (new asks + historical backlog) with the model's inputs."""
    co = raw["companies"].set_index("company_name")
    live = set(raw["live_catalog"].connector_name)
    open_req = req[req.tool.notna() & ~req.tool.isin(live)]
    g = open_req.groupby("tool")
    new = pd.DataFrame({
        "asks": g.size(),
        "new_orgs": g.requester_org.nunique(),
        "new_enterprise_orgs": g.apply(lambda d: d.loc[d.plan == "Enterprise", "requester_org"].nunique(), include_groups=False),
        "channels": g.channel.apply(lambda c: ", ".join(sorted(set(c)))),
        "first_asked": g.received_at.min(),
        "blocked_deal_arr": g.blocked_deal_arr.sum(),
        "use_cases": g.use_case.apply(lambda u: [x for x in pd.unique(u) if x][:5]),
    })
    bl = backlog.dropna(subset=["tool"]).set_index("tool")
    tools = sorted(set(new.index) | set(bl.index))
    t = pd.DataFrame(index=pd.Index(tools, name="tool"))
    t = t.join(new).join(bl[["issue_id", "created_at", "priority", "assignee", "customer_request_count",
                             "enterprise_customer_count"]].rename(columns={"priority": "old_priority",
                                                                          "assignee": "old_assignee"}))
    t["asks"] = t.asks.fillna(0).astype(int)
    for c in ["new_orgs", "new_enterprise_orgs", "blocked_deal_arr", "customer_request_count", "enterprise_customer_count"]:
        t[c] = t[c].fillna(0).astype(int)
    t["use_cases"] = t.use_cases.apply(lambda u: u if isinstance(u, list) else [])
    t["requesting_orgs"] = t.new_orgs + t.customer_request_count
    t["enterprise_orgs"] = t.new_enterprise_orgs + t.enterprise_customer_count
    t["enterprise_share"] = (t.enterprise_orgs / t.requesting_orgs.clip(lower=1)).round(2)
    t["source"] = np.where(t.issue_id.notna() & (t.asks > 0), "Backlog + new asks",
                           np.where(t.issue_id.notna(), "Historical backlog", "New asks"))
    t = t.join(co[["company_id", "domain", "category", "employees", "headcount_growth_12m", "mentions_90d",
                   "api_type", "auth"]])
    return t.reset_index()


def score_tools(t, model):
    X = model_features(t, "employees", "headcount_growth_12m", "mentions_90d", "requesting_orgs", "enterprise_share")
    beta = model["beta"]
    t["priority_score"] = np.round(100 * predict_logistic(beta, X.values)).astype(int)
    # Top reasons: features pushing this tool's odds up most versus an average past launch.
    contrib = (X - pd.Series(model["means"])) * beta[1:]
    t["top_reasons"] = [
        [FEATURE_LABELS[f] for f in row.sort_values(ascending=False).index if row[f] > 0.15][:2]
        for _, row in contrib.iterrows()]
    for f in FEATURES:
        t[f"pts_{f}"] = contrib[f].round(2).values

    def tier(r):
        if r.priority_score >= TIER_URGENT or (r.priority_score >= TIER_HIGH and r.blocked_deal_arr >= URGENT_BLOCKED_ARR):
            return "Urgent"
        if r.priority_score >= TIER_HIGH:
            return "High"
        if r.priority_score >= TIER_MEDIUM:
            return "Medium"
        return "Low"
    t["tier"] = t.apply(tier, axis=1)
    return t


# =============================================================================
# 4. Decide: build / partner / decline / need info
# =============================================================================
REPLIES = {
    "Build": "Thanks for asking. {tool} is approved to build (priority: {tier}). Tracking in {issue}; we'll update this thread when it ships.",
    "Partner": "Thanks for asking. {tool} already runs its own MCP server, so we're working with their team to list it. Tracking in {issue}.",
    "Decline": "Thanks for asking. We're not building {tool} right now: {why}. We review declined tools every quarter and will reopen {issue} if this changes.",
    "Need info": "Thanks for asking. Before we can triage this, could you {why}? Tracking in {issue}.",
    "Already live": "Good news: {tool} is already in the marketplace. You can enable it today from the connectors page.",
}
TIER_ORDER = {"Urgent": 0, "High": 1, "Medium": 2, "Low": 3}


def decide(t):
    def one(r):
        if r.api_type == "Unknown":
            return "Need info", "confirm whether the tool has a public API (research pending)", OWNER_PM
        if r.api_type.startswith("Official MCP"):
            # The vendor maintains the server; we list it. Only real demand needs the Product Lead.
            owner = OWNER_PM if r.tier == "Low" else OWNER_PRODUCT_LEAD
            return "Partner", "vendor runs its own MCP server", owner
        if r.api_type == "No public API":
            return "Decline", "the tool has no public API to connect to", OWNER_PM
        if r.tier == "Low":
            return "Decline", "too few signals of adoption yet", OWNER_PM
        return "Build", "public API and strong adoption signals", None
    out = t.apply(lambda r: pd.Series(one(r), index=["decision", "decision_reason", "owner"]), axis=1)
    t = pd.concat([t, out], axis=1)

    # Builds: highest score first, alternate pods, fill weekly build slots.
    build = t[t.decision == "Build"].copy()
    build["tier_rank"] = build.tier.map(TIER_ORDER)
    build = build.sort_values(["tier_rank", "priority_score"], ascending=[True, False])
    t.loc[build.index, "owner"] = [ENG_PODS[i % 2] for i in range(len(build))]
    t.loc[build.index, "build_week"] = [i // BUILD_SLOTS_PER_WEEK + 1 for i in range(len(build))]
    t["brief"] = (t.decision == "Build") & t.tier.isin(["Urgent", "High"])

    # Escalations to the Product Lead: partnerships and hard calls.
    def escalation(r):
        if r.decision == "Partner" and r.tier != "Low":
            return "Partnership: vendor-run MCP server"
        if r.decision == "Decline" and r.api_type == "No public API" and r.priority_score >= TIER_HIGH:
            return "Hard call: strong demand but no API (ask vendor for an API or MCP server)"
        if r.blocked_deal_arr >= ESCALATE_BLOCKED_ARR and r.tier in ("Medium", "Low"):
            return f"Hard call: ${r.blocked_deal_arr:,.0f} deal blocked, model says {r.tier}"
        return ""
    t["escalation"] = t.apply(escalation, axis=1)

    # Linear: reuse the existing issue id, otherwise allocate the next one.
    next_id = 101 + 62
    ids = []
    for v in t.issue_id:
        if isinstance(v, str):
            ids.append(v)
        else:
            ids.append(f"CON-{next_id}")
            next_id += 1
    t["issue_id"] = ids
    t["linear_status"] = t.apply(lambda r: {
        "Build": "Todo" if r.brief else "Backlog", "Partner": "Backlog",
        "Decline": "Canceled", "Need info": "Triage"}[r.decision], axis=1)
    return t


def triage_dates(req):
    """Each ask is triaged at the next weekly pass (Friday), the same day if it lands on a Friday."""
    d = req.received_at.dt.normalize()
    days = (TRIAGE_WEEKDAY - d.dt.weekday) % 7
    req["triaged_on"] = d + pd.to_timedelta(days, unit="D")
    req["business_days_to_triage"] = np.busday_count(d.values.astype("datetime64[D]"),
                                                     req.triaged_on.values.astype("datetime64[D]"))
    return req


def attach_decisions(req, t):
    m = t.set_index("tool")[["decision", "tier", "priority_score", "owner", "issue_id", "decision_reason"]]
    req = req.join(m, on="tool", rsuffix="_t")
    req["issue_id"] = req.issue_id.fillna(req.linear_issue)
    live = req.match_status == "Already live"
    req.loc[live, ["decision", "owner"]] = ["Already live", OWNER_PM]
    unnamed = req.match_status == "Tool not named"
    unnamed_ids = [f"CON-{900 + i}" for i in range(unnamed.sum())]
    req.loc[unnamed, ["decision", "owner", "decision_reason"]] = [
        "Need info", OWNER_PM, "tell us which tool you mean (name or website) and what you'd like to do with it"]
    req.loc[unnamed, "issue_id"] = unnamed_ids

    def reply(r):
        return REPLIES[r.decision].format(tool=r.tool, tier=r.tier, issue=r.issue_id, why=r.decision_reason)
    req["reply"] = req.apply(reply, axis=1)
    return req


def linear_import(t, req):
    """Rows in Linear's CSV import shape: one issue per tool (+ one per unnamed ask)."""
    rows = []
    for _, r in t.iterrows():
        labels = ["connector-request", r.decision.lower().replace(" ", "-")] + (["escalated"] if r.escalation else [])
        rows.append({
            "ID": r.issue_id, "Title": f"Connector: {r.tool}", "Status": r.linear_status, "Priority": r.tier,
            "Assignee": r.owner, "Labels": ",".join(labels),
            "Description": (f"Decision: {r.decision} ({r.decision_reason}). Score {r.priority_score}/100. "
                            f"{r.requesting_orgs} customers asking ({r.enterprise_orgs} Enterprise), "
                            f"{r.asks} new asks via {r.channels if isinstance(r.channels, str) else 'backlog only'}. "
                            f"API: {r.api_type}." + (f" Blocked deals: ${r.blocked_deal_arr:,.0f}." if r.blocked_deal_arr else "")),
        })
    for _, r in req[req.match_status == "Tool not named"].iterrows():
        rows.append({"ID": r.issue_id, "Title": f"Connector ask (tool not named): {r.requester_org}",
                     "Status": "Triage", "Priority": "No priority", "Assignee": OWNER_PM,
                     "Labels": "connector-request,need-info", "Description": f'Original ask ({r.channel}): "{r.tool_text}"'})
    return pd.DataFrame(rows)


# =============================================================================
# 5–6. Skills: rank candidates, qualify, port, launch
# =============================================================================
SKILL_FEATURES = ["log_stars_7d", "log_x_mentions", "log_community", "log_total_stars"]
SKILL_LABELS = {"log_stars_7d": "GitHub stars, last 7 days", "log_x_mentions": "X mentions, last 7 days",
                "log_community": "Community mentions, last 7 days", "log_total_stars": "Total GitHub stars"}


def skill_X(df, s7, x, comm, stars):
    return pd.DataFrame({"log_stars_7d": np.log1p(df[s7]), "log_x_mentions": np.log1p(df[x]),
                         "log_community": np.log1p(df[comm]), "log_total_stars": np.log1p(df[stars])})


def fit_ols(X, y):
    Xd = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(Xd, y, rcond=None)
    resid = y - Xd @ beta
    sigma2 = resid @ resid / (len(y) - Xd.shape[1])
    se = np.sqrt(np.diag(sigma2 * np.linalg.inv(Xd.T @ Xd)))
    return beta, se


def spearman(a, b):
    return float(pd.Series(a).rank().corr(pd.Series(b).rank()))


def fit_installs_model(hist):
    X = skill_X(hist, "stars_7d_at_port", "x_mentions_7d_at_port", "community_mentions_7d_at_port", "stars_at_port")
    y = np.log1p(hist.installs_30d.values)
    test = np.random.default_rng(SEED).random(len(X)) < HOLDOUT_SHARE
    b_tr, _ = fit_ols(X[~test].values, y[~test])
    pred = b_tr[0] + X[test].values @ b_tr[1:]
    r2 = 1 - ((y[test] - pred) ** 2).sum() / ((y[test] - y[test].mean()) ** 2).sum()
    beta, se = fit_ols(X.values, y)
    return {
        "beta": beta, "n_train": int((~test).sum()), "n_test": int(test.sum()),
        "holdout_r2": float(r2), "holdout_spearman": spearman(pred, y[test]),
        "baseline_spearman": spearman(X[test].log_total_stars.values, y[test]),   # "rank by total stars"
        "coefficients": [{"feature": "Intercept", "label": "Baseline", "coef": beta[0], "se": se[0]}] + [
            {"feature": f, "label": SKILL_LABELS[f], "coef": b, "se": s, "z": b / s}
            for f, b, s in zip(SKILL_FEATURES, beta[1:], se[1:])],
    }


def gate_results(c, outreach_row):
    """Five gates; each is Pass, Action (fixable by us) or Fail (stops the port)."""
    g = {}
    lic = c.license
    g["License"] = ("Pass", lic) if lic in ALLOWED_LICENSES else \
        ("Action", f"{lic}: legal review before redistributing") if lic in REVIEW_LICENSES else \
        ("Fail", f"{lic}: no right to redistribute")
    st = outreach_row.status
    g["Creator permission"] = {"Granted": ("Pass", f"Granted {outreach_row.responded_on}"),
                               "Pending": ("Action", f"Asked {outreach_row.requested_on}; waiting on @{c.creator}"),
                               "Not requested": ("Action", f"Ask @{c.creator}"),
                               "Declined": ("Fail", f"@{c.creator} declined")}[st]
    attr = outreach_row.attribution_text
    g["Attribution"] = ("Pass", attr) if isinstance(attr, str) and attr else ("Action", "Write attribution line")
    g["Transport"] = ("Pass", c.transport) if c.transport in OK_TRANSPORTS else \
        ("Fail", f"{c.transport}: needs a remote MCP transport to run on the platform")
    g["Sandbox"] = ("Pass", c.sandbox_needs) if c.sandbox_needs in OK_SANDBOX else \
        ("Fail", f"Needs {c.sandbox_needs.lower()}, not available in the sandbox")
    return g


def qualify_skills(cands, outreach, qa, model):
    X = skill_X(cands, "stars_7d", "x_mentions_7d", "community_mentions_7d", "stars")
    b = model["beta"]
    cands["predicted_installs_30d"] = np.round(np.expm1(b[0] + X.values @ b[1:]), -1).astype(int)
    cands["rank"] = cands.predicted_installs_30d.rank(ascending=False, method="first").astype(int)

    last_round = qa.groupby("skill_name")["round"].max()
    qa_summary = {}
    for name, rnd in last_round.items():
        rows = qa[(qa.skill_name == name) & (qa["round"] == rnd)]
        qa_summary[name] = {"round": int(rnd), "prompts": int(len(rows)), "passed": int(rows.passed.sum()),
                            "pass_rate": float(rows.passed.mean())}

    o = outreach.set_index("repo")
    gates, statuses, next_steps = [], [], []
    for _, c in cands.iterrows():
        g = gate_results(c, o.loc[c.repo])
        gates.append({k: {"result": v[0], "detail": v[1]} for k, v in g.items()})
        results = [v[0] for v in g.values()]
        qs = qa_summary.get(c.skill_name)
        if "Fail" in results:
            status = "Blocked"
            step = next(f"{k}: {v[1]}" for k, v in g.items() if v[0] == "Fail")
        elif "Action" in results:
            status = "Needs action"
            step = next(f"{k}: {v[1]}" for k, v in g.items() if v[0] == "Action")
        elif qs is None:
            status, step = "Ready to port", "Package as SKILL.md and run QA"
        elif qs["pass_rate"] >= QA_PASS_BAR and qs["prompts"] >= QA_MIN_PROMPTS:
            status, step = "Ready to launch", "Schedule launch"
        else:
            status, step = "In QA", f"Fix failures from QA round {qs['round']} and re-test"
        statuses.append(status)
        next_steps.append(step)
    cands["gates"] = gates
    cands["status"] = statuses
    cands["next_step"] = next_steps
    cands["qa"] = cands.skill_name.map(qa_summary)
    return cands.sort_values("rank").reset_index(drop=True)


def launch_calendar(cands, hist):
    """Past launches per week + the next 4 weeks: launch-ready first, then ready-to-port (1 week to port + QA)."""
    past = pd.to_datetime(hist.launched_on).dt.to_period("W-FRI").value_counts().sort_index()
    past = past[past.index >= pd.Period(AS_OF_DATE - pd.Timedelta(weeks=12), "W-FRI")]
    plan, week = [], 1
    queue = list(cands[cands.status == "Ready to launch"].skill_name) + \
        list(cands[cands.status == "Ready to port"].skill_name)
    for i, name in enumerate(queue[:LAUNCHES_PER_WEEK * 4]):
        week = i // LAUNCHES_PER_WEEK + 1
        if name in set(cands[cands.status == "Ready to port"].skill_name):
            week = max(week, 2)                              # needs a week to package and QA
        plan.append({"skill_name": name, "week": week,
                     "launch_on": str((AS_OF_DATE + pd.Timedelta(weeks=week) - pd.Timedelta(days=3)).date())})
    return {"past_weeks": [{"week_ending": str(p.end_time.date()), "launches": int(n)} for p, n in past.items()],
            "plan": plan}


def write_skill_package(c, qa, rewrite):
    """data/output/skills/<name>/: SKILL.md, listing.json, qa_log.md — what the export workflow ships."""
    d = OUTPUT / "skills" / c.skill_name
    d.mkdir(parents=True, exist_ok=True)
    attribution = c.gates["Attribution"]["detail"]
    (d / "SKILL.md").write_text(f"""---
name: {c.skill_name}
description: {rewrite['summary']} Use when someone asks for a diagram, schematic, flowchart or technical illustration.
license: {c.license}
metadata:
  source: https://github.com/{c.repo}
  attribution: "{attribution}"
---

# {rewrite['title']}

{rewrite['summary']}

## When to use
- The user asks for a diagram, flowchart, schematic, cutaway or other technical illustration.
- The user gives a list of steps or components and wants them drawn.

## How to work
1. Restate what will be drawn in one line and list the components.
2. Write the illustration as SVG. Label every component; keep text at 12px or larger.
3. For more than 30 nodes, use the auto-layout script (`scripts/layout.py`) instead of placing nodes by hand.
4. Save files only to the outputs folder. Never write anywhere else.
5. Offer PNG export and a dark-mode version as follow-ups.

## Limits
- No copyrighted characters or logos; offer a generic stand-in instead.
- If the description is empty, ask what to draw before drawing anything.

## Attribution
{attribution}
""")
    to_json(rewrite, d / "listing.json")
    rows = qa[qa.skill_name == c.skill_name].sort_values(["round", "prompt_id"])
    lines = [f"# QA log: {c.skill_name}", ""]
    for rnd, g in rows.groupby("round"):
        lines += [f"## Round {rnd} ({g.tested_on.iloc[0]}): {g.passed.sum()}/{len(g)} passed", "",
                  "| ID | Type | Prompt | Result | Notes |", "|---|---|---|---|---|"]
        lines += [f"| {r.prompt_id} | {r.prompt_type} | {r.prompt} | {'Pass' if r.passed else 'Fail'} | {r.notes if isinstance(r.notes, str) else ''} |"
                  for _, r in g.iterrows()]
        lines.append("")
    (d / "qa_log.md").write_text("\n".join(lines))


# =============================================================================
# 7. Listings: audit against the template
# =============================================================================
def split(v):
    return [x for x in str(v).split("|") if x and x != "nan"] if isinstance(v, str) else []


def listing_checks(r):
    """The listing template as eight checks. Each returns True when the listing meets the rule."""
    title, summary = str(r.title or ""), str(r.summary or "") if isinstance(r.summary, str) else ""
    caps, prompts = split(r.capabilities), split(r.try_asking)
    author = r.author if isinstance(r.author, str) else ""
    name = str(r["name"])
    return {
        "Title is the product name only": bool(title) and len(title) <= LISTING_TITLE_MAX
        and not any(w in title.lower() for w in TITLE_BANNED) and not (title.isupper() and len(title) > 4),
        "One-line summary leads with what you can do": bool(summary) and len(summary) <= LISTING_SUMMARY_MAX
        and summary.endswith(".") and summary.count(". ") == 0 and summary[0].isupper()
        and not summary.lower().startswith(name.lower()),
        f"{CAPABILITIES_MIN}–{CAPABILITIES_MAX} capability bullets, each starting with a verb":
            CAPABILITIES_MIN <= len(caps) <= CAPABILITIES_MAX and all(c[0].isupper() and len(c) <= 60 for c in caps),
        "Permissions stated": isinstance(r.permissions, str) and bool(r.permissions),
        "Required connectors stated": isinstance(r.required_connectors, str) and bool(r.required_connectors),
        f"{TRY_ASKING_MIN}+ \"Try asking\" prompts": len(prompts) >= TRY_ASKING_MIN
        and all(15 <= len(p) <= 80 for p in prompts),
        "Author shown": bool(author),
        "Attribution complete (ports name repo, creator, license)": bool(author) and (
            r.kind != "skill" or ("/" in author and "@" in author and "(" in author)),
    }


def audit_listings(listings, rewrites):
    checks = listings.apply(listing_checks, axis=1)
    listings["checks"] = checks
    listings["score"] = checks.apply(lambda c: sum(c.values()))
    listings["failing"] = checks.apply(lambda c: [k for k, v in c.items() if not v])
    n = len(next(iter(checks)))
    # Priority: traffic × how far from the template. A popular, broken listing costs the most.
    listings["gap"] = 1 - listings.score / n
    listings["priority"] = (listings.monthly_views * listings.gap).round().astype(int)
    order = listings.sort_values(["priority", "monthly_views"], ascending=False)
    top = set(order.listing_id.head(TOP_PRIORITY_LISTINGS))
    listings["top_priority"] = listings.listing_id.isin(top)

    rw = rewrites.set_index("listing_id")
    after = []
    for _, r in listings.iterrows():
        if r.listing_id in rw.index:
            new = r.copy()
            for col in ["title", "summary", "capabilities", "permissions", "required_connectors", "try_asking", "author"]:
                new[col] = rw.loc[r.listing_id, col]
            c = listing_checks(new)
            after.append({"listing_id": r.listing_id, "after": {col: new[col] for col in
                          ["title", "summary", "capabilities", "permissions", "required_connectors", "try_asking", "author"]},
                          "score_after": sum(c.values()), "checks_after": c})
    after = {a["listing_id"]: a for a in after}
    listings["status"] = np.where(listings.listing_id.isin(after), "Rewritten",
                                  np.where(listings.top_priority & (listings.score < n), "Queued for rewrite",
                                           np.where(listings.score == n, "Meets template", "Fix in next sweep")))
    queued = listings[listings.status == "Queued for rewrite"].sort_values("priority", ascending=False)
    listings.loc[queued.index, "rewrite_week"] = [i // REWRITES_PER_WEEK + 1 for i in range(len(queued))]
    return listings, after, n


# =============================================================================
# Engineering briefs, escalations, weekly status
# =============================================================================
def draft_listing(r):
    caps = [u[0].upper() + u[1:] for u in r.use_cases][:CAPABILITIES_MAX]
    while len(caps) < CAPABILITIES_MIN:
        caps.append(["Search records by keyword or owner", "Summarize recent activity", "Answer questions about your data"][len(caps)])
    writes = any(w in " ".join(r.use_cases) for w in ["create", "update", "draft", "reconcile", "schedule", "open"])
    return {
        "title": r.tool,
        "summary": f"Search and work with your {r.tool} data from chat.",
        "capabilities": "|".join(caps),
        "permissions": "Read and write" if writes else "Read",
        "required_connectors": "None",
        "try_asking": "|".join([f"What changed in {r.tool} this week?",
                                f"Summarize the top items in {r.tool} for my team",
                                f"Find anything in {r.tool} about our Q4 launch"]),
        "author": "Marketplace team",
    }


def write_brief(r):
    lst = draft_listing(r)
    path = OUTPUT / "briefs" / f"{r.issue_id}-{slug(r.tool)}.md"
    reasons = ", ".join(r.top_reasons) if r.top_reasons else "balanced signals"
    caps = "\n".join(f"- {c}" for c in lst["capabilities"].split("|"))
    prompts = "\n".join(f"- {p}" for p in lst["try_asking"].split("|"))
    path.write_text(f"""# Build brief: {r.tool} connector ({r.issue_id})

**Priority:** {r.tier} (score {r.priority_score}/100) · **Owner:** {r.owner} · **Target start:** build week {int(r.build_week)}

## Why build it
- {r.requesting_orgs} customers asking ({r.enterprise_orgs} Enterprise); {r.asks} new asks via {r.channels}.
- Blocked deals: ${r.blocked_deal_arr:,.0f}.
- Model: {r.priority_score}% chance of 50+ weekly active orgs by day 90. Top reasons: {reasons}.

## What customers want to do
{chr(10).join(f"- {u}" for u in r.use_cases) or "- (no use cases given; confirm with requesters)"}

## Technical
- API: {r.api_type} · Auth: {r.auth} · Docs: https://{r.domain}/developers
- Transport: remote MCP (HTTP). Scopes: request only what the capabilities below need.

## Acceptance criteria
- Every capability below works on a test workspace with real-shaped data.
- Auth works for an org admin and a regular member; scopes match the listing's permissions.
- 10+ representative prompts pass QA (90%+), logged in the QA sheet.
- Listing below passes all 8 template checks before launch.

## Draft listing
**{lst['title']}**: {lst['summary']}

Capabilities:
{caps}

Permissions: {lst['permissions']} · Required connectors: {lst['required_connectors']} · Author: {lst['author']}

Try asking:
{prompts}
""")
    return lst


def write_escalations(t):
    e = t[t.escalation != ""].sort_values("priority_score", ascending=False)
    lines = [f"# Escalations for the Product Lead: week of {AS_OF_DATE.date()}", "",
             "| Issue | Tool | Why it's escalated | Score | Customers | Blocked deals |", "|---|---|---|---|---|---|"]
    lines += [f"| {r.issue_id} | {r.tool} | {r.escalation} | {r.priority_score} ({r.tier}) | {r.requesting_orgs} | ${r.blocked_deal_arr:,.0f} |"
              for _, r in e.iterrows()]
    (OUTPUT / "escalations.md").write_text("\n".join(lines) + "\n")
    return e


def weekly_status(req, t, cands, cal, listings, n_checks, metrics):
    wk_start = AS_OF_DATE - pd.Timedelta(days=4)
    this_week = req[req.received_at >= wk_start]
    dec = t.decision.value_counts()
    launches_next = [p for p in cal["plan"] if p["week"] == 1]
    lines = [
        f"# Connectors & skills: weekly status, week ending {AS_OF_DATE.date()}", "",
        "## Headlines",
        f"- **{len(this_week)} new asks** this week ({this_week.tool.nunique()} tools); all triaged today.",
        f"- **Backlog:** {metrics['backlog_dispositioned']} of {metrics['backlog_total']} historical issues scored and given a decision.",
        f"- **Decisions (all open tools):** {dec.get('Build', 0)} build, {dec.get('Partner', 0)} partner, "
        f"{dec.get('Decline', 0)} decline, {dec.get('Need info', 0)} need info.",
        f"- **Escalated to Product Lead:** {(t.escalation != '').sum()} (see escalations.md).",
        f"- **Skills:** {len(cands)} candidates ranked; {(cands.status == 'Ready to launch').sum()} ready to launch; "
        f"next launches: {', '.join(p['skill_name'] for p in launches_next) or 'none'}.",
        f"- **Listings:** {len(listings)} audited; {(listings.score == n_checks).sum()} meet the template; "
        f"{(listings.status == 'Rewritten').sum()} of {TOP_PRIORITY_LISTINGS} top-priority rewritten.",
        "", "## 90-day success metrics",
        "| Metric | Now | Target |", "|---|---|---|",
    ]
    lines += [f"| {m['metric']} | {m['now']} | {m['target']} |" for m in metrics["table"]]
    lines += ["", "## Top of the build queue", "| Issue | Tool | Tier | Score | Owner |", "|---|---|---|---|---|"]
    top = t[t.decision == "Build"].sort_values(["build_week", "priority_score"], ascending=[True, False]).head(6)
    lines += [f"| {r.issue_id} | {r.tool} | {r.tier} | {r.priority_score} | {r.owner} |" for _, r in top.iterrows()]
    (OUTPUT / f"weekly_status_{AS_OF_DATE.date()}.md").write_text("\n".join(lines) + "\n")


def success_metrics(req, t, backlog, cands, cal, listings, n_checks):
    new_req = req
    within = (new_req.business_days_to_triage <= SLA_BUSINESS_DAYS).mean()
    logged = new_req[["owner", "decision", "reply"]].notna().all(axis=1).mean()
    bl_tools = set(backlog.tool.dropna())
    bl_done = int(t[t.tool.isin(bl_tools)].decision.notna().sum())
    launch_names = [p["skill_name"] for p in cal["plan"]]
    launching = cands[cands.skill_name.isin(launch_names) & (cands.status == "Ready to launch")]
    backed = launching.apply(lambda c: c.gates["Creator permission"]["result"] == "Pass"
                             and c.gates["Attribution"]["result"] == "Pass" and isinstance(c.qa, dict), axis=1)
    top = listings[listings.top_priority]
    past = cal["past_weeks"][-8:]
    legacy_open_days = (AS_OF_DATE - pd.to_datetime(backlog.created_at)).dt.days
    return {
        "sla_within": float(within), "logged": float(logged),
        "backlog_total": int(len(backlog)), "backlog_dispositioned": int(bl_done),
        "legacy_median_days_open": int(legacy_open_days.median()),
        "legacy_unprioritized": int(backlog.priority.isna().sum()),
        "legacy_unassigned": int(backlog.assignee.isna().sum()),
        "legacy_no_reply": int(backlog.last_reply_at.isna().sum()),
        "table": [
            {"metric": f"New asks triaged within {SLA_BUSINESS_DAYS} business days", "now": f"{within:.0%}", "target": "100%"},
            {"metric": "Historical backlog scored and given a decision", "now": f"{bl_done}/{len(backlog)}", "target": "All"},
            {"metric": "Asks logged with owner, decision and reply", "now": f"{logged:.0%}", "target": "100%"},
            {"metric": "Skill candidates ranked", "now": f"{len(cands)}", "target": "Active, ranked pipeline"},
            {"metric": "Launch cadence (last 8 weeks)", "now": f"{sum(w['launches'] for w in past) / max(len(past), 1):.1f}/week",
             "target": f"{LAUNCHES_PER_WEEK}/week, steady"},
            {"metric": "Launches backed by test log, permission and attribution",
             "now": f"{backed.mean():.0%}" if len(backed) else "n/a", "target": "100%"},
            {"metric": "Listings audited against the template", "now": f"{len(listings)}/{len(listings)}", "target": "All"},
            {"metric": "Top-priority listings rewritten", "now": f"{(top.status == 'Rewritten').sum()}/{len(top)}",
             "target": f"All {len(top)} (queue: {REWRITES_PER_WEEK}/week)"},
        ],
    }


# =============================================================================
# Main
# =============================================================================
def main():
    for d in [PROCESSED, OUTPUT, OUTPUT / "briefs", SITE]:
        d.mkdir(parents=True, exist_ok=True)
    for old in (OUTPUT / "briefs").glob("*.md"):
        old.unlink()
    raw = load()

    # 1–2. Collect, match, dedupe
    req = unify_requests(raw)
    req, backlog = match_and_dedupe(req, raw)
    req = triage_dates(req)

    # 3. Score
    model = fit_adoption_model(raw["past_connector_launches"])
    t = build_tool_table(req, backlog, raw)
    t = score_tools(t, model)

    # 4. Decide
    t = decide(t)
    req = attach_decisions(req, t)
    linear = linear_import(t, req)
    briefs = {r.tool: write_brief(r) for _, r in t[t.brief].iterrows()}
    esc = write_escalations(t)

    # 5–6. Skills
    smodel = fit_installs_model(raw["past_skill_ports"])
    cands = qualify_skills(raw["skill_candidates"].copy(), raw["skill_outreach"], raw["qa_runs"], smodel)
    cal = launch_calendar(cands, raw["past_skill_ports"])

    # 7. Listings
    listings, after, n_checks = audit_listings(raw["listings"].copy(), raw["listing_rewrites"])
    sw = cands[cands.skill_name == FEATURED["skill"]].iloc[0]
    sw_listing = {"title": "Sketchwright",
                  "summary": "Turn a plain-English description into a clean, labeled technical illustration.",
                  "capabilities": "Draw diagrams, flowcharts and schematics as SVG|Label every component clearly|Lay out large diagrams automatically|Export as PNG or dark-mode SVG",
                  "permissions": "Write files to the outputs folder", "required_connectors": "None",
                  "try_asking": "Draw a load balancer in front of three web servers|Turn these steps into a flowchart|Make a labeled cutaway of a centrifugal pump",
                  "author": f"Ported from {sw.repo} by @{sw.creator} ({sw.license})"}
    sw_check = listing_checks(pd.Series({**sw_listing, "name": "sketchwright", "kind": "skill"}))
    write_skill_package(sw, raw["qa_runs"], sw_listing)
    bp_check = listing_checks(pd.Series({**briefs[FEATURED["build"]], "name": FEATURED["build"], "kind": "connector"}))

    # 8. Report
    metrics = success_metrics(req, t, backlog, cands, cal, listings, n_checks)
    weekly_status(req, t, cands, cal, listings, n_checks, metrics)

    # ---- Story checks: fail if a featured item lands somewhere unexpected ----
    tt = t.set_index("tool")
    assert tt.loc[FEATURED["build"], "tier"] == "Urgent" and tt.loc[FEATURED["build"], "decision"] == "Build"
    assert tt.loc[FEATURED["partner"], "decision"] == "Partner"
    assert tt.loc[FEATURED["decline"], "decision"] == "Decline"
    hr = req[req.tool_text.str.contains("HR tool", na=False)].iloc[0]
    assert hr.decision == "Need info"
    cs = cands.set_index("skill_name")
    assert cs.loc[FEATURED["skill"], "status"] == "Ready to launch", cs.loc[FEATURED["skill"], "status"]
    assert cs.loc[FEATURED["blocked_skill"], "status"] == "Blocked"
    assert all(sw_check.values()) and all(bp_check.values())
    for lid in after:
        assert after[lid]["score_after"] == n_checks

    # ---- Write processed tables + tool outputs ----
    req.to_csv(PROCESSED / "requests.csv", index=False)
    t.drop(columns=["use_cases"]).to_csv(PROCESSED / "tool_scores.csv", index=False)
    cands.drop(columns=["gates", "qa"]).to_csv(PROCESSED / "skill_candidates_ranked.csv", index=False)
    listings.drop(columns=["checks", "failing"]).to_csv(PROCESSED / "listing_audit.csv", index=False)
    linear.to_csv(OUTPUT / "linear_import.csv", index=False)
    req[["request_id", "channel", "requester_org", "issue_id", "decision", "reply"]].to_csv(OUTPUT / "replies.csv", index=False)

    # ---- Site JSON ----
    write_site(req, t, model, briefs, esc, linear, cands, smodel, cal, listings, after, n_checks,
               sw_listing, sw_check, bp_check, metrics, raw, backlog)
    publish_files(t)
    print_summary(req, t, model, smodel, cands, listings, metrics, n_checks)

    import validate
    validate.main()


def write_site(req, t, model, briefs, esc, linear, cands, smodel, cal, listings, after, n_checks,
               sw_listing, sw_check, bp_check, metrics, raw, backlog):
    weekly = req.assign(week=req.triaged_on.dt.strftime("%Y-%m-%d")).groupby(["week", "channel"]).size() \
        .unstack(fill_value=0).reset_index()
    tool_cols = ["tool", "issue_id", "source", "category", "asks", "requesting_orgs", "enterprise_orgs",
                 "enterprise_share", "blocked_deal_arr", "channels", "api_type", "auth", "employees",
                 "headcount_growth_12m", "mentions_90d", "priority_score", "tier", "top_reasons", "decision",
                 "decision_reason", "owner", "linear_status", "escalation", "brief", "build_week", "use_cases",
                 "old_priority", "old_assignee", "domain"] + [f"pts_{f}" for f in FEATURES]
    tv = t[tool_cols].copy()
    tv["slug"] = tv.tool.map(slug)
    req_v = req.assign(received_at=req.received_at.dt.strftime("%Y-%m-%d %H:%M"),
                       triaged_on=req.triaged_on.dt.strftime("%Y-%m-%d"))
    to_json({
        "as_of": str(AS_OF_DATE.date()),
        "config": {"sla_days": SLA_BUSINESS_DAYS, "tier_urgent": TIER_URGENT, "tier_high": TIER_HIGH,
                   "tier_medium": TIER_MEDIUM, "urgent_blocked_arr": URGENT_BLOCKED_ARR,
                   "escalate_blocked_arr": ESCALATE_BLOCKED_ARR, "build_slots": BUILD_SLOTS_PER_WEEK,
                   "adoption_threshold": ADOPTION_THRESHOLD},
        "counts": {"raw_asks": len(req), "duplicates": int(req.is_duplicate.sum()),
                   "tools": int(req.tool.nunique()), "unnamed": int((req.match_status == "Tool not named").sum()),
                   "already_live": int((req.match_status == "Already live").sum()),
                   "merged_backlog": int((req.match_status == "Merged into backlog issue").sum()),
                   "by_channel": req.channel.value_counts().to_dict(),
                   "by_match": req.match_status.value_counts().to_dict(),
                   "decisions": t.decision.value_counts().to_dict(), "tiers": t.tier.value_counts().to_dict()},
        "model": {k: v for k, v in model.items() if k not in ("beta", "means")},
        "tools": records(tv.sort_values("priority_score", ascending=False)),
        "requests": records(req_v.drop(columns=["linear_issue", "decision_reason"])),
        "weekly": records(weekly),
        "briefs": briefs, "bp_check": bp_check,
        "escalations": records(esc[["issue_id", "tool", "escalation", "priority_score", "tier",
                                    "requesting_orgs", "blocked_deal_arr"]]),
        "linear": records(linear),
        "legacy": {k: metrics[k] for k in ["legacy_median_days_open", "legacy_unprioritized", "legacy_unassigned",
                                           "legacy_no_reply", "backlog_total"]},
    }, SITE / "intake.json")

    to_json({
        "as_of": str(AS_OF_DATE.date()),
        "config": {"qa_pass_bar": QA_PASS_BAR, "launches_per_week": LAUNCHES_PER_WEEK,
                   "allowed_licenses": sorted(ALLOWED_LICENSES), "review_licenses": sorted(REVIEW_LICENSES)},
        "model": {k: v for k, v in smodel.items() if k != "beta"},
        "candidates": records(cands),
        "calendar": cal,
        "qa": records(raw["qa_runs"]),
        "sketchwright_listing": sw_listing, "sketchwright_checks": sw_check,
        "status_counts": cands.status.value_counts().to_dict(),
    }, SITE / "skills.json")

    to_json({
        "as_of": str(AS_OF_DATE.date()), "n_checks": n_checks,
        "check_names": list(next(iter(listings.checks)).keys()),
        "listings": records(listings.drop(columns=["gap"])),
        "rewrites": after,
        "pass_rate_by_check": {k: float(np.mean([c[k] for c in listings.checks])) for k in next(iter(listings.checks))},
        "status_counts": listings.status.value_counts().to_dict(),
        "config": {"top_priority": TOP_PRIORITY_LISTINGS, "rewrites_per_week": REWRITES_PER_WEEK},
    }, SITE / "catalog.json")

    to_json({"as_of": str(AS_OF_DATE.date()), **metrics,
             "status_markdown": (OUTPUT / f"weekly_status_{AS_OF_DATE.date()}.md").read_text()}, SITE / "status.json")


def publish_files(t):
    """Copy the files people would open (Linear CSV, briefs, SKILL.md, status) next to the site."""
    files = SITE.parent / "files"
    files.mkdir(exist_ok=True)
    bp = t.set_index("tool").loc[FEATURED["build"]]
    copies = {
        OUTPUT / "linear_import.csv": "linear_import.csv",
        OUTPUT / "escalations.md": "escalations.md",
        OUTPUT / f"weekly_status_{AS_OF_DATE.date()}.md": "weekly_status.md",
        OUTPUT / "briefs" / f"{bp.issue_id}-{slug(FEATURED['build'])}.md": "brief-brightpath-analytics.md",
        OUTPUT / "skills" / FEATURED["skill"] / "SKILL.md": "sketchwright-SKILL.md",
        OUTPUT / "skills" / FEATURED["skill"] / "qa_log.md": "sketchwright-qa_log.md",
        ROOT / "content" / "how_this_works.md": "how_this_works.md",
    }
    for src, name in copies.items():
        if src.exists():
            (files / name).write_text(src.read_text())


def print_summary(req, t, model, smodel, cands, listings, metrics, n_checks):
    print(f"Asks: {len(req)} raw → {req.tool.nunique()} tools "
          f"({req.is_duplicate.sum()} duplicates, {(req.match_status == 'Already live').sum()} already live, "
          f"{(req.match_status == 'Tool not named').sum()} unnamed)")
    print(f"Adoption model: holdout AUC {model['holdout_auc']:.2f} vs 'most asks' {model['baseline_auc']:.2f}; "
          f"Brier {model['holdout_brier']:.3f}")
    print("Tiers:", t.tier.value_counts().to_dict(), "| Decisions:", t.decision.value_counts().to_dict())
    print(f"Installs model: holdout R² {smodel['holdout_r2']:.2f}, Spearman {smodel['holdout_spearman']:.2f} "
          f"vs total stars {smodel['baseline_spearman']:.2f}")
    print("Skills:", cands.status.value_counts().to_dict())
    print(f"Listings meeting template: {(listings.score == n_checks).sum()}/{len(listings)}")
    for m in metrics["table"]:
        print(f"  {m['metric']:60s} {m['now']:>10s}  target {m['target']}")
    bp = t.set_index("tool").loc[FEATURED["build"]]
    print(f"Brightpath Analytics: {bp.asks} asks, {bp.requesting_orgs} orgs, score {bp.priority_score}, "
          f"{bp.tier}, {bp.decision}, {bp.owner}, {bp.issue_id}")


if __name__ == "__main__":
    main()
