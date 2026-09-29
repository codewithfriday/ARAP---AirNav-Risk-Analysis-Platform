"""Case search for the investigation expert system (SRS IES-04).

Score = 0.6 · cosine(TF-IDF of the narrative, TF-IDF of the case) + 0.4 · share of the narrative's detected ORLIO
factors that the case contains. Before tokenising, phrases in the thesaurus are replaced by one concept token, so
"add fuel", "fuel added" and "refuelled" match each other. Every result lists the terms and factors that matched.
"""
from __future__ import annotations

import math
import re
from collections import Counter

ENGINE_VERSION = "casesearch-1.0.0"

STOP = set("""a an the and or of to in on at for from by with without was were is are be been being this that these those it its
as into after before during than then there their they he she his her them we our you your not no but if so such which who whom
while also had has have do did done one two three four five six seven eight nine ten can could would should may might will shall about over under between up down out off very""".split())


def _stem(t: str) -> str:
    for suf in ("ings", "ing", "edly", "ed", "es", "s"):
        if len(t) > len(suf) + 3 and t.endswith(suf):
            return t[: -len(suf)]
    return t


class Normaliser:
    def __init__(self, thesaurus: list[list[str]]):
        pairs = []
        for group in thesaurus:
            concept = "§" + re.sub(r"\W+", "_", group[0].lower())
            for ph in group:
                pairs.append((ph.lower(), concept))
        pairs.sort(key=lambda p: -len(p[0]))
        self.pairs = [(re.compile(r"(?<![\w-])" + re.escape(ph) + r"(?![\w-])"), c) for ph, c in pairs]
        self.labels = {("§" + re.sub(r"\W+", "_", g[0].lower())): g[0] for g in thesaurus}

    def text(self, s: str) -> str:
        s = " " + (s or "").lower() + " "
        for rx, c in self.pairs:
            s = rx.sub(" " + c + " ", s)
        return s

    def tokens(self, s: str) -> list[str]:
        out = []
        for t in re.findall(r"§\w+|[a-z0-9]+", self.text(s)):
            if t.startswith("§"):
                out.append(t)
            elif t not in STOP and len(t) > 1:
                out.append(_stem(t))
        return out

    def readable(self, t: str) -> str:
        return self.labels.get(t, t)


def detect_factors(norm: Normaliser, text: str, factors: list[dict]) -> list[str]:
    s = norm.text(text)
    found = []
    for f in factors:
        for kw in f.get("keywords", []):
            k = norm.text(kw).strip()
            if k and re.search(r"(?<![\w§])" + re.escape(k) + r"(?!\w)", s):
                found.append(f["code"])
                break
    return found


def case_document(case: dict) -> str:
    parts = [case.get("title", ""), case.get("summary", "")]
    for b in case.get("model", {}).get("blocks", []):
        parts += [b.get("label", ""), b.get("text", "")]
    return " ".join(parts)


def search(text: str, cases: list[dict], factors: list[dict], thesaurus: list[list[str]], limit: int = 10) -> dict:
    norm = Normaliser(thesaurus)
    docs = [Counter(norm.tokens(case_document(c))) for c in cases]
    n = len(docs)
    df = Counter(t for d in docs for t in d)
    idf = {t: math.log((1 + n) / (1 + df[t])) + 1 for t in df}
    q = Counter(norm.tokens(text))

    def vec(c):
        return {t: (1 + math.log(v)) * idf.get(t, math.log(1 + n) + 1) for t, v in c.items()}
    qv = vec(q)
    qn = math.sqrt(sum(v * v for v in qv.values())) or 1
    qf = set(detect_factors(norm, text, factors))
    out = []
    for c, d in zip(cases, docs):
        dv = vec(d)
        dn = math.sqrt(sum(v * v for v in dv.values())) or 1
        shared = [t for t in qv if t in dv]
        cos = sum(qv[t] * dv[t] for t in shared) / (qn * dn)
        cf = {b.get("factor") for b in c.get("model", {}).get("blocks", [])
              if b.get("factor") and (b.get("past") if isinstance(b.get("past"), str) else "S") in ("S", "SS")}
        fm = sorted(qf & cf)
        fscore = len(fm) / len(qf) if qf else 0.0
        score = 0.6 * cos + 0.4 * fscore if qf else cos
        top = sorted(shared, key=lambda t: -qv[t] * dv[t])[:8]
        out.append({"id": c["id"], "ref": c.get("ref"), "title": c.get("title"), "status": c.get("status"),
                    "score": round(score, 4), "text_similarity": round(cos, 4), "factor_share": round(fscore, 4),
                    "matched_terms": [norm.readable(t) for t in top], "matched_factors": fm})
    out.sort(key=lambda r: -r["score"])
    return {"detected_factors": sorted(qf), "results": out[:limit], "engine_version": ENGINE_VERSION}
