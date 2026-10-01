"""ATSB safety investigation analysis engine (Manual Appendix F, SRS §5.15).

Study model (method "atsb"):
    {"occurrence": {...}, "events": [...], "factors": [...], "key_findings": [...], "review": {...}, "stop_rule": "..."}
Each factor carries three tests — existence, influence (with a target), importance — each with evidence items rated
supports / opposes / no effect / unsure, a conclusion (supported / not supported) and a probability expression.

Derived here:
* finding type ([G] p.145): existence + influence = contributing safety factor; existence + importance = other safety
  factor; a factor whose only influence is on a non-contributing factor is an other safety factor ([T] p.125);
  positive actions/conditions that pass existence + influence are positive safety factors (other key findings);
* safety issue level from the risk rating on the AirNav 5×5 or the ATSB 6×6; broadly acceptable ⇒ not a safety issue;
* residual risk evaluation after safety action and the six-monthly follow-up date;
* checks: writing rules, argument from ignorance, standard of proof, compound probability, independence, safety-issue
  rules, classification completeness, test for sufficiency, fairness, follow-up.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from .. import atsb as ref
from . import risk

ENGINE_VERSION = "atsb-1.0.0"
LEVEL_ORDER = {"E": 0, "I": 1, "T": 1, "L": 2, "R": 3, "O": 4}


def _prob(t: dict) -> int | None:
    p = t.get("probability")
    return ref.PROB_LOWER.get(p) if p else None


def _passed(t: dict | None) -> bool | None:
    if not t:
        return None
    c = t.get("conclusion")
    if c == "supported":
        p = _prob(t)
        return p is None or p >= ref.STANDARD_OF_PROOF
    if c == "not_supported":
        return False
    return None


def _ratings(t: dict | None) -> dict[str, int]:
    out = {k: 0 for k in ref.ITEM_RATINGS}
    for it in (t or {}).get("items", []):
        if it.get("rating") in out:
            out[it["rating"]] += 1
    return out


def finding_types(factors: list[dict]) -> dict[str, dict]:
    by_id = {f["id"]: f for f in factors}
    res: dict[str, dict] = {}
    for f in factors:
        ex, inf = _passed(f.get("existence")), _passed(f.get("influence"))
        imp = (f.get("importance") or {}).get("passed")
        target = (f.get("influence") or {}).get("target")
        res[f["id"]] = {"existence": ex, "influence": inf, "importance": imp, "target": target}
    # contributing: existence + influence on the occurrence or on a contributing factor (fixpoint over the chain)
    contributing: set[str] = set()
    changed = True
    while changed:
        changed = False
        for fid, r in res.items():
            if fid in contributing or not (r["existence"] and r["influence"]):
                continue
            if r["target"] == "occurrence" or r["target"] in contributing:
                contributing.add(fid); changed = True
    for f in factors:
        r, t = res[f["id"]], f.get("type")
        positive = ref.TYPES.get(t, {}).get("positive", False)
        if f.get("further") is False:
            ft = "excluded"
        elif r["existence"] is False:
            ft = "not_established"
        elif r["existence"] is None:
            ft = "pending"
        elif f["id"] in contributing:
            ft = "positive" if positive else "contributing"
        elif r["influence"] and r["target"] in by_id:
            ft = "positive" if positive else "other"      # influenced only a non-contributing factor
        elif r["influence"] is None and r["importance"] is None:
            ft = "pending"
        elif r["importance"]:
            ft = "positive" if positive else "other"
        elif r["importance"] is False or r["influence"] is False:
            ft = "not_safety_factor" if r["importance"] is False else "pending"
        else:
            ft = "pending"
        r["finding_type"] = ft
    return res


def rate(r: dict | None, airnav: dict) -> dict | None:
    if not r or not r.get("consequence") or not r.get("likelihood"):
        return None
    try:
        return risk.classify_issue(r.get("scheme", "airnav"), r["consequence"], int(r["likelihood"]), airnav)
    except ValueError as e:
        return {"error": str(e)}


def _words(s: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", s or "")


def writing_checks(text: str, where: str, ref_id: str, out: list, is_event: bool = False):
    if not text:
        out.append(_c("error", ref_id, "writing", f"{where}: no title or statement")); return
    low = " " + text.lower() + " "
    w = _words(text)
    if len(w) < 3:
        out.append(_c("warning", ref_id, "writing", f"{where}: write a complete sentence with a subject and an action verb ('{text}')"))
    hits = [x for x in ref.JUDGEMENTAL_WORDS if f" {x}" in low]
    if hits:
        out.append(_c("warning", ref_id, "writing", f"{where}: judgemental wording ({', '.join(hits)}) — describe what happened in neutral terms"))
    vague = [x for x in ref.VAGUE_WORDS if re.search(r"\b" + re.escape(x) + r"\b", low)]
    if vague:
        out.append(_c("info", ref_id, "writing", f"{where}: vague wording ({', '.join(vague)}) — be specific"))
    if not is_event and (len(re.findall(r"\band\b", low)) >= 2 or ", and " in low or " as well as " in low):
        out.append(_c("info", ref_id, "writing", f"{where}: may bundle more than one factor — one factor per statement"))


def _c(severity: str, ref_id: str | None, code: str, message: str) -> dict:
    return {"severity": severity, "ref": ref_id, "code": code, "message": message}


def test_checks(f: dict, key: str, label: str, out: list):
    t = f.get(key) or {}
    if t.get("conclusion") not in ("supported", "not_supported"):
        return
    n = _ratings(t)
    if t["conclusion"] == "supported":
        if n["supports"] == 0:
            out.append(_c("warning", f["id"], "ignorance", f"{f['title']}: {label} concluded supported but no item supports it — "
                                                            "absence of evidence is not evidence (argument from ignorance)"))
        if n["opposes"] > n["supports"]:
            out.append(_c("warning", f["id"], "opposing", f"{f['title']}: {label} has more opposing than supporting items — "
                                                           "explain how the opposing evidence is accounted for"))
        p = _prob(t)
        if p is not None and p < ref.STANDARD_OF_PROOF:
            out.append(_c("error", f["id"], "proof", f"{f['title']}: {label} probability is below the standard of proof (likely, ≥ 66%)"))
        if not t.get("probability"):
            out.append(_c("info", f["id"], "qualifier", f"{f['title']}: state the probability expression for the {label} finding"))
    srcs = [it.get("source", "").strip().lower() for it in t.get("items", []) if it.get("source", "").strip()]
    dup = {s for s in srcs if srcs.count(s) > 1}
    if dup:
        out.append(_c("info", f["id"], "independence", f"{f['title']}: {label} items share a source ({', '.join(sorted(dup))}) — not independent"))


def analyse(model: dict, airnav: dict | None = None, today: date | None = None) -> dict[str, Any]:
    airnav = airnav or risk.DEFAULT_SCHEME
    today = today or date.today()
    factors = model.get("factors") or []
    events = model.get("events") or []
    ids = {f["id"] for f in factors}
    checks: list[dict] = []
    ft = finding_types(factors)
    explained_by: dict[str, list[str]] = {f["id"]: [] for f in factors}
    for f in factors:
        tg = (f.get("influence") or {}).get("target")
        if tg in explained_by and ft[f["id"]]["existence"]:
            explained_by[tg].append(f["id"])
    out_factors = {}
    issues = []
    for f in factors:
        fid, t = f["id"], f.get("type")
        meta = ref.TYPES.get(t)
        d = dict(ft[fid])
        d["explained_by"] = explained_by[fid]
        if not meta:
            checks.append(_c("error", fid, "type", f"{f.get('title', fid)}: choose a safety factor type"))
            out_factors[fid] = d; continue
        writing_checks(f.get("title", ""), "Factor", fid, checks)
        if f.get("further") is False and not (f.get("exclusion_reason") or f.get("further_justification")):
            checks.append(_c("error", fid, "exclusion", f"{f['title']}: not analysed further — give the reason"))
        if f.get("further") is False:
            out_factors[fid] = d; continue
        if t not in ("OE",) and not f.get("codes"):
            checks.append(_c("warning", fid, "classify", f"{f['title']}: classify with at least one ATSB safety factor type code"))
        if t == "IA" and (not f.get("role") or not f.get("error_type")):
            checks.append(_c("warning", fid, "classify", f"{f['title']}: individual action needs the individual's role and the error type"))
        if t in ("LC", "RC", "OI", "TFM", "PC") and not f.get("functional_area"):
            checks.append(_c("info", fid, "classify", f"{f['title']}: add the functional area"))
        if t == "RC" and not f.get("control_function"):
            checks.append(_c("info", fid, "classify", f"{f['title']}: is this a preventive or a recovery control?"))
        for key, label in (("existence", "existence"), ("influence", "influence")):
            test_checks(f, key, label, checks)
        inf = f.get("influence") or {}
        if inf.get("conclusion") == "supported":
            tg = inf.get("target")
            if not tg:
                checks.append(_c("error", fid, "target", f"{f['title']}: name the factor or the occurrence it influenced"))
            elif tg == fid or (tg != "occurrence" and tg not in ids):
                checks.append(_c("error", fid, "target", f"{f['title']}: influence target is not valid"))
        pe, pi = _prob(f.get("existence") or {}), _prob(inf)
        if d["existence"] and d["influence"] and pe is not None and pi is not None and pe * pi / 100 < 50:
            checks.append(_c("warning", fid, "compound", f"{f['title']}: existence ({pe}%+) and influence ({pi}%+) together may be only "
                                                         f"about {round(pe * pi / 100)}% — reconsider the contributing finding"))
        if d["existence"] and d["influence"] is False and d["importance"] is None:
            checks.append(_c("info", fid, "importance", f"{f['title']}: influence not shown — complete the test for importance"))
        if d["importance"] is not None and not (f.get("importance") or {}).get("justification"):
            checks.append(_c("warning", fid, "importance", f"{f['title']}: justify the importance decision"))
        # safety issue
        if f.get("safety_issue"):
            if not meta["issue_allowed"]:
                checks.append(_c("error", fid, "issue_type", f"{f['title']}: only local conditions, risk controls and organisational influences can be safety issues"))
            if not f.get("issue_owner"):
                checks.append(_c("warning", fid, "issue_owner", f"{f['title']}: name the organisation that owns the safety issue"))
            if d["finding_type"] not in ("contributing", "other"):
                checks.append(_c("info", fid, "issue_tests", f"{f['title']}: risk analysis normally follows existence plus influence or importance"))
            ra = f.get("risk") or {}
            r = rate(ra, airnav)
            d["risk"] = r
            if r and "error" not in r:
                lvl = r["issue_level"]
                d["issue_level"] = lvl
                d["is_safety_issue"] = lvl != "broadly_acceptable"
                for fld, nm in (("worst_credible", "worst credible scenario"), ("consequence_justification", "consequence justification"),
                                ("likelihood_justification", "likelihood justification")):
                    if not ra.get(fld):
                        checks.append(_c("warning", fid, "risk", f"{f['title']}: record the {nm}"))
                sens = ra.get("sensitivity") or {}
                if sens.get("consequence") and sens.get("likelihood"):
                    d["sensitivity"] = rate({**sens, "scheme": ra.get("scheme", "airnav")}, airnav)
                # residual risk and evaluation of safety action
                ev = f.get("evaluation") or {}
                rr = rate({**(ev.get("residual") or {}), "scheme": ra.get("scheme", "airnav")}, airnav)
                d["residual"] = rr
                if rr and "error" not in rr:
                    rl = rr["issue_level"]
                    d["action_evaluation"] = ("no_further" if rl == "broadly_acceptable" or (rl == "significant" and ev.get("alarp") is True)
                                              else "further")
                if d["is_safety_issue"]:
                    st = f.get("issue_status") or "pending"
                    if st == "adequately" and d.get("action_evaluation") == "further":
                        checks.append(_c("warning", fid, "status", f"{f['title']}: marked adequately addressed but residual risk still needs further action"))
                    if lvl == "critical" and not f.get("actions"):
                        checks.append(_c("warning", fid, "action", f"{f['title']}: critical safety issue — communicate immediately and record safety action"))
                    pr = ev.get("practicability") or {}
                    if t in ("RC", "OI") and not any(pr.values()):
                        checks.append(_c("info", fid, "practicability", f"{f['title']}: consider reasonableness/practicability for this organisational finding"))
                    if st != "adequately" and d.get("action_evaluation") != "no_further":
                        dates = [a.get("notified_on") for a in f.get("actions", []) if a.get("notified_on")]
                        dates += [c.get("date") for a in f.get("actions", []) for c in a.get("log", []) if c.get("date")]
                        if dates:
                            last = max(date.fromisoformat(x[:10]) for x in dates)
                            due = last + timedelta(days=ref.FOLLOW_UP_DAYS)
                            d["follow_up_due"] = due.isoformat()
                            if due < today:
                                checks.append(_c("warning", fid, "follow_up", f"{f['title']}: follow-up overdue since {due.isoformat()} (every 6 months while above ALARP)"))
                    issues.append({"id": fid, "title": f["title"], "level": lvl, "risk": r, "status": f.get("issue_status") or "pending",
                                   "owner": f.get("issue_owner", ""), "evaluation": d.get("action_evaluation")})
            elif r and "error" in r:
                checks.append(_c("error", fid, "risk", f"{f['title']}: {r['error']}"))
            else:
                d["issue_level"] = None
                checks.append(_c("info", fid, "risk", f"{f['title']}: potential safety issue — complete the risk analysis"))
        out_factors[fid] = d
    # test for sufficiency and fairness
    by_id = {f["id"]: f for f in factors}
    for f in factors:
        d = out_factors[f["id"]]
        if d.get("finding_type") != "contributing" or f.get("type") == "OI":
            continue
        if not d["explained_by"] and not f.get("sufficiency_note"):
            checks.append(_c("warning", f["id"], "sufficiency", f"{f['title']}: no verified factor explains why it occurred or existed (test for sufficiency) "
                                                                "— add explaining factors or note why none was found"))
        if f.get("type") == "IA":
            stack, seen, found = list(d["explained_by"]), set(), False
            while stack:
                x = stack.pop()
                if x in seen:
                    continue
                seen.add(x)
                if by_id[x].get("type") in ("LC", "RC", "OI") and out_factors[x].get("finding_type") in ("contributing", "other"):
                    found = True; break
                stack += out_factors[x]["explained_by"]
            if not found and not f.get("sufficiency_note"):
                checks.append(_c("warning", f["id"], "fairness", f"{f['title']}: this individual action has no identified reasons (local conditions or risk controls) "
                                                                 "— the finding may appear to blame the individual"))
    # sequence of events
    for e in events:
        if not e.get("start"):
            checks.append(_c("error", e.get("id"), "event_time", f"Event '{e.get('title', '')}': start time is required (estimate and say so in comments)"))
        writing_checks(e.get("title", ""), "Event", e.get("id"), checks, is_event=True)
        if e.get("safety_factor") and not e.get("factor_id"):
            checks.append(_c("info", e.get("id"), "event_sf", f"Event '{e.get('title', '')}' is flagged as a safety factor but not on the safety factors list"))
    # key findings (basic evidence tables)
    kf_out = {}
    for k in model.get("key_findings") or []:
        writing_checks(k.get("statement", ""), "Key finding", k.get("id"), checks)
        p = _passed(k)
        kf_out[k["id"]] = {"supported": p}
        if p and _ratings(k)["supports"] == 0:
            checks.append(_c("warning", k["id"], "ignorance", f"Key finding '{k.get('statement', '')}': supported but no item supports it"))
    # review checklist
    rv = model.get("review") or {}
    open_items = [t for k, _, t in ref.REVIEW_CHECKLIST if not rv.get(k)]
    if open_items:
        checks.append(_c("info", None, "review", f"Analysis review: {len(open_items)} of {len(ref.REVIEW_CHECKLIST)} checks not yet confirmed"))
    # organised findings ([G] p.189)
    def key(f):
        return (LEVEL_ORDER.get(ref.TYPES.get(f.get("type"), {}).get("level", "E"), 9), f.get("title", ""))
    contrib = sorted([f for f in factors if out_factors[f["id"]].get("finding_type") == "contributing"], key=key)
    other = sorted([f for f in factors if out_factors[f["id"]].get("finding_type") == "other"], key=key)
    positive = [f for f in factors if out_factors[f["id"]].get("finding_type") == "positive"]
    keyf = [k for k in model.get("key_findings") or [] if kf_out[k["id"]]["supported"] and k.get("add_to_key", True)]
    def fl(f):
        d = out_factors[f["id"]]
        return {"id": f["id"], "title": f["title"], "type": f.get("type"), "codes": f.get("codes", []),
                "safety_issue": bool(d.get("is_safety_issue")), "issue_level": d.get("issue_level")}
    findings = {"contributing": [fl(f) for f in contrib], "other": [fl(f) for f in other],
                "other_key": [{"id": f["id"], "title": f["title"], "kind": "positive"} for f in positive] +
                             [{"id": k["id"], "title": k["statement"], "kind": k.get("kind", "other_key")} for k in keyf]}
    counts = {}
    for d in out_factors.values():
        counts[d.get("finding_type", "pending")] = counts.get(d.get("finding_type", "pending"), 0) + 1
    order = {"error": 0, "warning": 1, "info": 2}
    checks.sort(key=lambda c: order[c["severity"]])
    return {"factors": out_factors, "key_findings": kf_out, "issues": sorted(issues, key=lambda i: ["critical", "significant", "broadly_acceptable"].index(i["level"])),
            "findings": findings, "counts": counts, "checks": checks,
            "check_counts": {s: sum(1 for c in checks if c["severity"] == s) for s in order}, "engine_version": ENGINE_VERSION,
            "at": today.isoformat()}
