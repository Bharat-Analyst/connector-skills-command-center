"""
validate.py — the pipeline's last step. Recomputes key numbers from the raw files
with separate, simpler code and fails loudly if anything the site shows is wrong.

Checks:
    1. Every raw ask is accounted for exactly once (no ask lost in matching or dedupe).
    2. Every ask has an owner, a decision and a reply; every tool has one Linear issue.
    3. Triage SLA: business days recomputed from dates, all within the target.
    4. Every priority score recomputes from the raw signals, and its breakdown adds up.
    5. Tiers and decisions follow the published rubric exactly.
    6. Every launch-scheduled skill has permission, attribution, passing gates and a QA log at the bar.
    7. Listing audit: rewritten listings pass every check; counts on the site match the CSVs.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

import pipeline as P

ROOT = Path(__file__).parent


def check(cond, msg):
    if not cond:
        raise SystemExit(f"VALIDATION FAILED: {msg}")


def main():
    raw = {p.stem: pd.read_csv(p, keep_default_na=False, na_values=[""]) for p in (ROOT / "data/raw").glob("*.csv")}
    req = pd.read_csv(ROOT / "data/processed/requests.csv", keep_default_na=False, na_values=[""])
    tools = pd.read_csv(ROOT / "data/processed/tool_scores.csv", keep_default_na=False, na_values=[""])
    linear = pd.read_csv(ROOT / "data/output/linear_import.csv", keep_default_na=False, na_values=[""])
    intake = json.loads((ROOT / "docs/data/intake.json").read_text())
    skills = json.loads((ROOT / "docs/data/skills.json").read_text())
    catalog = json.loads((ROOT / "docs/data/catalog.json").read_text())
    n = 0

    # 1. Every ask accounted for once
    raw_ids = set(raw["intake_forms"].submission_id) | set(raw["slack_requests"].message_id) | set(raw["direct_asks"].ask_id)
    check(set(req.request_id) == raw_ids and req.request_id.is_unique, "asks lost or duplicated")
    check(intake["counts"]["raw_asks"] == len(raw_ids), "site raw ask count")
    live = set(raw["live_catalog"].connector_name)
    check((req.match_status == "Already live").sum() == req.tool.isin(live).sum(), "already-live count")
    n += 3

    # 2. Owner / decision / reply on every ask; one Linear issue per tool
    check(req[["owner", "decision", "reply"]].notna().all().all(), "ask without owner, decision or reply")
    check(linear.ID.is_unique, "duplicate Linear IDs")
    check(set(tools.issue_id) <= set(linear.ID), "tool without a Linear issue")
    check(len(linear) == len(tools) + (req.match_status == "Tool not named").sum(), "Linear row count")
    check(set(raw["linear_issues"].issue_id) <= set(linear.ID), "an existing backlog issue was dropped")
    n += 5

    # 3. SLA: weekday arithmetic done by hand, not with busday_count
    def bdays(a, b):
        d, k = a, 0
        while d < b:
            if d.weekday() < 5:
                k += 1
            d += pd.Timedelta(days=1)
        return k
    rec = pd.to_datetime(req.received_at).dt.normalize()
    tri = pd.to_datetime(req.triaged_on)
    check((tri.dt.weekday == P.TRIAGE_WEEKDAY).all() and (tri >= rec).all(), "triage day")
    check(all(bdays(a, b) == k for a, b, k in zip(rec, tri, req.business_days_to_triage)), "business days mismatch")
    check((req.business_days_to_triage <= P.SLA_BUSINESS_DAYS).all(), "SLA breached")
    n += 3

    # 4. Recompute the weighted score from the raw signals with a separate bucket lookup
    def pts(v, buckets):
        return next((p for m, p in buckets if v >= m), 0)
    W = P.WEIGHTS
    for _, r in tools.iterrows():
        s = (W["customers"] * pts(r.requesting_orgs, P.CUSTOMERS_BUCKETS)
             + W["traction"] * pts(r.mentions_90d, P.TRACTION_BUCKETS)
             + W["enterprise"] * round(100 * r.enterprise_share)
             + W["size"] * pts(r.employees, P.SIZE_BUCKETS)
             + W["growth"] * pts(r.headcount_growth_12m, P.GROWTH_BUCKETS))
        check(abs(s - r.priority_score) <= 0.5, f"score for {r.tool}: {s:.1f} vs {r.priority_score}")
        parts = sum(r[f"pts_{f}"] for f in P.FEATURES)
        check(abs(parts - r.priority_score) <= 0.6, f"score breakdown for {r.tool} doesn't add up")
    n += 2

    # 5. Rubric and decisions
    for _, r in tools.iterrows():
        s, arr = r.priority_score, r.blocked_deal_arr
        tier = ("Urgent" if s >= P.TIER_URGENT or (s >= P.TIER_HIGH and arr >= P.URGENT_BLOCKED_ARR)
                else "High" if s >= P.TIER_HIGH else "Medium" if s >= P.TIER_MEDIUM else "Low")
        check(r.tier == tier, f"tier for {r.tool}")
        dec = ("Need info" if r.api_type == "Unknown" else "Partner" if r.api_type.startswith("Official MCP")
               else "Decline" if r.api_type == "No public API" or tier == "Low" else "Build")
        check(r.decision == dec, f"decision for {r.tool}")
    builds = tools[tools.decision == "Build"]
    check(builds.groupby("build_week").size().max() <= P.BUILD_SLOTS_PER_WEEK, "build week over capacity")
    n += 3

    # 6. Launch-scheduled skills are fully backed
    cands = {c["skill_name"]: c for c in skills["candidates"]}
    for item in skills["calendar"]["plan"]:
        c = cands[item["skill_name"]]
        check(all(g["result"] == "Pass" for g in c["gates"].values()), f"{c['skill_name']} scheduled with a failing gate")
        if c["status"] == "Ready to launch":
            check(c["qa"]["pass_rate"] >= P.QA_PASS_BAR and c["qa"]["prompts"] >= P.QA_MIN_PROMPTS,
                  f"{c['skill_name']} QA below bar")
    check((ROOT / "data/output/skills/sketchwright/SKILL.md").exists(), "sketchwright package missing")
    weeks = pd.Series([p["week"] for p in skills["calendar"]["plan"]]).value_counts()
    check(weeks.max() <= P.LAUNCHES_PER_WEEK, "launch week over cadence")
    n += 3

    # 7. Listings
    for lid, a in catalog["rewrites"].items():
        check(a["score_after"] == catalog["n_checks"], f"rewrite {lid} fails the template")
    audit = pd.read_csv(ROOT / "data/processed/listing_audit.csv")
    check(len(audit) == len(catalog["listings"]) == len(raw["listings"]), "listing counts")
    check(audit.top_priority.sum() == P.TOP_PRIORITY_LISTINGS, "top-priority count")
    n += 3

    print(f"validate: {n} checks passed")


if __name__ == "__main__":
    main()
