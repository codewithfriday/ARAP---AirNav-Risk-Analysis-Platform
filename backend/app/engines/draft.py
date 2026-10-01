"""Draft an ORLIO AcciMap from the text of a final report (Manual Appendix E.7, SRS IES-10 … IES-13).

Two drafters, both produce a *draft* that an investigator must review and a reviewer must approve before the case is
used by search, fuzzy inference or the Bayesian network:

* ``llm``       — Claude (Anthropic Messages API, tool use for structured output). Used only when an API key is
                  configured. Every block must carry a verbatim quote from the report.
* ``heuristic`` — offline: sentences are matched to the category's factor catalogue and mechanism keywords.

Whichever drafter is used, every quote is checked against the report text; a block whose quote is not found is
flagged ``quote_verified = false`` so the reviewer sees it.
"""
from __future__ import annotations

import json
import re
import urllib.request
from typing import Any, Callable

from . import fuzzy

ENGINE_VERSION = "draft-1.0.0"
NEG = re.compile(r"\b(not a factor|was not|were not|no evidence|did not contribute|ruled out|excluded)\b", re.I)
FINDING_CUE = re.compile(r"\b(contribut\w*|finding\w*|safety factor\w*|caus\w*|likely|probabl\w*)\b", re.I)


class DraftError(ValueError):
    pass


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def sentences(text: str) -> list[str]:
    t = re.sub(r"\s+", " ", text or "").strip()
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", t) if len(s.strip()) > 20]


def verify_quotes(model: dict, text: str) -> int:
    nt = _norm(text)
    bad = 0
    for b in model.get("blocks", []):
        q = _norm(b.get("quote", ""))
        b["quote_verified"] = bool(q) and q in nt
        if b.get("quote") and not b["quote_verified"]:
            bad += 1
    return bad


def _finalise(model: dict, category: dict, factors: dict, mechanism: str | None) -> dict:
    mechs = [m["code"] for m in category["mechanisms"]]
    for b in model["blocks"]:
        if b.get("factor") and b["factor"] not in factors:
            b["factor_suggested"] = b["factor"]
            b["factor"] = None
        if b["kind"] == "finding":
            mech = b.pop("mechanism", None) or mechanism or mechs[0]
            b["past"] = {m: ("VP" if m == mech else "HU") for m in mechs}
        elif not isinstance(b.get("past"), str) or b["past"] not in fuzzy.SUPPORT:
            b["past"] = "S"
    model["rules"] = fuzzy.default_rules(model)
    return model


# ------------------------------------------------------------------ heuristic drafter
def heuristic(text: str, category: dict, factor_list: list[dict], normaliser) -> dict[str, Any]:
    from .casesearch import detect_factors
    sents = sentences(text)
    if not sents:
        raise DraftError("the report text is empty or has no sentences")
    blocks, used = [], set()
    n = 0
    for s in sents:
        for code in detect_factors(normaliser, s, factor_list):
            if code in used:
                continue
            used.add(code)
            f = next(x for x in factor_list if x["code"] == code)
            n += 1
            blocks.append({"id": f"e{n}", "layer": f["layer"], "kind": "evidence", "label": f["label"], "text": "",
                           "factor": code, "quote": s[:400], "past": "O" if NEG.search(s) else "S", "confidence": 0.5})
    if not blocks:
        raise DraftError("no factor of this category was recognised in the text; draft the AcciMap by hand")
    # mechanism: keyword hits, counted double in sentences that state findings or contributing factors
    score = {m["code"]: 0.0 for m in category["mechanisms"]}
    for s in sents:
        low = normaliser.text(s)
        w = 2.0 if FINDING_CUE.search(s) else 1.0
        for m in category["mechanisms"]:
            score[m["code"]] += w * sum(1 for k in m.get("keywords", []) if normaliser.text(k).strip() in low)
    mech = max(score, key=score.get) if any(score.values()) else None
    ev_low = [b["id"] for b in blocks if b["layer"] in ("L", "I")]
    ev_high = [b["id"] for b in blocks if b["layer"] in ("O", "R")]
    ev_e = [b["id"] for b in blocks if b["layer"] == "E"]
    edges = []
    mlabel = next((m["label"] for m in category["mechanisms"] if m["code"] == mech), "mechanism to be confirmed")
    fin_inputs = list(ev_e)
    if ev_low:
        blocks.append({"id": "h1", "layer": "I", "kind": "hypothesis", "label": f"Hypothesis: {mlabel}", "text": "",
                       "factor": None, "quote": "", "past": "S", "confidence": 0.3})
        edges += [{"source": i, "target": "h1", "role": "input"} for i in ev_low]
        fin_inputs.insert(0, "h1")
    if ev_high:
        blocks.append({"id": "h2", "layer": "R", "kind": "hypothesis", "label": "Risk-control and organisational factors", "text": "",
                       "factor": None, "quote": "", "past": "S", "confidence": 0.3})
        edges += [{"source": i, "target": "h2", "role": "input"} for i in ev_high]
        edges.append({"source": "h2", "target": "f1", "role": "context"})
    blocks.append({"id": "f1", "layer": "E", "kind": "finding", "label": f"Occurrence: {category['name']} — {mlabel}", "text": "",
                   "factor": None, "quote": "", "confidence": 0.3})
    edges += [{"source": i, "target": "f1", "role": "input"} for i in fin_inputs]
    model = {"blocks": blocks, "edges": edges}
    return {"model": model, "mechanism": mech, "mechanism_scores": score}


# ------------------------------------------------------------------ LLM drafter
TOOL = {
    "name": "record_accimap",
    "description": "Record the ORLIO AcciMap of the occurrence described in the report.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Two or three sentences summarising the occurrence."},
            "mechanism": {"type": "string", "description": "Code of the primary contributing mechanism."},
            "blocks": {"type": "array", "items": {"type": "object", "properties": {
                "id": {"type": "string"}, "layer": {"type": "string", "enum": ["O", "R", "L", "I", "T", "E"]},
                "kind": {"type": "string", "enum": ["evidence", "hypothesis", "finding"]},
                "label": {"type": "string", "description": "Short label, at most 12 words."},
                "factor": {"type": ["string", "null"], "description": "Factor code from the catalogue, or null."},
                "quote": {"type": "string", "description": "Verbatim sentence or phrase from the report that supports the block."},
                "past": {"type": "string", "enum": ["SS", "S", "NE", "O", "SO"], "description": "How strongly the report supports it."}},
                "required": ["id", "layer", "kind", "label", "quote"]}},
            "edges": {"type": "array", "items": {"type": "object", "properties": {
                "source": {"type": "string"}, "target": {"type": "string"},
                "role": {"type": "string", "enum": ["input", "context"]}}, "required": ["source", "target"]}},
        },
        "required": ["blocks", "edges", "mechanism"],
    },
}


def llm_prompt(text: str, category: dict, factor_list: list[dict]) -> str:
    cat = "\n".join(f"- {f['code']} ({f['layer']}, ATSB {f.get('atsb', '-')}): {f['label']}" for f in factor_list)
    mech = "\n".join(f"- {m['code']}: {m['label']}" for m in category["mechanisms"])
    return f"""You are helping an air navigation service provider build a case library for its occurrence-investigation
expert system. Represent the final report below as an AcciMap in the ATSB ORLIO layers:
O = organisational influences, R = risk controls, L = local conditions, I = individual actions, T = technical failure mechanisms,
E = occurrence events (ATSB Safety Investigation Guidelines — Analysis).

Rules:
- Evidence blocks are facts established in the report. Hypothesis blocks are intermediate conclusions the investigators
  drew from evidence. Exactly one finding block (layer E) states the occurrence and its mechanism.
- Every block must have a quote copied VERBATIM from the report. Do not paraphrase inside the quote. If you cannot quote
  it, leave the block out.
- Use a factor code from the catalogue when one fits; otherwise null.
- Edges point from a block to the conclusion it supports (evidence → hypothesis → finding). Use role "context" for
  organisational and risk-control blocks that explain but are not needed to establish the finding.
- "past": SS if the report states it as established by physical or recorded evidence, S if from interviews or
  judgement, O or SO if the report rules it out.
- Choose the mechanism code from the list.
- Write labels in neutral ATSB style: a subject and an action verb for events and actions; no judgemental words such as
  "failed", "deficient", "inadequate", "poor"; one factor per block.

Occurrence category: {category['name']}
Mechanisms:
{mech}
Factor catalogue:
{cat}

REPORT TEXT:
<<<
{text[:60000]}
>>>"""


def _post(url: str, key: str, payload: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"content-type": "application/json", "x-api-key": key,
                                          "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 — URL comes from server configuration
        return json.loads(r.read())


def llm(text: str, category: dict, factor_list: list[dict], key: str, model_name: str, url: str,
        post: Callable[[str, str, dict], dict] | None = None) -> dict[str, Any]:
    if not key:
        raise DraftError("AI drafting is not configured (ARAP_ANTHROPIC_API_KEY)")
    payload = {"model": model_name, "max_tokens": 8000, "tools": [TOOL],
               "tool_choice": {"type": "tool", "name": "record_accimap"},
               "messages": [{"role": "user", "content": llm_prompt(text, category, factor_list)}]}
    try:
        resp = (post or _post)(url, key, payload)
    except Exception as e:  # network, HTTP or JSON error
        raise DraftError(f"AI drafting failed: {e}") from e
    use = next((c for c in resp.get("content", []) if c.get("type") == "tool_use"), None)
    if not use:
        raise DraftError("AI drafting returned no AcciMap")
    data = use["input"]
    ids = set()
    blocks = []
    for b in data.get("blocks", []):
        if b.get("id") in ids or b.get("layer") not in fuzzy.LAYERS or b.get("kind") not in ("evidence", "hypothesis", "finding"):
            continue
        ids.add(b["id"])
        blocks.append({"id": b["id"], "layer": b["layer"], "kind": b["kind"], "label": b.get("label", "")[:200], "text": "",
                       "factor": b.get("factor"), "quote": b.get("quote", ""), "past": b.get("past", "S"), "confidence": 0.7})
    if not any(b["kind"] == "finding" for b in blocks):
        blocks.append({"id": "f1", "layer": "E", "kind": "finding", "label": f"Occurrence: {category['name']}", "text": "",
                       "factor": None, "quote": "", "confidence": 0.3})
    fid = next(b["id"] for b in blocks if b["kind"] == "finding")
    for b in blocks:
        if b["kind"] == "finding" and b["id"] != fid:
            b["kind"] = "hypothesis"
    edges = [{"source": e["source"], "target": e["target"], "role": e.get("role", "input")}
             for e in data.get("edges", []) if e.get("source") in ids and e.get("target") in ids and e["source"] != e["target"]]
    model = {"blocks": blocks, "edges": edges}
    try:
        fuzzy.topo(model)
    except fuzzy.FuzzyError:
        model["edges"] = [e for e in edges if e["role"] == "context"]
    return {"model": model, "mechanism": data.get("mechanism"), "summary": data.get("summary", ""),
            "usage": resp.get("usage", {}), "model_name": resp.get("model", model_name)}


def draft(text: str, category: dict, factor_list: list[dict], normaliser, *, use_ai: bool, key: str = "",
          model_name: str = "", url: str = "", post=None) -> dict[str, Any]:
    method = "llm" if use_ai else "heuristic"
    out = llm(text, category, factor_list, key, model_name, url, post) if use_ai else heuristic(text, category, factor_list, normaliser)
    fidx = {f["code"]: f for f in factor_list}
    mechs = {m["code"] for m in category["mechanisms"]}
    mech = out.get("mechanism") if out.get("mechanism") in mechs else None
    model = _finalise(out["model"], category, fidx, mech)
    unverified = verify_quotes(model, text)
    return {"model": model, "mechanism": mech, "summary": out.get("summary", ""), "method": method,
            "unverified_quotes": unverified, "details": {k: v for k, v in out.items() if k not in ("model",)},
            "engine_version": ENGINE_VERSION}
