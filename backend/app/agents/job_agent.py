"""Job Matching Agent: ranks companies/roles for a candidate and matches job descriptions."""
import json
from pathlib import Path
from .catalog import extract_skills, label, learn_hint
from .similarity import scaled, similarities
from .skill_gap_agent import _satisfaction

DATA = Path(__file__).resolve().parent.parent / "data" / "companies.json"


def load_companies() -> list[dict]:
    return json.loads(DATA.read_text(encoding="utf-8"))["companies"]


def _fit_label(score: int) -> str:
    return "Strong fit" if score >= 75 else "Good fit" if score >= 55 else "Stretch" if score >= 35 else "Not yet"


def candidate_document(profile: dict, have: dict, resume_text: str = "") -> str:
    proj = " ".join(f"{p.get('title','')} {p.get('description','')}" if isinstance(p, dict) else str(p) for p in (profile.get("projects") or []) + (profile.get("experiences") or []))
    return " ".join([" ".join(have), proj, " ".join(profile.get("interests") or []), profile.get("career_goal") or "", resume_text[:3000]])


def match_companies(profile: dict, have: dict, coding_score: int | None = None, resume_text: str = "", top: int = 12) -> list[dict]:
    entries = [(c, r) for c in load_companies() for r in c["roles"]]
    docs = [f"{r['title']} {r['description']} " + " ".join(s.replace("|", " ") for s in r["core"] + r["nice"]) for _, r in entries]
    sims = similarities(candidate_document(profile, have, resume_text), docs)
    cgpa = profile.get("cgpa")
    out = []
    for (c, r), sim in zip(entries, sims):
        wsum = got = 0.0; matched, missing = [], []
        for tier, w in (("core", 2), ("nice", 1)):
            for item in r[tier]:
                sat, _ = _satisfaction(item, have); wsum += w; got += w * sat
                if sat >= 0.5: matched.append(label(item))
                elif tier == "core": missing.append(label(item))
        coverage = got / wsum if wsum else 0
        dsa_prev = coding_score / 100 if coding_score else have.get("dsa", {}).get("proficiency", 0.0) * 0.8
        dsa_fit = c["dsa_weight"] * dsa_prev + (1 - c["dsa_weight"]) * 1.0
        if cgpa is None: cg_fit, eligible = 0.7, None
        else:
            cg_fit = 1.0 if cgpa >= c["min_cgpa"] else max(0.0, 1 - (c["min_cgpa"] - cgpa) / 2)
            eligible = cgpa >= c["min_cgpa"]
        score = round(100 * (0.45 * coverage + 0.20 * scaled(sim) + 0.20 * dsa_fit + 0.15 * cg_fit))
        tips = []
        if missing: tips.append("Learn: " + ", ".join(missing[:3]))
        if c["dsa_weight"] >= 0.7 and dsa_prev < 0.6: tips.append("This company weighs DSA heavily; raise your coding practice")
        if eligible is False: tips.append(f"Typical CGPA cut-off is about {c['min_cgpa']}; check the current drive criteria")
        out.append({"company": c["name"], "category": c["category"], "role": r["title"], "match_score": score, "fit": _fit_label(score),
                    "eligible_by_cgpa": eligible, "matched_skills": matched[:8], "missing_skills": missing[:6],
                    "selection_process": c["process"], "how_to_improve": tips,
                    "breakdown": {"skills": round(coverage * 100), "profile_similarity": round(scaled(sim) * 100), "dsa_fit": round(dsa_fit * 100), "academics": round(cg_fit * 100)}})
    out.sort(key=lambda x: -x["match_score"])
    return out[:top]


def match_job_description(jd: str, have: dict, resume_text: str = "") -> dict:
    wanted = extract_skills(jd)
    matched = [s for s in wanted if have.get(s, {}).get("proficiency", 0) >= 0.5]
    missing = [s for s in wanted if s not in matched]
    sim = scaled(similarities(resume_text or " ".join(have), [jd])[0])
    coverage = len(matched) / len(wanted) if wanted else 0.0
    score = round(100 * (0.7 * coverage + 0.3 * sim)) if wanted else round(100 * sim)
    return {"match_score": score, "fit": _fit_label(score), "matched": matched, "missing": missing,
            "suggested_keywords": missing, "skills_in_jd": wanted,
            "advice": [f"{s}: ~{learn_hint(s)[0]}h. {learn_hint(s)[1]}" for s in missing[:4]],
            "note": None if wanted else "No recognised skills were found in this description; paste the full requirements section."}
